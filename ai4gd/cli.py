"""One JSON command interface for humans, coding agents and model API drivers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__, checks, evolution, godot, knowledge, tasks
from .storage import Refused, execute, read, write


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ai4gd")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--root", type=Path, default=tasks.ROOT, help="Framework source root")
    commands = p.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit", help="Check source, links, budgets and release files")
    audit.add_argument("--release", action="store_true")
    init = commands.add_parser("init", help="Bind an existing game without copying source or installing plugins")
    init.add_argument("project", type=Path)
    init.add_argument("--rebind", action="store_true")
    register = commands.add_parser("register", help="Write a pointer-only skill discovery file")
    register.add_argument("--dest", type=Path, required=True)
    check = commands.add_parser("check", help="Import a Godot project or run a standalone regression")
    check.add_argument("project", type=Path)
    check.add_argument("--godot")
    check.add_argument("--script")
    check.add_argument("--expect")
    check.add_argument("--timeout", type=float, default=60)
    task = commands.add_parser("task")
    task.add_argument("project", type=Path)
    task.add_argument("id")
    operations = task.add_subparsers(dest="operation", required=True)
    begin = operations.add_parser("begin")
    begin.add_argument("--goal", required=True)
    begin.add_argument("--focus", default="code")
    begin.add_argument("--plan", type=Path, required=True)
    ack = operations.add_parser("ack")
    ack.add_argument("--sha256", required=True)
    for op in ("show", "refresh", "run", "close"):
        operations.add_parser(op)
    research = operations.add_parser("research")
    research.add_argument("--source", type=Path, required=True)
    research.add_argument("--next-action", required=True)
    review = operations.add_parser("review")
    review.add_argument("--source", type=Path, required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--passed", action="store_true")
    abandon = operations.add_parser("abandon")
    abandon.add_argument("--reason", required=True)
    evolve = commands.add_parser("evolve")
    evolve.add_argument("id")
    stages = evolve.add_subparsers(dest="operation", required=True)
    propose = stages.add_parser("propose")
    propose.add_argument("--target", action="append", required=True)
    propose.add_argument("--source", type=Path, action="append", required=True)
    propose.add_argument("--trigger", required=True)
    propose.add_argument("--lesson", required=True)
    verify = stages.add_parser("verify")
    verify.add_argument("--project", type=Path, required=True)
    verify.add_argument("--regression", type=Path, required=True, help="JSON file containing a command argv array")
    verify.add_argument("--timeout", type=float, default=300)
    accept = stages.add_parser("accept")
    accept.add_argument("--decision", required=True)
    stages.add_parser("rollback")
    stages.add_parser("show")
    kb = commands.add_parser("knowledge")
    actions = kb.add_subparsers(dest="operation", required=True)
    learn = actions.add_parser("learn")
    learn.add_argument("--godot-version", required=True)
    learn.add_argument("--online", action="store_true")
    learn.add_argument("--limit", type=int, default=2)
    review_source = actions.add_parser("review")
    review_source.add_argument("key")
    review_source.add_argument("--decision", choices=["noop", "local", "candidate"], required=True)
    review_source.add_argument("--reason", required=True)
    status = actions.add_parser("vector-status")
    status.add_argument("--target", choices=["local", "cloud"], default="local")
    index = actions.add_parser("index")
    index.add_argument("--target", choices=["local", "cloud"], default="local")
    index.add_argument("--godot-version", required=True)
    index.add_argument("--allow-model-download", action="store_true")
    retrieve = actions.add_parser("retrieve")
    retrieve.add_argument("query")
    retrieve.add_argument("--godot-version", required=True)
    retrieve.add_argument("--target", choices=["local", "cloud", "both"], default="local")
    retrieve.add_argument("--limit", type=int, default=6)
    return p


def dispatch(args) -> dict:
    root = args.root.resolve()
    if args.command == "audit":
        return checks.audit(root, args.release)
    if args.command == "init":
        project = godot.project(args.project)
        path = project / ".ai4gd/engine.json"
        if path.is_file() and read(path).get("engine_root") != str(root) and not args.rebind:
            raise Refused("Project uses another framework; --rebind explicitly switches the source binding")
        write(path, {"schema": 2, "engine_root": str(root), "framework_version": __version__})
        return {"project": str(project), "binding": str(path), "copied_tools": False}
    if args.command == "register":
        path = args.dest.resolve() / "ai4gd/SKILL.md"
        if path.exists() and "<!-- ai4gd-source-pointer -->" not in path.read_text(encoding="utf-8"):
            raise Refused("Existing skill is not an ai4gd pointer; refusing to overwrite")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\nname: ai4gd\ndescription: Godot development, verification and evidence-driven framework improvement.\n---\n\n'
                        '<!-- ai4gd-source-pointer -->\nRead `' + str(root / "SKILL.md") + '`; resolve its links at that source.\n', encoding="utf-8")
        return {"pointer": str(path), "source": str(root)}
    if args.command == "check":
        return godot.check(args.project, args.godot, script=args.script, expected=args.expect, timeout=args.timeout)
    if args.command == "task":
        if args.operation == "begin":
            return tasks.begin(args.project, args.id, args.goal, args.focus, read(args.plan), root)
        if args.operation == "show":
            return read(tasks.location(args.project, args.id) / "task.json")
        options = {k: getattr(args, k) for k in ("source", "next_action", "reviewer", "passed", "reason") if hasattr(args, k)}
        if args.operation == "ack":
            options["digest"] = args.sha256
        return tasks.update(args.project.resolve(), args.id, args.operation, **options)
    if args.command == "evolve":
        if args.operation == "propose":
            return evolution.proposal(root, args.id, args.target, args.source, args.trigger, args.lesson)
        if args.operation == "verify":
            argv = json.loads(args.regression.read_text(encoding="utf-8-sig"))
            return evolution.verify(root, args.id, args.project, argv, args.timeout)
        if args.operation == "show":
            return read(root / ".ai4gd/evolution" / args.id / "candidate.json")
        return evolution.finish(root, args.id, args.operation, getattr(args, "decision", ""))
    if args.operation == "learn":
        return knowledge.learn(root, args.godot_version, online=args.online, limit=args.limit)
    if args.operation == "review":
        return knowledge.review(root, args.key, args.decision, args.reason)
    if args.operation == "vector-status":
        return {"target": args.target, "collections": knowledge.Qdrant(args.target).call("/collections")["result"]["collections"]}
    if args.operation == "index":
        return knowledge.index(root, args.godot_version, args.target, knowledge.Embeddings(args.allow_model_download))
    targets = ["local", "cloud"] if args.target == "both" else [args.target]
    return knowledge.retrieve(args.query, args.godot_version, targets, args.limit)


def main(argv: list[str] | None = None) -> int:
    try:
        result = dispatch(parser().parse_args(argv))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("passed") is False or result.get("state") == "failed" else 0
    except (OSError, ValueError, KeyError, ImportError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 2
