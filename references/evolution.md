# Evolve from a demonstrated failure

Improvement aims to prevent repeated failures, not accumulate rules. Use task
observations, experiments, player reports or external research to identify a
specific trigger. An unreviewed report or upstream README alone is insufficient
to make a technical rule. Reproduce the issue or record independent supporting
sources and applicability. Game-specific content stays in the game.

Prefer changing the nearest existing instruction or tool. Remove obsolete
guidance and check callers before combining duplicates. Skill files have a
16 KiB UTF-8 byte budget; selected task context has a separate limit. Byte
counts are not model token counts. Exact duplicate files are review candidates,
not an automatic deletion list.

Propose **before** editing maintained source. The measured source record should
contain reproduction steps, actual results, versions and the expected change:

```bash
python -m ai4gd evolve fix-id propose --target ai4gd/godot.py --target tests/test_godot.py --target references/changes.md --source /path/to/reproduction.json --trigger "Specific repeated failure" --lesson "Bounded proposed correction"
```

Targets are individual files, constrained to the selected framework root. The
proposal snapshots their original bytes and the complete source inventory.
Runtime state is excluded. Verification refuses edits outside declared targets
and refuses a no-change candidate; record NOOP learning decisions instead.

After implementation, write the command for a relevant existing game's
regression as a JSON argv array in a file outside maintained source:

```bash
python -m ai4gd evolve fix-id verify --project /path/to/game --regression /path/to/regression.json
python -m ai4gd evolve fix-id accept --decision "Current user authorization and applicability reviewed"
# If the changed source should be restored:
python -m ai4gd evolve fix-id rollback
```

Verification actually runs release/source audit, framework tests and the game
regression. Each attempt has its own directory. Acceptance requires current
framework and game inputs, intact logs and unchanged proposal evidence. Rollback
checks current target bytes and all original snapshots before touching any file.
A concurrent edit blocks rollback; it never resets the repository.

Proposal evidence and decisions require human/model judgment. Hashes do not
establish source independence or the relevance of a regression. A trivially
successful command is not a meaningful game test. The current runner validates
structure and freshness, not the semantic quality of submitted commands.

For instruction changes, compare the same small tasks before and after with the
same engine, model and evaluation criteria. Retain failures and report coverage,
task success and context cost separately. No benchmark improvement is claimed
until those controlled comparisons have actually run. Capability drift, stale
knowledge and repeated task failures suggest what to test next.
