# Implement and verify game behavior

Before editing, inspect project instructions, Git changes, the Godot version,
main scene and the behavior the player should observe. Keep the existing
architecture. Choose only the relevant source files and engine documentation.

Define an acceptance check before implementation. A check should distinguish
the reported failure from success: a mouse test moves and recaptures the cursor;
a speed test measures distance over simulation time; a save test reloads known
values. Avoid tests that merely match source text or repeat the implementation.

Use `task PROJECT ID begin --goal ... --focus ... --plan FILE` with a JSON plan:
`checks` is a nonempty array of unique `id`, `argv`, optional `timeout`, optional
exact stdout `expect`; `review_required` is a boolean. Read `context.md`, modify
the project, `refresh`, read again, acknowledge its SHA-256, then `run`.
All listed checks execute and all must pass for current inputs.

For UI or visual interaction, set `review_required: true`. Run the game with a
rendering window, exercise the changed interaction and record what was observed.
Attach the record with `task PROJECT ID review --reviewer NAME --source FILE
--passed`. A self-review must say so; the named review is an attestation, not
an automatically proven independent assessment. A changed review record expires.

`close` captures raw task observations into an unreviewed L3 inbox. It does not
derive causes, overwrite stable project knowledge or change framework rules.
Use `abandon --reason ...` when stopping; retain failed attempts.

## Godot checks

`check PROJECT --godot EXECUTABLE` imports the project and checks engine output.
It recognizes script/parse errors even when the engine returns zero. Errors
remain errors, including resource leaks reported as `ERROR:`; this independent
version does not blanket-exempt shutdown diagnostics.

`check PROJECT --godot EXECUTABLE --script res://test/driver.gd --expect MARKER`
runs a standalone SceneTree/MainLoop driver. The driver must quit itself. A
timeout or absent exact marker fails. File inheritance and imported global
classes are checked before launch; unconfirmed inheritance is refused instead
of risking a native error dialog. Node scripts use a scene driver; gdUnit suites
use their installed runner. No testing addon is installed automatically.

Use the sample [scene driver](../examples/check_scene.py) as a loader smoke test,
then add project-specific assertions. Unit testing libraries, real-input E2E
drivers and screenshot tools can be added to a task's argv checks without
changing ai4gd's task engine.

Check import → relevant mechanism → real interaction/visual review. Do not call
a headless load a player test. Confirm keyboard focus, mouse escape/reacquire,
pause/resume and loading transitions when those paths change. Release and
physics checks should use the target platform and project time step.
