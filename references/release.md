# Game release loop

Start with the current playable project and its target platform. Confirm export
presets and matching Godot templates. Run the project's mechanism tests, export
to a game-owned output directory, then launch the actual exported artifact.
An editor run is not evidence that the exported build works.

Keep platform-specific store text, screenshots, icons, attribution and input
instructions in the game. Check the actual platform's current packaging and
store requirements. Retain a manifest of engine version, source revision,
artifact hash, export command and launch outcome.

Create a task whose argv checks call the project's export and artifact-smoke
scripts. Include a review for visual/store-facing changes. Publishing to a store
or uploading a game requires the user's authorization for that action; a local
export command does not publish anything.

After release, collect actual player feedback and reproduction details in the
game. Separate taste/preferences from reproducible faults. General framework
failures can enter the evolution loop; game-specific balance, plot and art do
not become universal rules.

ai4gd 2 does not bundle a store uploader, export template installer or a complete
asset-production pipeline. Project scripts and optional external tools remain
task checks. This keeps platform services and credentials outside the core.
