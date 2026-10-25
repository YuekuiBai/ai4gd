# Origin and third-party boundaries

ai4gd 2 is a new implementation written for this repository. Its Python modules,
skill instructions, configuration, tests and documentation are distributed under
the MIT license in [LICENSE](LICENSE).

The preceding local ai4godotdev/godotai framework incorporated third-party
material. That source tree, its Git history, Godot documentation mirror,
templates, hooks and role library are **not included** in this distribution.
Version 2 is a smaller successor with an intentionally different command API;
this notice does not relicense any earlier distribution.

Design research included the public descriptions of
[GodotPrompter](https://github.com/jame581/GodotPrompter),
[Godogen](https://github.com/htdt/godogen),
[Godai](https://godai.sh/), and
[Godot MCP Toolkit](https://github.com/NPGameDev/godot-mcp-toolkit).
These are learning references, not bundled source or dependencies.
[GodotMaker](https://github.com/RandallLiuXin/GodotMaker) informed earlier local
work; its BUSL source, prompts and documentation are excluded from this release.

Godot and Qdrant are separately installed products. Optional sentence-transformers
and embedding model downloads retain their own licenses; installing or querying
them does not include their source or weights in this repository. Public source
text fetched during learning remains attributed to its source and is stored in
ignored local state, not redistributed as part of the MIT framework.

No endorsement or affiliation by these projects is claimed. Exact-file matching
and automated scans assist review; they do not establish copyright ownership.
