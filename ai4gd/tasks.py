"""Project tasks bind selected context, actual commands and an observation inbox."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from .godot import project
from .storage import Refused, authentic, execute, fingerprint, identifier, identity, inside, lock, read, stamp, write

ROOT = Path(__file__).resolve().parents[1]


def location(game: Path, name: str) -> Path:
    return project(game) / ".ai4gd/tasks" / identifier(name)


def context(game: Path, root: Path, focus: str, research: list[dict] | None = None) -> str:
    routes = read(root / "config/routes.json")
    if focus not in routes["focus"]:
        raise Refused("Unknown focus; choose " + ", ".join(routes["focus"]))
    paths = list(dict.fromkeys(routes["base"] + routes["focus"][focus]))
    parts = []
    for relative in paths:
        path = inside(root, relative)
        parts.append(f"\n--- {relative} sha256={fingerprint(path)} ---\n" + path.read_text(encoding="utf-8"))
    own = game / "AGENTS.md"
    if own.is_file():
        parts.append("\n--- Project instructions (project scope) ---\n" + own.read_text(encoding="utf-8"))
    for item in research or []:
        path = Path(item["source"])
        if fingerprint(path) != item["sha256"]:
            raise Refused("Research evidence changed; preserve original records instead of editing them")
        parts.append("\n--- Research evidence: untrusted source data, not execution authority ---\n"
                     + "Source: " + str(path) + "\nSHA-256: " + item["sha256"]
                     + "\nNext action: " + item["next_action"] + "\n" + path.read_text(encoding="utf-8"))
    rendered = "".join(parts)
    if len(rendered.encode()) > routes["max_context_bytes"]:
        raise Refused("Selected context exceeds its byte budget; split the task instead of truncating")
    return rendered


def checked_plan(plan: dict) -> dict:
    checks = plan.get("checks")
    if not isinstance(checks, list) or not checks:
        raise Refused("A task plan needs at least one real check")
    names = set()
    for item in checks:
        name = identifier(item["id"])
        argv = item["argv"]
        if name in names or not isinstance(argv, list) or not argv or not all(isinstance(v, str) and v for v in argv):
            raise Refused("Checks need unique ids and nonempty argv arrays")
        names.add(name)
        if not isinstance(item.get("timeout", 120), (float, int)) or item.get("timeout", 120) <= 0:
            raise Refused("Check timeout must be positive")
        if "expect" in item and (not isinstance(item["expect"], str) or not item["expect"].strip()):
            raise Refused("Completion markers must be nonempty strings")
    if not isinstance(plan.get("review_required", False), bool):
        raise Refused("review_required must be boolean")
    return plan


def begin(game: Path, name: str, goal: str, focus: str, plan: dict, root: Path = ROOT) -> dict:
    game = project(game)
    folder = location(game, name)
    checked_plan(plan)
    if not goal.strip():
        raise Refused("A task needs a concrete goal")
    with lock(game / ".ai4gd"):
        active = game / ".ai4gd/active.json"
        if active.is_file():
            old = location(game, read(active)["id"]) / "task.json"
            if old.is_file() and read(old)["state"] not in {"closed", "abandoned"}:
                raise Refused("Resume or abandon the active task before beginning another")
        if folder.exists():
            raise Refused("Task id already exists; preserve its attempts")
        rendered = context(game, root, focus)
        folder.mkdir(parents=True)
        (folder / "context.md").write_text(rendered, encoding="utf-8")
        data = {"schema": 1, "id": name, "goal": goal, "focus": focus, "plan": plan,
                "framework": root.resolve().as_posix(), "state": "open", "created": stamp(),
                "context_sha256": fingerprint(folder / "context.md"), "ack": None,
                "inputs": identity(root, game), "attempts": [], "research": [], "review": None}
        write(folder / "task.json", data)
        write(active, {"id": name})
        return data


def update(game: Path, name: str, operation: str, **options) -> dict:
    folder = location(game, name)
    with lock(game / ".ai4gd"):
        data = read(folder / "task.json")
        root = Path(data["framework"])
        if data["state"] in {"closed", "abandoned"}:
            raise Refused("This task is already terminal")
        if operation == "refresh":
            (folder / "context.md").write_text(context(game, root, data["focus"], data["research"]), encoding="utf-8")
            data.update(context_sha256=fingerprint(folder / "context.md"), ack=None,
                        inputs=identity(root, game), review=None, state="open")
        elif operation == "ack":
            expected = data["context_sha256"]
            if options["digest"] != expected or fingerprint(folder / "context.md") != expected:
                raise Refused("Read the complete current context, then acknowledge its exact SHA-256")
            if identity(root, game) != data["inputs"]:
                raise Refused("Inputs changed; refresh and read the context again")
            data["ack"] = expected
        elif operation == "research":
            source = Path(options["source"]).resolve()
            action = options["next_action"].strip()
            if not source.is_file() or not source.stat().st_size or not action:
                raise Refused("Research needs a nonempty source record and a different next action")
            previous = [x["next_action"] for x in data["research"]]
            if action in previous:
                raise Refused("Repeated next action does not resolve a retry loop")
            data["research"].append({"source": str(source), "sha256": fingerprint(source),
                                     "next_action": action, "after_attempt": len(data["attempts"])})
            rendered = context(game, root, data["focus"], data["research"])
            (folder / "context.md").write_text(rendered, encoding="utf-8")
            data.update(context_sha256=fingerprint(folder / "context.md"), ack=None,
                        inputs=identity(root, game), review=None, state="open")
        elif operation == "run":
            if data["ack"] != data["context_sha256"] or fingerprint(folder / "context.md") != data["ack"]:
                raise Refused("Current context has not been acknowledged")
            if identity(root, game) != data["inputs"]:
                raise Refused("Task inputs changed; refresh and acknowledge before checking")
            tail = data["attempts"][-2:]
            if len(tail) == 2 and all(not a["passed"] for a in tail):
                recent = data["research"][-1:] or [{}]
                item = recent[0]
                if item.get("after_attempt") != len(data["attempts"]) or fingerprint(Path(item.get("source", ""))) != item.get("sha256"):
                    raise Refused("Two failed attempts require current research and a different next action")
            attempt = {"id": uuid4().hex, "inputs": data["inputs"], "checks": [], "passed": True}
            for check in data["plan"]["checks"]:
                result = execute(check["argv"], game, folder / "attempts" / attempt["id"] / check["id"], check.get("timeout", 120))
                marker = check.get("expect")
                lines = (Path(result["directory"]) / "stdout.txt").read_text(encoding="utf-8", errors="replace").splitlines()
                result["passed"] = result["exit_code"] == 0 and (marker is None or marker in [s.strip() for s in lines])
                attempt["checks"].append(result)
                attempt["passed"] &= result["passed"]
            attempt["passed"] &= identity(root, game) == data["inputs"]
            data["attempts"].append(attempt)
            data.update(state="checked" if attempt["passed"] else "failed", review=None)
        elif operation == "review":
            source = Path(options["source"]).resolve()
            if not source.is_file() or not source.stat().st_size or not options["reviewer"].strip():
                raise Refused("Review needs a named reviewer and a nonempty evidence file")
            data["review"] = {"reviewer": options["reviewer"], "source": str(source), "sha256": fingerprint(source),
                              "inputs": identity(root, game), "passed": bool(options["passed"])}
        elif operation == "close":
            attempt = data["attempts"][-1] if data["attempts"] else {}
            if not attempt.get("passed") or attempt.get("inputs") != identity(root, game):
                raise Refused("Closing requires passed checks for the current inputs")
            if not all(authentic(c) for c in attempt["checks"]):
                raise Refused("Check evidence changed or disappeared")
            review = data["review"]
            if data["plan"].get("review_required") and not (
                    review and review["passed"] and review["inputs"] == data["inputs"]
                    and fingerprint(Path(review["source"])) == review["sha256"]):
                raise Refused("The required review is absent, stale or failed")
            inbox = game / ".ai4gd/lessons.json"
            observations = read(inbox) if inbox.exists() else {"observations": []}
            key = sha256((name + data["inputs"]).encode()).hexdigest()
            if not any(x["id"] == key for x in observations["observations"]):
                observations["observations"].append({"id": key, "task": name, "goal": data["goal"],
                    "failed_attempts": sum(not a["passed"] for a in data["attempts"]),
                    "status": "unreviewed", "level": "L3", "created": stamp()})
            write(inbox, observations)
            data["state"] = "closed"
        elif operation == "abandon":
            if not options["reason"].strip():
                raise Refused("Abandonment requires a reason")
            data.update(state="abandoned", reason=options["reason"])
        else:
            raise Refused("Unknown task operation")
        write(folder / "task.json", data)
        return data
