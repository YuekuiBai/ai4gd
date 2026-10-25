from pathlib import Path
import sys
import pytest

from ai4gd.storage import Refused, authentic, execute, identity, inside, lock, read, write


def test_recorded_command_and_tamper_detection(tmp_path):
    result = execute([sys.executable, "-c", "print('OBSERVED')"], tmp_path, tmp_path / "proof")
    assert result["exit_code"] == 0 and authentic(result)
    (tmp_path / "proof/stdout.txt").write_text("invented", encoding="utf-8")
    assert not authentic(result)


def test_timeout_is_not_success(tmp_path):
    result = execute([sys.executable, "-c", "import time; time.sleep(2)"], tmp_path, tmp_path / "timeout", .05)
    assert result["exit_code"] is None and result["outcome"] == "timeout"


@pytest.mark.parametrize("value", ["../outside", "", "."])
def test_paths_stay_in_selected_root(tmp_path, value):
    with pytest.raises(Refused):
        inside(tmp_path, value)


def test_lock_conflict_and_release(tmp_path):
    with lock(tmp_path):
        with pytest.raises(Refused):
            with lock(tmp_path):
                pass
    with lock(tmp_path):
        pass


def test_runtime_noise_does_not_expire_source_identity(tmp_path):
    (tmp_path / "source.py").write_text("initial", encoding="utf-8")
    first = identity(tmp_path)
    write(tmp_path / ".ai4gd/status.json", {"state": "changed"})
    assert identity(tmp_path) == first
    (tmp_path / "source.py").write_text("changed", encoding="utf-8")
    assert identity(tmp_path) != first


@pytest.mark.parametrize("argv", ["echo done", [], [""], [1]])
def test_shell_strings_and_invalid_argv_are_refused(tmp_path, argv):
    with pytest.raises(Refused):
        execute(argv, tmp_path, tmp_path / "bad")
