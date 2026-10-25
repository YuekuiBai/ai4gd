"""Offline checks for authored source, context size and publishable files."""
from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path
import re
import subprocess

from .storage import inventory


def publish_paths(root: Path) -> list[str]:
    try:
        command = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                 capture_output=True, timeout=10)
        if command.returncode == 0:
            return sorted(set(x for x in command.stdout.decode("utf-8").split("\0") if x))
    except (OSError, subprocess.TimeoutExpired):
        pass
    return sorted(inventory(root))


def audit(root: Path, release: bool = False) -> dict:
    findings = []
    metrics = {"files": 0, "bytes": 0, "skills": [], "duplicate_files": []}
    contents = {}
    paths = publish_paths(root)
    for name in paths:
        path = root / name
        if path.is_symlink():
            findings.append({"file": name, "kind": "symlink-not-distributed"})
            continue
        if not path.is_file():
            continue
        parts = set(Path(name).parts)
        forbidden = bool(parts & {".ai4gd", ".godot", ".venv", "__pycache__", ".pytest_cache"})
        forbidden |= path.name in {".env", ".env.local", "id_ed25519", "id_rsa"} or path.suffix == ".dpapi"
        if forbidden:
            if release:
                findings.append({"file": name, "kind": "local-state-or-secret-file"})
            continue
        raw = path.read_bytes()
        metrics["files"] += 1
        metrics["bytes"] += len(raw)
        if len(raw) > 2_000_000:
            findings.append({"file": name, "kind": "file-over-2mb-budget"})
            continue
        contents.setdefault(sha256(raw).hexdigest(), []).append(name)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            findings.append({"file": name, "kind": "unexpected-binary"})
            continue
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=name)
            except SyntaxError as exc:
                findings.append({"file": name, "line": exc.lineno, "kind": "python-syntax"})
        if path.name == "SKILL.md":
            metrics["skills"].append({"file": name, "utf8_bytes": len(raw), "lines": len(text.splitlines())})
            if len(raw) > 16_384:
                findings.append({"file": name, "kind": "skill-over-16kb-budget"})
            if not re.match(r'\A---\r?\nname: [a-z0-9-]+\r?\ndescription: .+\r?\n---', text):
                findings.append({"file": name, "kind": "skill-frontmatter"})
        if path.suffix == ".md":
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
                if "://" in target or target.startswith(("#", "mailto:")) or any(c in target for c in "<>{}"):
                    continue
                relative = target.split("#", 1)[0]
                if relative and not (path.parent / relative).exists():
                    findings.append({"file": name, "kind": "broken-link", "target": relative})
        if release:
            patterns = {
                "private-key": r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',
                "github-token": r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
                "jwt": r'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}',
            }
            for number, line in enumerate(text.splitlines(), 1):
                for kind, pattern in patterns.items():
                    if re.search(pattern, line):
                        findings.append({"file": name, "line": number, "kind": kind})
    metrics["duplicate_files"] = [names for names in contents.values() if len(names) > 1]
    if release:
        for name in ("LICENSE", "NOTICE.md", "CONTRIBUTING.md", "README.md", ".github/workflows/verify.yml"):
            if name not in paths:
                findings.append({"file": name, "kind": "missing-distribution-file"})
    return {"passed": not findings, "findings": findings, "metrics": metrics,
            "scope": "current publishable files, not git history or a legal provenance determination"}
