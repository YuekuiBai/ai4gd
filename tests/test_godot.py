import os
from pathlib import Path
import subprocess
import sys
import pytest

from ai4gd import godot
from ai4gd.storage import Refused


@pytest.mark.parametrize("parent", ["Node", "Node3D", "GdUnitTestSuite", "Resource", "RefCounted"])
def test_non_mainloop_scripts_are_refused_before_launch(game, parent):
    (game / "suite.gd").write_text("extends " + parent + "\n", encoding="utf-8")
    with pytest.raises(Refused): godot.script_entry(game, "res://suite.gd")
    assert not (game / ".ai4gd/runs").exists()


@pytest.mark.parametrize("parent", ["SceneTree", "MainLoop"])
def test_valid_file_inheritance(game, parent):
    (game / "base.gd").write_text("extends " + parent + "\n", encoding="utf-8")
    (game / "entry.gd").write_text('extends "base.gd"\n', encoding="utf-8")
    godot.script_entry(game, "res://entry.gd")


def test_imported_global_class_and_cycle(game):
    (game / "base.gd").write_text("extends SceneTree\n", encoding="utf-8")
    (game / "entry.gd").write_text("extends Driver\n", encoding="utf-8")
    (game / ".godot").mkdir()
    (game / ".godot/global_script_class_cache.cfg").write_text('list=[{ "class": &"Driver", "path": "res://base.gd" }]', encoding="utf-8")
    godot.script_entry(game, "res://entry.gd")
    (game / "base.gd").write_text('extends "entry.gd"\n', encoding="utf-8")
    with pytest.raises(Refused, match="cyclic"): godot.script_entry(game, "res://entry.gd")


def test_script_error_is_not_hidden_by_zero_exit_or_shutdown_noise():
    text = 'Godot Engine\nWARNING: shutdown note\nSCRIPT ERROR: Parse Error: invalid symbol\nERROR: Failed to load script\n'
    assert len(godot.diagnostics(text)) == 2
    assert godot.diagnostics('Godot Engine\nWARNING: note\n') == []


@pytest.mark.godot
@pytest.mark.skipif(not os.environ.get("GODOT_BIN"), reason="Set GODOT_BIN for an actual engine check")
def test_actual_godot_import_scene_and_script_error(game):
    binary = os.environ["GODOT_BIN"]
    assert godot.check(game, binary)["passed"]
    sample = Path(__file__).resolve().parents[1] / "examples/check_scene.py"
    result = subprocess.run([sys.executable, str(sample), str(game), binary], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    (game / "broken.gd").write_text('extends SceneTree\nfunc _initialize() -> void:\n    unknown_function()\n', encoding="utf-8")
    failure = godot.check(game, binary, script="res://broken.gd", expected="NOT_REACHED")
    assert not failure["passed"] and failure["errors"]
