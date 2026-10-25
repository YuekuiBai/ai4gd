# Changes

## 2.0.0 · public source extraction

An actual Godot documentation fetch produced 1168 raw HTML/feed fragments, mostly
page navigation. Indexing now extracts article content and commit facts while
retaining original bytes and hashes. The extraction/chunk contract participates
in collection identity. Cached CPU embeddings use bounded threads; the newer
embedding dimension API is used when available.

## 2.0.0 · research context correction

A reproduced retry loop showed that a research attachment could unlock another
attempt while the selected model context still lacked the finding and changed
action. Research now regenerates the bounded context, labels source text as
untrusted evidence and invalidates the old receipt. Tests cover delivery, fresh
acknowledgment and oversized input without partial context replacement.

## 2.0.0 · 2026-10-25

Independent MIT implementation replacing third-party-derived local framework
distribution. Adds a host-neutral JSON CLI, bounded task context and checks,
lesson inbox, inventory-scoped evolution, guarded rollback, Godot script-entry
checks, source audit, versioned source learning and optional local/cloud Qdrant.

The previous pipeline, assets, prompts, documentation mirror and history are
excluded. See [migration boundaries](design.md). Validation results are recorded
in [validation](validation.md); unrun environments are not claimed as passing.
