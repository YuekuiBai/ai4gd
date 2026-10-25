# Independent edition: architecture and migration

The 2.0 implementation uses one Python package, one skill entry, explicit context
routes and a small reference library. Filesystem/evidence primitives are shared
by task and evolution commands. Knowledge clients are optional; their dependencies
are imported only on vector operations. Host discovery produces source pointers.

The previous local framework had a much larger staged pipeline and third-party
lineage. Version 2 does not import, transform, rename or redistribute its source,
templates, role prompts, documentation mirror, addon versions or Git history.
Its commands and records are intentionally not represented as compatible v1 APIs.

| Previous capability | Version 2 treatment |
|---|---|
| Game task checks, evidence and observation capture | New task state machine and CLI |
| Bounded evolution, regression and rollback | New inventory-based implementation |
| Host-specific discovery/runtime | Explicit pointer registration; host-independent CLI |
| Public-source learning and Qdrant | New optional clients and versioned review inbox |
| ECS stages, asset generators, addon installers, store helpers | Not bundled; existing project scripts may be task checks |
| Godot reference mirror | Original documentation URLs, no vendored mirror |
| Existing game data and .ai4gd history | Left in place; not rewritten or uploaded |

For migration, keep the previous source available while an active game depends
on it. Try version 2 on a copy first. To bind a project explicitly:

```bash
python -m ai4gd init /path/to/game --rebind
```

This changes only the source binding. It does not migrate historical task JSON,
make previous scripts understand new interfaces or replace host registration.
Use a new task id, update the relevant calling command and validate the game
before changing your host's discovery pointer. Do not switch an active parallel
agent's source path without coordinating with its user-approved workflow.

GitHub publication uses only this independent source tree. Local credential
stores, original repositories, game files and runtime logs are outside the
publishable set. The source audit checks likely credentials and local-state paths;
it does not audit arbitrary prior Git history, so only reviewed history is pushed.

Contributions should keep one canonical implementation per operation. Add a
reference when a real task needs guidance; add a module when repeated executable
behavior warrants it. Measure budgets and task behavior before adding roles,
wrappers or another state ledger.
