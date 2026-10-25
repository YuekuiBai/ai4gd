import sys
from pathlib import Path
import pytest

from ai4gd import tasks
from ai4gd.storage import Refused, read


def plan(code="print('MECHANISM_OK')", review=False, marker="MECHANISM_OK"):
    return {"checks": [{"id": "mechanism", "argv": [sys.executable, "-c", code], "expect": marker}], "review_required": review}


def started(game, framework, selected=None):
    data = tasks.begin(game, "input-fix", "Mouse recaptures after pause", "code", selected or plan(), framework)
    tasks.update(game, "input-fix", "ack", digest=data["context_sha256"])
    return data


def test_real_task_closes_and_captures_only_unreviewed_observations(game, framework):
    started(game, framework)
    assert tasks.update(game, "input-fix", "run")["state"] == "checked"
    assert tasks.update(game, "input-fix", "close")["state"] == "closed"
    item = read(game / ".ai4gd/lessons.json")["observations"][0]
    assert item["status"] == "unreviewed" and item["level"] == "L3"
    assert not (game / "MEMORY.md").exists()


def test_changed_input_requires_refresh_and_rerun(game, framework):
    started(game, framework)
    tasks.update(game, "input-fix", "run")
    (game / "movement.gd").write_text("extends Node\n", encoding="utf-8")
    with pytest.raises(Refused, match="current inputs"):
        tasks.update(game, "input-fix", "close")
    with pytest.raises(Refused, match="changed"):
        tasks.update(game, "input-fix", "run")
    data = tasks.update(game, "input-fix", "refresh")
    tasks.update(game, "input-fix", "ack", digest=data["context_sha256"])
    tasks.update(game, "input-fix", "run")
    assert tasks.update(game, "input-fix", "close")["state"] == "closed"


def test_substring_completion_marker_does_not_pass(game, framework):
    started(game, framework, plan("print('not MECHANISM_OK yet')"))
    assert tasks.update(game, "input-fix", "run")["state"] == "failed"
    with pytest.raises(Refused):
        tasks.update(game, "input-fix", "close")


def test_failed_attempts_preserved_and_research_required(game, framework, tmp_path):
    started(game, framework, plan("raise SystemExit(1)"))
    tasks.update(game, "input-fix", "run")
    data = tasks.update(game, "input-fix", "run")
    assert len(data["attempts"]) == 2
    with pytest.raises(Refused, match="research"):
        tasks.update(game, "input-fix", "run")
    source = tmp_path / "research.md"
    source.write_text("Actual symptom and original issue URL; test input propagation instead.", encoding="utf-8")
    updated = tasks.update(game, "input-fix", "research", source=source, next_action="Inspect GUI event propagation")
    tasks.update(game, "input-fix", "ack", digest=updated["context_sha256"])
    data = tasks.update(game, "input-fix", "run")
    assert len(data["attempts"]) == 3
    assert all(Path(c["directory"]).is_dir() for a in data["attempts"] for c in a["checks"])


def test_changed_research_evidence_cannot_unlock_retry(game, framework, tmp_path):
    started(game, framework, plan("raise SystemExit(1)"))
    for _ in range(2): tasks.update(game, "input-fix", "run")
    source = tmp_path / "research.md"
    source.write_text("original evidence", encoding="utf-8")
    tasks.update(game, "input-fix", "research", source=source, next_action="Inspect another event route")
    source.write_text("changed evidence", encoding="utf-8")
    with pytest.raises(Refused): tasks.update(game, "input-fix", "run")


def test_review_must_exist_and_remain_intact(game, framework, tmp_path):
    started(game, framework, plan(review=True))
    tasks.update(game, "input-fix", "run")
    with pytest.raises(Refused, match="review"):
        tasks.update(game, "input-fix", "close")
    record = tmp_path / "review.md"
    record.write_text("Self-review: observed cursor capture and Escape recovery in a visible window.", encoding="utf-8")
    tasks.update(game, "input-fix", "review", source=record, reviewer="self-review", passed=True)
    record.write_text("replacement", encoding="utf-8")
    with pytest.raises(Refused): tasks.update(game, "input-fix", "close")


def test_modified_command_log_cannot_be_used_to_close(game, framework):
    started(game, framework)
    data = tasks.update(game, "input-fix", "run")
    folder = Path(data["attempts"][-1]["checks"][0]["directory"])
    (folder / "stdout.txt").write_text("MECHANISM_OK\nforged", encoding="utf-8")
    with pytest.raises(Refused, match="evidence"):
        tasks.update(game, "input-fix", "close")


def test_cannot_replace_active_task_or_ack_modified_context(game, framework):
    data = started(game, framework)
    with pytest.raises(Refused, match="active task"):
        tasks.begin(game, "other", "Another goal", "code", plan(), framework)
    (tasks.location(game, "input-fix") / "context.md").write_text("shortened", encoding="utf-8")
    with pytest.raises(Refused):
        tasks.update(game, "input-fix", "ack", digest=data["context_sha256"])


def test_checks_mutating_source_cannot_prove_current_inputs(game, framework):
    started(game, framework, plan("from pathlib import Path; Path('change.txt').write_text('mutated'); print('MECHANISM_OK')"))
    assert tasks.update(game, "input-fix", "run")["state"] == "failed"


def test_research_delivers_findings_and_requires_a_new_context_receipt(game, framework, tmp_path):
    started(game, framework, plan("raise SystemExit(1)"))
    for _ in range(2): tasks.update(game, "input-fix", "run")
    source = tmp_path / "findings.md"
    source.write_text("Observed GUI consumes the input before capture.", encoding="utf-8")
    data = tasks.update(game, "input-fix", "research", source=source, next_action="Inspect GUI propagation")
    rendered = (tasks.location(game, "input-fix") / "context.md").read_text(encoding="utf-8")
    assert "Observed GUI consumes" in rendered and "Inspect GUI propagation" in rendered
    assert "untrusted source data" in rendered and data["ack"] is None
    with pytest.raises(Refused, match="acknowledged"):
        tasks.update(game, "input-fix", "run")
    tasks.update(game, "input-fix", "ack", digest=data["context_sha256"])
    assert len(tasks.update(game, "input-fix", "run")["attempts"]) == 3


def test_research_cannot_silently_overflow_context(game, framework, tmp_path):
    started(game, framework)
    source = tmp_path / "long-source.md"
    source.write_text("Large evidence " * 2000, encoding="utf-8")
    before = (tasks.location(game, "input-fix") / "context.md").read_bytes()
    with pytest.raises(Refused, match="budget"):
        tasks.update(game, "input-fix", "research", source=source, next_action="Read a bounded source")
    assert (tasks.location(game, "input-fix") / "context.md").read_bytes() == before


@pytest.mark.parametrize("value", [{}, {"checks": []}, {"checks": [{"id": "bad", "argv": "echo OK"}]}])
def test_invalid_plans_are_rejected(game, framework, value):
    with pytest.raises(Refused): tasks.begin(game, "bad", "Goal", "code", value, framework)
