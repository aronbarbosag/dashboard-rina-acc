import pytest

from scripts.run_pipeline import (
    PipelineAlreadyRunningError,
    is_pipeline_locked,
    pipeline_lock,
    read_pipeline_lock,
)


def test_pipeline_lock_creates_and_removes_lock_file(tmp_path):
    raw_dir = tmp_path / "raw"

    with pipeline_lock(raw_dir):
        assert is_pipeline_locked(raw_dir) is True
        assert read_pipeline_lock(raw_dir)["pid"] is not None

    assert is_pipeline_locked(raw_dir) is False


def test_pipeline_lock_blocks_concurrent_updates(tmp_path):
    raw_dir = tmp_path / "raw"

    with pipeline_lock(raw_dir):
        with pytest.raises(PipelineAlreadyRunningError):
            with pipeline_lock(raw_dir):
                pass
