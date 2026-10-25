"""Run Godot with explicit executable, bounded duration and diagnostic checks."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
from uuid import uuid4

from .storage import Refused, execute, fingerprint, inside, write


def project(path: Path) -> Path:
    path = path.resolve()
    if not (path / "project.godot").is_file():
        raise Refused("The selected directory is not a Godot project")
    return path


def engine(value: str | None) -> str:
    candidate = value or os.environ.get("GODOT_BIN") or shutil.which("godot4") or shutil.which("godot")
    if not candidate or not Path(candidate).is_file():
        raise Refused("Provide --godot or GODOT_BIN pointing to a Godot executable")
    return str(Path(candidate).resolve())


def script_entry(game: Path, value: str, visited: set[Path] | None = None) -> None:
    """Resolve file inheritance; imported global classes are checked via Godot's cache."""
    path = inside(game, value.removeprefix("res://"))
    visited = visited or set()
    if path in visited or not path.is_file():
        raise Refused("Missing script or cyclic inheritance")
    visited.add(path)
    text = path.read_text(encoding="utf-8-sig")
    found = re.search(r'^extends\s+([^#\r\n]+)', text, re.MULTILINE)
    if not found:
        raise Refused("Standalone scripts must extend SceneTree or MainLoop")
    parent = found[1].strip()
    if parent in {"SceneTree", "MainLoop"}:
        return
    if parent.startswith(('"', "'")):
        target = parent.strip('"\'')
        if not target.startswith("res://"):
            target = (path.parent / target).relative_to(game).as_posix()
        return script_entry(game, target, visited)
    cache = game / ".godot/global_script_class_cache.cfg"
    if cache.is_file():
        for block in cache.read_text(encoding="utf-8").split("{"):
            if re.search(r'"class"\s*:\s*&?"' + re.escape(parent) + r'"', block):
                target = re.search(r'"path"\s*:\s*"([^"]+)"', block)
                if target:
                    return script_entry(game, target[1], visited)
    raise Refused(f"{parent} is not a confirmed MainLoop base; run gdUnit suites via their runner and scenes via a scene driver")


def diagnostics(text: str) -> list[str]:
    """Retain real errors even when the engine exits with status zero."""
    errors = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r'^(?:SCRIPT ERROR:|ERROR:|Parse Error:|Shader compilation failed)', stripped):
            errors.append(stripped)
    return errors


def check(game: Path, binary: str | None, *, script: str | None = None,
          expected: str | None = None, timeout: float = 60) -> dict:
    game = project(game)
    executable = engine(binary)
    if script:
        script_entry(game, script)
    if script and not expected:
        raise Refused("A script regression requires an exact completion marker via --expect")
    output = game / ".ai4gd/runs" / uuid4().hex
    command = [executable, "--headless", "--path", str(game)]
    command += ["--script", script] if script else ["--editor", "--import"]
    command += ["--quit"] if not script else []
    result = execute(command, game, output, timeout)
    text = "\n".join((output / name).read_text(encoding="utf-8", errors="replace") for name in ("stdout.txt", "stderr.txt"))
    errors = diagnostics(text)
    marker = expected is None or expected in {line.strip() for line in text.splitlines()}
    assessment = {"passed": result["exit_code"] == 0 and not errors and marker,
                  "errors": errors, "completion_marker_found": marker, "visual_verified": False,
                  "command_evidence": result}
    write(output / "assessment.json", assessment)
    return {**assessment, "assessment": str(output / "assessment.json"),
            "assessment_sha256": fingerprint(output / "assessment.json")}
