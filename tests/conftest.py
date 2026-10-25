from pathlib import Path
import json
import pytest


@pytest.fixture
def game(tmp_path):
    folder = tmp_path / "game"
    folder.mkdir()
    (folder / "project.godot").write_text('config_version=5\n[application]\nconfig/name="ai4gd test"\nrun/main_scene="res://main.tscn"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding="utf-8")
    (folder / "main.tscn").write_text('[gd_scene format=3]\n[node name="Root" type="Node"]\n', encoding="utf-8")
    return folder


@pytest.fixture
def framework(tmp_path):
    root = tmp_path / "framework"
    (root / "config").mkdir(parents=True)
    (root / "SKILL.md").write_text("Read this complete test context.", encoding="utf-8")
    (root / "config/routes.json").write_text(json.dumps({"max_context_bytes": 10000,
        "base": ["SKILL.md"], "focus": {"code": ["SKILL.md"], "ui": ["SKILL.md"]}}), encoding="utf-8")
    return root
