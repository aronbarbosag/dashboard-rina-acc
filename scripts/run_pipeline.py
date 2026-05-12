import argparse
import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from importlib import import_module
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

fetch_audits = import_module("fetches.fetch_audits")
transform_audits = import_module("transforms.transform_audits")

DEFAULT_RAW_DIR = fetch_audits.DEFAULT_RAW_DIR
FetchAudits = fetch_audits.FetchAudits
METADATA_FILE = fetch_audits.METADATA_FILE
PROCESSED_DIR = transform_audits.PROCESSED_DIR
run_transform = transform_audits.run_transform


LOCK_STALE_AFTER_SECONDS = 2 * 60 * 60


class PipelineAlreadyRunningError(RuntimeError):
    pass


def get_data_dir(raw_dir=DEFAULT_RAW_DIR):
    return Path(raw_dir).parent


def get_lock_path(raw_dir=DEFAULT_RAW_DIR):
    return get_data_dir(raw_dir) / ".pipeline.lock"


def read_pipeline_lock(raw_dir=DEFAULT_RAW_DIR):
    lock_path = get_lock_path(raw_dir)
    if not lock_path.exists():
        return None

    try:
        with lock_path.open("r") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {"lock_path": str(lock_path), "status": "unknown"}


def is_pipeline_locked(raw_dir=DEFAULT_RAW_DIR):
    lock_info = read_pipeline_lock(raw_dir)
    if not lock_info:
        return False

    started_at = lock_info.get("started_at")
    if not started_at:
        return True

    parsed_started_at = datetime.fromisoformat(started_at)
    age = datetime.now(tz=timezone.utc) - parsed_started_at
    return age.total_seconds() <= LOCK_STALE_AFTER_SECONDS


def remove_stale_lock(raw_dir=DEFAULT_RAW_DIR):
    if is_pipeline_locked(raw_dir):
        return

    lock_path = get_lock_path(raw_dir)
    if lock_path.exists():
        lock_path.unlink()


@contextmanager
def pipeline_lock(raw_dir=DEFAULT_RAW_DIR):
    lock_path = get_lock_path(raw_dir)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    remove_stale_lock(raw_dir)

    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "lock_path": str(lock_path),
    }

    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise PipelineAlreadyRunningError(
            "A pipeline update is already running."
        ) from error

    with os.fdopen(descriptor, "w") as file:
        json.dump(payload, file, indent=4)

    try:
        yield payload
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def publish_directory(source_dir, target_dir):
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for source_file in source_dir.iterdir():
        if not source_file.is_file():
            continue

        target_file = target_dir / source_file.name
        os.replace(source_file, target_file)


def copy_existing_raw_data(raw_dir, temp_raw_dir):
    raw_dir = Path(raw_dir)
    temp_raw_dir = Path(temp_raw_dir)
    temp_raw_dir.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        return

    for source_file in raw_dir.iterdir():
        if source_file.is_file() and source_file.suffix == ".json":
            shutil.copy2(source_file, temp_raw_dir / source_file.name)


def format_initial_date(value):
    if value is None:
        return None

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    return str(value)


def format_final_date(value):
    if value is None:
        return None

    if isinstance(value, date):
        return f"{value.strftime('%Y-%m-%d')}T23:59:00Z"

    value = str(value)
    if "T" in value:
        return value

    return f"{value}T23:59:00Z"


def run_pipeline(
    initial_date=None,
    final_date=None,
    raw_dir=DEFAULT_RAW_DIR,
    processed_dir=PROCESSED_DIR,
    fetch=True,
):
    raw_dir = Path(raw_dir)
    processed_dir = Path(processed_dir)
    data_dir = get_data_dir(raw_dir)
    temp_root = data_dir / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)

    with pipeline_lock(raw_dir):
        temp_run_dir = Path(tempfile.mkdtemp(prefix="pipeline_", dir=temp_root))
        temp_raw_dir = temp_run_dir / "raw"
        temp_processed_dir = temp_run_dir / "processed"

        try:
            if fetch:
                fetcher = FetchAudits(output_dir=temp_raw_dir)
                formatted_initial_date = format_initial_date(initial_date)
                formatted_final_date = format_final_date(final_date)

                if formatted_initial_date:
                    fetcher.set_initial_date(formatted_initial_date)

                if formatted_final_date:
                    fetcher.set_final_date(formatted_final_date)

                fetcher.run()
            else:
                copy_existing_raw_data(raw_dir, temp_raw_dir)

            result = run_transform(
                raw_dir=temp_raw_dir,
                processed_dir=temp_processed_dir,
            )

            publish_directory(temp_raw_dir, raw_dir)
            publish_directory(temp_processed_dir, processed_dir)

            return result
        finally:
            shutil.rmtree(temp_run_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch RINAACC data and build processed dashboard datasets."
    )
    parser.add_argument(
        "--initial-date", help="Initial audit date in YYYY-MM-DD format."
    )
    parser.add_argument("--final-date", help="Final audit date in YYYY-MM-DD format.")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Only transform existing raw JSON files.",
    )
    args = parser.parse_args()

    result = run_pipeline(
        initial_date=args.initial_date,
        final_date=args.final_date,
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        fetch=not args.skip_fetch,
    )

    kpis = result["kpis"]
    print(
        "Pipeline finished: "
        f"{kpis['total_audits']} audits, "
        f"{kpis['total_nonconformities']} nonconformities."
    )


if __name__ == "__main__":
    main()
