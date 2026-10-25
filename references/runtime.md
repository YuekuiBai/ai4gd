# Capabilities and state

Required capabilities are reading/writing files and executing Python. Game checks
also need the project's Godot executable. Image generation, visual inspection,
MCP, persistent agent memory and subagents are optional. If unavailable, report
the corresponding evidence as missing; do not impersonate a reviewer or tool.

Use the same CLI from every host. `--root` selects framework source and explicit
project arguments select the game. No host SDK, remote model or local daemon is
required. MCP implementations can wrap these commands; they are not part of the
core. The source-pointer registration is optional and requires an explicit path.

| Data | Location |
|---|---|
| Framework source and reusable instructions | This repository |
| Game source, assets and acceptance tests | Game project |
| Source binding | `<game>/.ai4gd/engine.json` |
| Context, checks and task history | `<game>/.ai4gd/tasks/` |
| Raw lesson observations | `<game>/.ai4gd/lessons.json` |
| Framework proposals and snapshots | `<framework>/.ai4gd/evolution/` |
| Fetched public knowledge and database receipts | `<framework>/.ai4gd/knowledge/` |

State updates use exclusive filesystem locks. An abandoned lock is not stolen
automatically: inspect the recorded PID before removing the lock file. Locks
serialize ai4gd operations; they cannot prevent an unrelated editor changing a
file. Input digests detect such changes before completion or rollback.

Checks execute argv arrays directly with a timeout. Their stdout, stderr and
execution metadata are retained and hashed. These records attest to what ran;
they cannot attest that the checks were well designed or the model understood
the context. No core command commits, publishes, deletes a game or installs a
global configuration.
