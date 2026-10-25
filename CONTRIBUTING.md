# Contributing

Open an issue with the Godot/Python versions, a minimal reproduction, expected
behavior and actual results. Remove credentials, private project paths and
proprietary game content before sharing logs.

Keep changes focused and compatible with Python 3.10+. Core operations must not
require a particular coding agent, external model, MCP server or background
service. Optional integrations belong behind explicit commands.

Contribute only material you may distribute under this repository's MIT license.
Do not import the previous local framework or restricted third-party code,
skills, templates or manuals. Learning a general method does not grant a right
to copy its implementation. Document external runtime dependencies and source
attribution where relevant.

For a fix, provide a test that fails for the reported behavior, run the relevant
checks and update [changes](references/changes.md). Instruction changes benefit
from a realistic task evaluation; static validation alone does not prove the
instructions improve model behavior.

```bash
python -m pip install "pytest>=8,<9"
python -m ai4gd audit --release
python -m pytest tests -q
```

Set `GODOT_BIN` for opt-in real-engine checks. Report skipped and unrun checks.
Windows and Linux CI runs are independent evidence; a locally passing Windows
run does not imply Linux passed. PRs should explain the trigger, resulting
behavior, evidence and material compatibility limits.
