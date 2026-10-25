from pathlib import Path
import sys
import pytest

from ai4gd import evolution
from ai4gd.storage import Refused, execute, fingerprint, identity, read, write


def proposed(framework, tmp_path, targets=None):
    evidence = tmp_path / "reproduction.json"
    evidence.write_text('{"observed":"real minimal experiment"}', encoding="utf-8")
    data = evolution.proposal(framework, "fix", targets or ["SKILL.md"], [evidence], "Observed failure", "Bounded correction")
    return data, evidence


def verified_fixture(framework, game, tmp_path):
    data, evidence = proposed(framework, tmp_path)
    (framework / "SKILL.md").write_text("New selected instruction", encoding="utf-8")
    result = execute([sys.executable, "-c", "print('ACTUAL_COMMAND')"], game, tmp_path / "gate")
    data.update(state="verified", project=str(game), after={"SKILL.md": fingerprint(framework / "SKILL.md")},
                attempts=[{"passed": True, "inputs": identity(framework, game), "gates": [result]}])
    write(framework / ".ai4gd/evolution/fix/candidate.json", data)
    return data, evidence


def test_snapshot_restores_only_declared_files(framework, game, tmp_path):
    original = (framework / "SKILL.md").read_bytes()
    verified_fixture(framework, game, tmp_path)
    unrelated = framework / "other.md"
    unrelated.write_text("Concurrent independent work", encoding="utf-8")
    assert evolution.finish(framework, "fix", "rollback")["state"] == "rolled-back"
    assert (framework / "SKILL.md").read_bytes() == original
    assert unrelated.read_text() == "Concurrent independent work"


def test_concurrent_target_edit_blocks_rollback(framework, game, tmp_path):
    verified_fixture(framework, game, tmp_path)
    (framework / "SKILL.md").write_text("Someone else's later change", encoding="utf-8")
    with pytest.raises(Refused, match="Concurrent edit"):
        evolution.finish(framework, "fix", "rollback")


def test_changed_game_blocks_acceptance(framework, game, tmp_path):
    verified_fixture(framework, game, tmp_path)
    (game / "added.gd").write_text("extends Node", encoding="utf-8")
    with pytest.raises(Refused, match="changed"):
        evolution.finish(framework, "fix", "accept", "Current user approval")


def test_changed_source_evidence_blocks_acceptance(framework, game, tmp_path):
    _, evidence = verified_fixture(framework, game, tmp_path)
    evidence.write_text("New incompatible observation", encoding="utf-8")
    with pytest.raises(Refused, match="evidence changed"):
        evolution.finish(framework, "fix", "accept", "Current user approval")


def test_corrupt_snapshot_refuses_without_partial_rollback(framework, game, tmp_path):
    verified_fixture(framework, game, tmp_path)
    backup = framework / ".ai4gd/evolution/fix/before/SKILL.md"
    backup.write_text("corrupted", encoding="utf-8")
    with pytest.raises(Refused, match="snapshot"):
        evolution.finish(framework, "fix", "rollback")
    assert (framework / "SKILL.md").read_text() == "New selected instruction"


def test_undeclared_edits_fail_before_running_gates(framework, game, tmp_path):
    proposed(framework, tmp_path)
    (framework / "not-declared.py").write_text("changed=True", encoding="utf-8")
    with pytest.raises(Refused, match="Undeclared"):
        evolution.verify(framework, "fix", game, [sys.executable, "-c", "print('unused')"])


def test_noop_and_runtime_targets_refused(framework, game, tmp_path):
    proposed(framework, tmp_path)
    with pytest.raises(Refused, match="No source change"):
        evolution.verify(framework, "fix", game, [sys.executable, "-c", "print('unused')"])
    evidence = tmp_path / "source.txt"
    evidence.write_text("observed", encoding="utf-8")
    with pytest.raises(Refused):
        evolution.proposal(framework, "unsafe", [".ai4gd/status.json"], [evidence], "Trigger", "Lesson")


def test_new_file_rollback_removes_only_new_target(framework, game, tmp_path):
    data, _ = proposed(framework, tmp_path, ["new.py"])
    (framework / "new.py").write_text("value=1", encoding="utf-8")
    data.update(state="failed", after={"new.py": fingerprint(framework / "new.py")})
    write(framework / ".ai4gd/evolution/fix/candidate.json", data)
    evolution.finish(framework, "fix", "rollback")
    assert not (framework / "new.py").exists()
