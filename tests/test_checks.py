from pathlib import Path
import subprocess
import sys
import pytest

from ai4gd.checks import audit


def test_release_audit_finds_credentials_without_echoing_them(tmp_path):
    secret = "ghp_" + "a" * 40
    (tmp_path / "oops.txt").write_text(secret, encoding="utf-8")
    report = audit(tmp_path, release=True)
    assert any(f["kind"] == "github-token" for f in report["findings"])
    assert secret not in str(report)


def test_dense_skill_has_byte_budget_even_when_short(tmp_path):
    (tmp_path / "SKILL.md").write_text("---\nname: demo\ndescription: valid\n---\n" + "测" * 6000, encoding="utf-8")
    assert any(f["kind"] == "skill-over-16kb-budget" for f in audit(tmp_path)["findings"])


def test_tracked_runtime_is_rejected_even_if_gitignored(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    folder = tmp_path / ".ai4gd"
    folder.mkdir()
    (folder / "state.json").write_text("{}", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".ai4gd/state.json"], capture_output=True, check=True)
    (tmp_path / ".gitignore").write_text(".ai4gd/\n", encoding="utf-8")
    assert any(f["kind"] == "local-state-or-secret-file" for f in audit(tmp_path, release=True)["findings"])


def test_bad_link_and_python_syntax_are_not_ignored(tmp_path):
    (tmp_path / "README.md").write_text("[Missing](does-not-exist.md)", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def nope(\n", encoding="utf-8")
    kinds = {f["kind"] for f in audit(tmp_path)["findings"]}
    assert {"broken-link", "python-syntax"} <= kinds


def test_real_cli_returns_machine_readable_error_for_invalid_project(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-m", "ai4gd", "init", str(tmp_path)], cwd=root, capture_output=True, text=True)
    assert result.returncode == 2 and '"passed": false' in result.stdout
