from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import pytest

from ai4gd import knowledge
from ai4gd.storage import Refused, read, write


def catalog(root):
    write(root / "config/sources.json", {"allowed_hosts": ["example.org"], "sources": [
        {"id": "original", "url": "https://example.org/docs", "read_url": "https://example.org/{version}", "review_days": 7}]})


def fetched(root):
    catalog(root)
    return knowledge.learn(root, "4.7", online=True, transport=lambda *a, **k: b"Original public developer source")


def test_learning_is_offline_by_default_and_does_not_promote(framework):
    catalog(framework)
    data = knowledge.learn(framework, "4.7")
    assert data["results"][0]["status"] == "due"
    assert not (framework / ".ai4gd/knowledge/learning.json").exists()
    fetched(framework)
    record = read(framework / ".ai4gd/knowledge/learning.json")["entries"]["original@4.7"]
    assert record["review"] == "unreviewed" and record["visibility"] == "public"
    assert knowledge.learn(framework, "4.7")["due_count"] == 0


def test_research_version_isolation_and_public_only_indexing(framework, tmp_path):
    fetched(framework)
    assert knowledge.public_documents(framework, "4.6") == []
    docs = knowledge.public_documents(framework, "4.7")
    assert len(docs) == 1 and docs[0]["payload"]["version"] == "4.7"
    state = read(framework / ".ai4gd/knowledge/learning.json")
    item = state["entries"]["original@4.7"]
    item["visibility"] = "private"
    write(framework / ".ai4gd/knowledge/learning.json", state)
    assert knowledge.public_documents(framework, "4.7") == []


def test_changed_source_returns_to_review_and_has_backoff(framework):
    fetched(framework)
    knowledge.review(framework, "original@4.7", "noop", "No relevant change")
    path = framework / ".ai4gd/knowledge/learning.json"
    state = read(path)
    state["entries"]["original@4.7"]["next_review"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    write(path, state)
    knowledge.learn(framework, "4.7", online=True, transport=lambda *a, **k: b"Different original source")
    assert read(path)["entries"]["original@4.7"]["review"] == "unreviewed"


def test_source_tampering_or_external_cache_path_refused(framework, tmp_path):
    fetched(framework)
    path = framework / ".ai4gd/knowledge/learning.json"
    state = read(path)
    item = state["entries"]["original@4.7"]
    Path(item["file"]).write_text("tampered", encoding="utf-8")
    with pytest.raises(Refused): knowledge.public_documents(framework, "4.7")
    external = tmp_path / "private.txt"
    external.write_text("private project", encoding="utf-8")
    item.update(file=str(external), sha256=sha256(external.read_bytes()).hexdigest())
    write(path, state)
    with pytest.raises(Refused, match="outside"): knowledge.public_documents(framework, "4.7")


@pytest.mark.parametrize("url", ["http://example.org/data", "https://user:password@example.org/data", "file:///etc/passwd"])
def test_invalid_remote_urls_are_refused_without_network(url):
    with pytest.raises(Refused): knowledge.request(url)


def test_cloud_requires_explicit_configuration(monkeypatch):
    monkeypatch.delenv("QDRANT_CLOUD_URL", raising=False)
    monkeypatch.delenv("QDRANT_CLOUD_API_KEY", raising=False)
    with pytest.raises(Refused): knowledge.Qdrant("cloud")


class Embedded:
    profile = "unit-test-profile"
    dimension = 2
    def encode(self, texts, query=False):
        return [[1.0, 0.0] for _ in texts]


class Client:
    def __init__(self, points=None):
        self.calls, self.points = [], points or []
    def call(self, path, body=None, method="GET"):
        self.calls.append((path, body, method))
        if path == "/collections": return {"result": {"collections": []}}
        if path.endswith("/points/query"): return {"result": {"points": self.points}}
        return {"result": {"status": "completed"}}


def test_index_records_only_after_upload_and_retires_old_revisions(framework):
    fetched(framework)
    client = Client()
    result = knowledge.index(framework, "4.7", "cloud", Embedded(), client)
    assert result["points"] == 1
    upsert = next(call for call in client.calls if "/points?" in call[0])
    payload = upsert[1]["points"][0]["payload"]
    assert payload["visibility"] == "public" and "file" not in payload
    assert client.calls[-1][0].endswith("/points/delete?wait=true")
    assert (framework / ".ai4gd/knowledge/index-cloud.json").is_file()


def test_failed_upload_does_not_write_success_receipt(framework):
    fetched(framework)
    class Failing(Client):
        def call(self, path, body=None, method="GET"):
            if "/points?" in path: raise OSError("offline")
            return super().call(path, body, method)
    with pytest.raises(OSError): knowledge.index(framework, "4.7", "local", Embedded(), Failing())
    assert not (framework / ".ai4gd/knowledge/index-local.json").exists()


def test_federated_results_deduplicate_and_preserve_sources():
    point = {"payload": {"source_id": "input", "sha256": "abc", "text": "Mouse capture", "visibility": "public", "version": "4.7"}}
    result = knowledge.retrieve("mouse", "4.7", ["local", "cloud"], embedder=Embedded(), clients={"local": Client([point]), "cloud": Client([point])})
    assert len(result["results"]) == 1
    assert result["results"][0]["targets"] == ["local", "cloud"]


def test_federation_degrades_when_one_database_is_unavailable():
    point = {"payload": {"source_id": "input", "sha256": "abc", "text": "Mouse capture", "visibility": "public", "version": "4.7"}}
    class Unavailable(Client):
        def call(self, *args): raise OSError("database unavailable")
    result = knowledge.retrieve("mouse", "4.7", ["local", "cloud"], embedder=Embedded(), clients={"local": Client([point]), "cloud": Unavailable()})
    assert result["passed"] and result["failures"][0]["target"] == "cloud"


def test_document_navigation_and_scripts_do_not_enter_embeddings():
    raw = b'<html><head><title>Shell</title></head><body><nav>Repeated navigation</nav><div role="main"><h1>Input handling</h1><p>Capture &amp; release</p><script>untrusted()</script></div><footer>Site footer</footer></body></html>'
    selected = knowledge.source_text(raw)
    assert "Input handling" in selected and "Capture & release" in selected
    assert all(noise not in selected for noise in ["Repeated navigation", "untrusted()", "Site footer", "Shell"])


def test_plain_html_fallback_skips_navigation_without_requiring_main():
    assert knowledge.source_text(b'<nav>Noise</nav><p>Original post</p>') == "Original post"


def test_commit_feeds_keep_actual_changes_and_original_urls():
    raw = json.dumps([{"sha": "abc", "commit": {"message": "Fixed input routing", "committer": {"date": "2026-10-25"}},
                       "html_url": "https://example.org/commit/abc", "author": {"avatar_url": "noisy-avatar"}}]).encode()
    text = knowledge.source_text(raw)
    assert "Fixed input routing" in text and "https://example.org/commit/abc" in text
    assert "noisy-avatar" not in text
