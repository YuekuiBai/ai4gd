"""Bounded framework changes with immutable attempts and guarded rollback."""
from __future__ import annotations

from pathlib import Path
import sys
from uuid import uuid4

from .godot import project
from .storage import Refused, authentic, execute, fingerprint, identifier, identity, inside, inventory, lock, read, stamp, write


def proposal(root: Path, name: str, targets: list[str], sources: list[Path], trigger: str, lesson: str) -> dict:
    root = root.resolve()
    identifier(name)
    if not targets or not sources or not trigger.strip() or not lesson.strip():
        raise Refused("A proposal needs bounded targets, measured sources, trigger and lesson")
    folder = root / ".ai4gd/evolution" / name
    with lock(root / ".ai4gd"):
        if folder.exists():
            raise Refused("Candidate id already exists")
        evidence = []
        for path in sources:
            path = path.resolve()
            if not path.is_file() or not path.stat().st_size:
                raise Refused("Source evidence is missing or empty")
            evidence.append({"path": str(path), "sha256": fingerprint(path)})
        selected = {}
        for relative in sorted(set(targets)):
            path = inside(root, relative)
            if any(x in {".git", ".ai4gd", ".venv"} for x in path.relative_to(root).parts):
                raise Refused("Runtime, Git and environment files are not evolution targets")
            if path.exists() and not path.is_file():
                raise Refused("Declare individual source files, not directories")
            key = path.relative_to(root).as_posix()
            selected[key] = {"before": fingerprint(path)}
        baseline = inventory(root)
        for key in selected:
            if selected[key]["before"] is not None:
                target = folder / "before" / key
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((root / key).read_bytes())
        data = {"id": name, "state": "proposed", "trigger": trigger, "lesson": lesson,
                "created": stamp(), "targets": selected, "baseline": baseline, "sources": evidence, "attempts": []}
        write(folder / "candidate.json", data)
        return data


def verify(root: Path, name: str, game: Path, regression: list[str], timeout: float = 300) -> dict:
    root = root.resolve()
    project(game)
    folder = root / ".ai4gd/evolution" / identifier(name)
    with lock(root / ".ai4gd"):
        data = read(folder / "candidate.json")
        if data["state"] not in {"proposed", "failed", "verified"}:
            raise Refused("Candidate is terminal")
        current = inventory(root)
        changed = {k for k in current.keys() | data["baseline"].keys() if current.get(k) != data["baseline"].get(k)}
        if changed - data["targets"].keys():
            raise Refused("Undeclared source edits: " + ", ".join(sorted(changed - data["targets"].keys())))
        if not changed:
            raise Refused("No source change; record a learning NOOP instead")
        before = identity(root, game)
        attempt = {"id": uuid4().hex, "gates": [], "passed": False}
        commands = [([sys.executable, "-m", "ai4gd", "audit", "--release"], root),
                    ([sys.executable, "-m", "pytest", "tests", "-q"], root), (regression, game)]
        for index, (argv, cwd) in enumerate(commands):
            result = execute(argv, cwd, folder / "attempts" / attempt["id"] / str(index), timeout)
            attempt["gates"].append(result)
            if result["exit_code"] != 0:
                break
        attempt["inputs"] = identity(root, game)
        attempt["passed"] = (len(attempt["gates"]) == 3 and all(g["exit_code"] == 0 for g in attempt["gates"])
                             and before == attempt["inputs"])
        data["attempts"].append(attempt)
        data["state"] = "verified" if attempt["passed"] else "failed"
        data["project"] = str(game.resolve())
        data["after"] = {key: fingerprint(root / key) for key in data["targets"]}
        write(folder / "candidate.json", data)
        return data


def finish(root: Path, name: str, operation: str, decision: str = "") -> dict:
    root = root.resolve()
    folder = root / ".ai4gd/evolution" / identifier(name)
    with lock(root / ".ai4gd"):
        data = read(folder / "candidate.json")
        if operation == "accept":
            if data["state"] != "verified" or not decision.strip():
                raise Refused("Accept requires verified gates and a current authorized decision")
            attempt = data["attempts"][-1]
            if identity(root, Path(data["project"])) != attempt["inputs"] or not all(authentic(g) for g in attempt["gates"]):
                raise Refused("Source, project or gate evidence changed after verification")
            if any(fingerprint(Path(s["path"])) != s["sha256"] for s in data["sources"]):
                raise Refused("Proposal evidence changed")
            data.update(state="accepted", decision=decision)
        elif operation == "rollback":
            if data["state"] not in {"failed", "verified", "accepted"}:
                raise Refused("Verify first to record the source being reverted")
            for key, previous in data["targets"].items():
                if fingerprint(root / key) != data["after"][key]:
                    raise Refused("Concurrent edit: " + key)
                if previous["before"] is not None and fingerprint(folder / "before" / key) != previous["before"]:
                    raise Refused("Missing or damaged snapshot: " + key)
            for key, previous in data["targets"].items():
                path = inside(root, key)
                if previous["before"] is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes((folder / "before" / key).read_bytes())
            data["state"] = "rolled-back"
        else:
            raise Refused("Unknown evolution operation")
        write(folder / "candidate.json", data)
        return data
