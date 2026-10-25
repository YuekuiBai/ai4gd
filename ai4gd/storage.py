"""Small filesystem and evidence contracts shared by the command line tools."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import time
from uuid import uuid4


class Refused(ValueError):
    """The requested transition lacks valid inputs or current evidence."""


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def fingerprint(path: Path) -> str | None:
    return sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def inside(root: Path, relative: str) -> Path:
    item = Path(relative)
    if item.is_absolute() or not relative.strip():
        raise Refused("Expected a nonempty relative path")
    resolved = (root / item).resolve()
    if not resolved.is_relative_to(root.resolve()) or resolved == root.resolve():
        raise Refused("Path leaves the selected root")
    return resolved


def identifier(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise Refused("Use an id of 1–64 lowercase letters, digits or hyphens")
    return value


@contextmanager
def lock(folder: Path):
    """Serialize updates; an abandoned lock is never silently stolen."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ".write-lock"
    try:
        handle = path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise Refused(f"Another operation owns {path}; inspect its process before removing it") from exc
    try:
        with handle:
            handle.write(json.dumps({"pid": os.getpid(), "created": stamp()}))
        yield
    finally:
        path.unlink(missing_ok=True)


EXCLUDED = {".git", ".godot", ".ai4gd", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}


def inventory(root: Path) -> dict[str, str]:
    result = {}
    for folder, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDED and not (Path(folder) / x).is_symlink())
        for name in sorted(names):
            path = Path(folder) / name
            if path.is_symlink() or path.suffix in {".pyc", ".log"} or name.startswith(".env"):
                continue
            result[path.relative_to(root).as_posix()] = fingerprint(path)
    return result


def identity(*roots: Path) -> str:
    return sha256(json.dumps([inventory(p) for p in roots], sort_keys=True).encode()).hexdigest()


def execute(argv: list[str], cwd: Path, output: Path, timeout: float = 120) -> dict:
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise Refused("Command must be a nonempty JSON argv array, never a shell string")
    if timeout <= 0:
        raise Refused("Timeout must be positive")
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    record = {"argv": argv, "cwd": cwd.as_posix(), "started": stamp(), "exit_code": None}
    try:
        process = subprocess.run(argv, cwd=cwd, timeout=timeout, capture_output=True,
                                 env={**os.environ, "PYTHONUTF8": "1"})
        stdout, stderr = process.stdout, process.stderr
        record.update(exit_code=process.returncode, outcome="exited")
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        record["outcome"] = "timeout"
    except OSError as exc:
        stdout, stderr = b"", str(exc).encode("utf-8")
        record["outcome"] = "launch-error"
    (output / "stdout.txt").write_bytes(stdout)
    (output / "stderr.txt").write_bytes(stderr)
    record["seconds"] = round(time.monotonic() - started, 3)
    write(output / "result.json", record)
    return {**record, "directory": output.as_posix(),
            "files": {name: fingerprint(output / name) for name in ("stdout.txt", "stderr.txt", "result.json")}}


def authentic(record: dict) -> bool:
    return bool(record.get("files")) and all(
        value is not None and fingerprint(Path(record["directory"]) / name) == value
        for name, value in record["files"].items())
