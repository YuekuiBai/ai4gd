"""Load the configured main scene for two frames; this is not a gameplay test."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai4gd.godot import check, project

game = project(Path(sys.argv[1]))
driver = game / ".ai4gd/scene-smoke.gd"
driver.parent.mkdir(parents=True, exist_ok=True)
driver.write_text('''extends SceneTree
func _initialize() -> void:
    call_deferred("smoke")
func smoke() -> void:
    var entry: String = ProjectSettings.get_setting("application/run/main_scene", "")
    if entry.is_empty():
        push_error("No main scene configured")
        quit(2)
        return
    var packed = load(entry)
    if not packed is PackedScene:
        push_error("Main scene is not a PackedScene")
        quit(2)
        return
    var instance = packed.instantiate()
    root.add_child(instance)
    await process_frame
    await process_frame
    instance.queue_free()
    await process_frame
    print("SCENE_REGRESSION_COMPLETE")
    quit(0)
''', encoding="utf-8")
result = check(game, sys.argv[2], script="res://.ai4gd/scene-smoke.gd", expected="SCENE_REGRESSION_COMPLETE")
if not result["passed"]:
    print(result)
    raise SystemExit(1)
print("SCENE_REGRESSION_COMPLETE")
