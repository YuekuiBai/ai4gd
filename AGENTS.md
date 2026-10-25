# Maintain ai4gd

Read [SKILL.md](SKILL.md), then only the reference needed for this task.
Keep the core independent of any coding-agent SDK, hosted model or editor plugin.
Subagents and visual tools are optional capabilities and require the current
user's authorization where applicable. A missing capability remains unverified.

Keep game code, assets and screenshots in the game project. Runtime records,
retrieval caches and proposal snapshots belong in ignored `.ai4gd/` directories.
Never copy the previous local framework or a third-party skill library into this
MIT source tree. New contributions must have a compatible, documented origin.

Preserve concurrent edits. Use task contracts for game changes and measured,
bounded evolution proposals for framework fixes. Independent review requires
another reviewer; self-review must be identified as self-review.

Run `python -m ai4gd audit --release` and `python -m pytest tests -q` after changes.
Use a real Godot regression for changes affecting engine execution. Record
meaningful behavior changes in [references/changes.md](references/changes.md).
Commands do not commit, upload files, register global hooks or publish games.
An explicit user request to publish the framework authorizes that separate step.
