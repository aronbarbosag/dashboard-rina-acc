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
REQUEST_RETRIES = fetch_audits.REQUEST_RETRIES
REQUEST_TIMEOUT = fetch_audits.REQUEST_TIMEOUT
MAX_REPORT_WORKERS = fetch_audits.MAX_REPORT_WORKERS
RAW_FETCH_FILES = (
    fetch_audits.AUDITS_FILE,
    fetch_audits.REPORTS_FILE,
    fetch_audits.AIRCRAFT_REPORTS_FILE,
    fetch_audits.NONCONFORMITIES_CURRENT_FILE,
)
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


def load_json_file(path, default=None):
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return [] if default is None else default

    with path.open("r") as file:
        return json.load(file)


def save_json_file(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        json.dump(data, file, indent=4)


def parse_period_date(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = str(value).strip()
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def raw_fetch_files_exist(raw_dir):
    raw_dir = Path(raw_dir)
    return all((raw_dir / filename).is_file() for filename in RAW_FETCH_FILES)


def read_fetch_metadata(raw_dir):
    metadata_path = Path(raw_dir) / METADATA_FILE
    if not metadata_path.exists():
        return None

    try:
        with metadata_path.open("r") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def raw_data_covers_period(raw_dir, initial_date=None, final_date=None):
    if not raw_fetch_files_exist(raw_dir):
        return False

    metadata = read_fetch_metadata(raw_dir)
    if not metadata:
        return False

    cached_initial = parse_period_date(metadata.get("initial_date"))
    cached_final = parse_period_date(metadata.get("final_date"))
    requested_initial = parse_period_date(initial_date)
    requested_final = parse_period_date(final_date)

    if not cached_initial or not cached_final:
        return False

    if requested_initial and requested_initial < cached_initial:
        return False

    if requested_final and requested_final > cached_final:
        return False

    return True


def can_incremental_update(raw_dir, initial_date=None, final_date=None):
    if not raw_fetch_files_exist(raw_dir):
        return False

    metadata = read_fetch_metadata(raw_dir)
    if not metadata:
        return False

    cached_initial = parse_period_date(metadata.get("initial_date"))
    cached_final = parse_period_date(metadata.get("final_date"))
    requested_initial = parse_period_date(initial_date)
    requested_final = parse_period_date(final_date)

    if not cached_initial or not cached_final or not requested_final:
        return False

    if requested_initial and requested_initial < cached_initial:
        return False

    return requested_final > cached_final


def get_incremental_initial_date(raw_dir):
    metadata = read_fetch_metadata(raw_dir) or {}
    cached_final = parse_period_date(metadata.get("final_date"))
    if cached_final is None:
        return None

    return cached_final.strftime("%Y-%m-%d")


def get_raw_item_key(filename, item):
    if not isinstance(item, dict):
        return None

    if filename == fetch_audits.AIRCRAFT_REPORTS_FILE:
        return item.get("audit_id") or item.get("_id")

    if filename == fetch_audits.NONCONFORMITIES_CURRENT_FILE:
        audit_id = item.get("audit_id")
        area = item.get("area")
        period = item.get("period") or "current"
        if audit_id and area:
            return audit_id, area, period
        return None

    return item.get("_id")


def merge_lists_by_key(filename, existing_items, incoming_items):
    if filename == fetch_audits.NONCONFORMITIES_CURRENT_FILE:
        existing_items = [
            item
            for item in existing_items or []
            if isinstance(item, dict) and (item.get("period") or "current") == "current"
        ]
        incoming_items = [
            item
            for item in incoming_items or []
            if isinstance(item, dict) and (item.get("period") or "current") == "current"
        ]

    merged = []
    indexes_by_key = {}

    for item in existing_items or []:
        key = get_raw_item_key(filename, item)
        if key is None:
            merged.append(item)
            continue

        indexes_by_key[key] = len(merged)
        merged.append(item)

    for item in incoming_items or []:
        key = get_raw_item_key(filename, item)
        if key is None:
            merged.append(item)
            continue

        if key in indexes_by_key:
            merged[indexes_by_key[key]] = item
        else:
            indexes_by_key[key] = len(merged)
            merged.append(item)

    return merged


def build_merged_metadata(raw_dir, merged_raw_dir, requested_initial, requested_final):
    existing_metadata = read_fetch_metadata(raw_dir) or {}
    cached_initial = parse_period_date(existing_metadata.get("initial_date"))
    cached_final = parse_period_date(existing_metadata.get("final_date"))
    requested_initial = parse_period_date(requested_initial)
    requested_final = parse_period_date(requested_final)

    initial_dates = [value for value in (cached_initial, requested_initial) if value]
    final_dates = [value for value in (cached_final, requested_final) if value]
    initial_date = min(initial_dates) if initial_dates else cached_initial
    final_date = max(final_dates) if final_dates else cached_final

    audits = load_json_file(Path(merged_raw_dir) / fetch_audits.AUDITS_FILE)
    reports = load_json_file(Path(merged_raw_dir) / fetch_audits.REPORTS_FILE)
    aircraft_reports = load_json_file(
        Path(merged_raw_dir) / fetch_audits.AIRCRAFT_REPORTS_FILE
    )

    audits_count = len(audits)
    metadata = {
        **existing_metadata,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        "initial_date": initial_date.strftime("%Y-%m-%d") if initial_date else None,
        "final_date": (
            f"{final_date.strftime('%Y-%m-%d')}T23:59:00Z" if final_date else None
        ),
        "audits_count": audits_count,
        "reports_count": len(reports),
        "aircraft_reports_count": len(aircraft_reports),
        "estimated_request_count": 2 + (audits_count * 4),
        "max_report_workers": MAX_REPORT_WORKERS,
        "request_timeout": REQUEST_TIMEOUT,
        "request_retries": REQUEST_RETRIES,
        "update_mode": "incremental",
        "audits_file": str(Path(merged_raw_dir) / fetch_audits.AUDITS_FILE),
        "reports_file": str(Path(merged_raw_dir) / fetch_audits.REPORTS_FILE),
        "aircraft_reports_file": str(
            Path(merged_raw_dir) / fetch_audits.AIRCRAFT_REPORTS_FILE
        ),
        "nonconformities_current_file": str(
            Path(merged_raw_dir) / fetch_audits.NONCONFORMITIES_CURRENT_FILE
        ),
    }
    return metadata


def merge_raw_data(raw_dir, delta_raw_dir, merged_raw_dir, initial_date, final_date):
    raw_dir = Path(raw_dir)
    delta_raw_dir = Path(delta_raw_dir)
    merged_raw_dir = Path(merged_raw_dir)
    merged_raw_dir.mkdir(parents=True, exist_ok=True)

    for filename in RAW_FETCH_FILES:
        existing_items = load_json_file(raw_dir / filename)
        incoming_items = load_json_file(delta_raw_dir / filename)
        merged_items = merge_lists_by_key(filename, existing_items, incoming_items)
        save_json_file(merged_raw_dir / filename, merged_items)

    metadata = build_merged_metadata(raw_dir, merged_raw_dir, initial_date, final_date)
    save_json_file(merged_raw_dir / METADATA_FILE, metadata)
    return metadata


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
        temp_delta_raw_dir = temp_run_dir / "delta_raw"
        temp_processed_dir = temp_run_dir / "processed"

        try:
            if fetch:
                fetcher = FetchAudits(output_dir=temp_raw_dir)
                formatted_initial_date = format_initial_date(initial_date)
                formatted_final_date = format_final_date(final_date)

                if raw_data_covers_period(
                    raw_dir,
                    initial_date=formatted_initial_date,
                    final_date=formatted_final_date,
                ):
                    copy_existing_raw_data(raw_dir, temp_raw_dir)
                elif can_incremental_update(
                    raw_dir,
                    initial_date=formatted_initial_date,
                    final_date=formatted_final_date,
                ):
                    incremental_initial_date = get_incremental_initial_date(raw_dir)
                    fetcher = FetchAudits(output_dir=temp_delta_raw_dir)
                    if incremental_initial_date:
                        fetcher.set_initial_date(incremental_initial_date)

                    if formatted_final_date:
                        fetcher.set_final_date(formatted_final_date)

                    fetcher.run()
                    merge_raw_data(
                        raw_dir,
                        temp_delta_raw_dir,
                        temp_raw_dir,
                        formatted_initial_date,
                        formatted_final_date,
                    )
                else:
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
