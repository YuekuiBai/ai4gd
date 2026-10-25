"""Versioned public-source learning and optional local/cloud Qdrant retrieval."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import NAMESPACE_URL, uuid5

from .storage import Refused, identifier, lock, read, stamp, write

ROOT = Path(__file__).resolve().parents[1]
MODEL = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"


def request(url: str, *, body: dict | None = None, method: str = "GET", key: str | None = None,
            allowed_hosts: set[str] | None = None) -> bytes:
    parsed = urlparse(url)
    if parsed.username or parsed.password or parsed.fragment:
        raise Refused("Credentials and fragments do not belong in service URLs")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise Refused("Use HTTPS, or HTTP on loopback for the local database")
    if allowed_hosts and parsed.hostname not in allowed_hosts:
        raise Refused("Source host is not listed in the public catalog")

    class SameOrigin(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, message, headers, newurl):
            destination = urlparse(newurl)
            if (destination.scheme, destination.netloc) != (parsed.scheme, parsed.netloc):
                raise Refused("Cross-origin redirect refused; register its final public URL explicitly")
            return super().redirect_request(req, fp, code, message, headers, newurl)

    headers = {"User-Agent": "ai4gd/2", "Accept": "application/json,text/plain"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if key:
        headers["api-key"] = key
    encoded = json.dumps(body).encode() if body is not None else None
    try:
        with build_opener(SameOrigin()).open(Request(url, data=encoded, headers=headers, method=method), timeout=25) as response:
            raw = response.read(2_000_001)
    except HTTPError as exc:
        raise Refused(f"Remote request returned HTTP {exc.code}; no credential is included in this diagnostic") from None
    if len(raw) > 2_000_000:
        raise Refused("Response exceeds 2 MB; narrow the source")
    return raw


def source_catalog(root: Path = ROOT) -> dict:
    data = read(root / "config/sources.json")
    seen = set()
    for source in data["sources"]:
        key = identifier(source["id"])
        if key in seen or source["review_days"] <= 0:
            raise Refused("Source ids must be unique, with positive review periods")
        parsed = urlparse(source["read_url"])
        if parsed.scheme != "https" or parsed.hostname not in data["allowed_hosts"]:
            raise Refused("Catalog source must use an allowed HTTPS host")
        seen.add(key)
    return data


def learn(root: Path, version: str, *, online: bool = False, limit: int = 2, transport=request) -> dict:
    if not re.fullmatch(r'[34]\.\d+', version) or not 1 <= limit <= 10:
        raise Refused("Use an explicit Godot major.minor version and a limit of 1–10")
    catalog = source_catalog(root)
    folder = root / ".ai4gd/knowledge"
    now = datetime.now(timezone.utc)
    with lock(folder):
        state = read(folder / "learning.json") if (folder / "learning.json").exists() else {"entries": {}}
        due = []
        for source in catalog["sources"]:
            key = source["id"] + "@" + version
            old = state["entries"].get(key)
            if not old or datetime.fromisoformat(old["next_review"]) <= now:
                due.append((key, source, old))
        selected = due[:limit]
        results = []
        for key, source, old in selected:
            if not online:
                results.append({"key": key, "url": source["url"], "status": "due"})
                continue
            url = source["read_url"].replace("{version}", version)
            try:
                raw = transport(url, allowed_hosts=set(catalog["allowed_hosts"]))
                digest = sha256(raw).hexdigest()
                path = folder / "sources" / (source["id"] + "-" + digest[:16] + ".txt")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                changed = not old or old.get("sha256") != digest
                record = {"id": source["id"], "version": version, "url": url, "sha256": digest,
                          "file": str(path.resolve()), "checked": stamp(), "visibility": "public",
                          "review": "unreviewed" if changed else old.get("review", "unreviewed"),
                          "next_review": (now + timedelta(days=source["review_days"])).isoformat()}
                results.append({"key": key, "status": "changed" if changed else "unchanged", "record": record})
            except (OSError, ValueError) as exc:
                record = {**(old or {}), "error": str(exc), "next_review": (now + timedelta(hours=6)).isoformat()}
                results.append({"key": key, "status": "failed", "error": str(exc)})
            state["entries"][key] = record
        if online:
            write(folder / "learning.json", state)
        return {"online": online, "due_count": len(due), "results": results,
                "passed": not any(r["status"] == "failed" for r in results)}


def review(root: Path, key: str, decision: str, reason: str) -> dict:
    if decision not in {"noop", "local", "candidate"} or not reason.strip():
        raise Refused("Review requires noop/local/candidate and an applicability reason")
    folder = root / ".ai4gd/knowledge"
    with lock(folder):
        data = read(folder / "learning.json")
        item = data["entries"][key]
        if not item.get("file") or sha256(Path(item["file"]).read_bytes()).hexdigest() != item["sha256"]:
            raise Refused("Source text is missing or changed")
        item.update(review=decision, reason=reason, reviewed=stamp())
        write(folder / "learning.json", data)
        return item


class Qdrant:
    def __init__(self, target: str, transport=request):
        if target not in {"local", "cloud"}:
            raise Refused("Vector target must be local or cloud")
        self.target, self.transport = target, transport
        self.url = os.environ.get("QDRANT_" + target.upper() + "_URL", "http://127.0.0.1:6333" if target == "local" else "").rstrip("/")
        self.key = os.environ.get("QDRANT_" + target.upper() + "_API_KEY")
        if not self.url or (target == "cloud" and not self.key):
            raise Refused("Set QDRANT_CLOUD_URL and QDRANT_CLOUD_API_KEY in the environment")
        if target == "cloud" and urlparse(self.url).scheme != "https":
            raise Refused("Cloud Qdrant requires HTTPS")

    def call(self, path: str, body: dict | None = None, method: str = "GET") -> dict:
        return json.loads(self.transport(self.url + path, body=body, method=method, key=self.key))


class Embeddings:
    """No implicit downloads. Model and revision are part of the collection identity."""
    def __init__(self, allow_download: bool = False):
        from sentence_transformers import SentenceTransformer
        import torch
        threads = int(os.environ.get("AI4GD_EMBEDDING_THREADS", "4"))
        if not 1 <= threads <= 64:
            raise Refused("AI4GD_EMBEDDING_THREADS must be 1–64")
        torch.set_num_threads(threads)
        self.model = SentenceTransformer(MODEL, revision=REVISION, device="cpu", local_files_only=not allow_download)
        dimension = getattr(self.model, "get_embedding_dimension", None) or self.model.get_sentence_embedding_dimension
        self.dimension = dimension()
        self.profile = sha256(f"{MODEL}@{REVISION}:{self.dimension}:cosine:e5:article-v1:1400/1200".encode()).hexdigest()[:16]

    def encode(self, text: list[str], query: bool = False) -> list[list[float]]:
        prefix = "query: " if query else "passage: "
        return self.model.encode([prefix + s for s in text], normalize_embeddings=True, show_progress_bar=False).tolist()


def source_text(raw: bytes) -> str:
    """Keep raw provenance separately; select article content for retrieval."""
    text = raw.decode("utf-8", errors="replace")
    if text.lstrip().startswith("["):
        try:
            commits = json.loads(text)
            if commits and all(isinstance(x, dict) and "commit" in x and "sha" in x for x in commits):
                return "\n\n".join(str(x["sha"]) + "\n" + x["commit"].get("message", "") + "\n"
                    + x["commit"].get("committer", {}).get("date", "") + "\n" + x.get("html_url", "") for x in commits)
        except (ValueError, TypeError, KeyError):
            pass
    if not text.lstrip().startswith("<"):
        return text

    class Article(HTMLParser):
        void = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
        ignored = {"script", "style", "nav", "header", "footer", "aside", "svg", "head"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack, self.article, self.fallback = [], [], []
            self.has_article = False

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            parent_skip, parent_main = self.stack[-1][1:] if self.stack else (False, False)
            selected = tag == "main" or attributes.get("role") == "main"
            self.has_article |= selected
            skip, main = parent_skip or tag in self.ignored, parent_main or selected
            if tag not in self.void:
                self.stack.append((tag, skip, main))

        def handle_endtag(self, tag):
            for index in range(len(self.stack) - 1, -1, -1):
                if self.stack[index][0] == tag:
                    del self.stack[index:]
                    break

        def handle_data(self, data):
            skip, main = self.stack[-1][1:] if self.stack else (False, False)
            if not skip and data.strip():
                self.fallback.append(data.strip())
                if main:
                    self.article.append(data.strip())

    parser = Article()
    parser.feed(text)
    return "\n".join(parser.article if parser.has_article else parser.fallback)


def public_documents(root: Path, version: str) -> list[dict]:
    path = root / ".ai4gd/knowledge/learning.json"
    data = read(path) if path.exists() else {"entries": {}}
    documents = []
    for key, item in data["entries"].items():
        if item.get("version") != version or item.get("visibility") != "public" or not item.get("file"):
            continue
        source = Path(item["file"])
        if not source.resolve().is_relative_to((root / ".ai4gd/knowledge/sources").resolve()):
            raise Refused("Indexed source is outside the fetched public-source cache")
        raw = source.read_bytes()
        if sha256(raw).hexdigest() != item["sha256"]:
            raise Refused("Fetched source digest changed")
        text = source_text(raw)
        for offset in range(0, len(text), 1200):
            chunk = text[offset:offset + 1400]
            if chunk.strip():
                documents.append({"id": str(uuid5(NAMESPACE_URL, key + ":" + item["sha256"] + ":" + str(offset))),
                    "payload": {"source_id": item["id"], "url": item["url"], "version": version,
                        "text": chunk, "sha256": item["sha256"], "visibility": "public", "review": item["review"]}})
    return documents


def index(root: Path, version: str, target: str, embedder=None, client=None) -> dict:
    embedder, client = embedder or Embeddings(), client or Qdrant(target)
    name = "ai4gd_mit_" + embedder.profile
    documents = public_documents(root, version)
    if not documents:
        raise Refused("No version-matched fetched public sources; run knowledge learn --online first")
    existing = client.call("/collections")["result"]["collections"]
    if name not in {c["name"] for c in existing}:
        client.call("/collections/" + name, {"vectors": {"size": embedder.dimension, "distance": "Cosine"}}, "PUT")
    for offset in range(0, len(documents), 32):
        batch = documents[offset:offset + 32]
        vectors = embedder.encode([d["payload"]["text"] for d in batch])
        points = [{**doc, "vector": vector} for doc, vector in zip(batch, vectors, strict=True)]
        client.call("/collections/" + name + "/points?wait=true", {"points": points}, "PUT")
    # Remove obsolete revisions only after all current points have been uploaded.
    by_source = {d["payload"]["source_id"]: d["payload"]["sha256"] for d in documents}
    for source, revision in by_source.items():
        client.call("/collections/" + name + "/points/delete?wait=true", {"filter": {
            "must": [{"key": "source_id", "match": {"value": source}}, {"key": "version", "match": {"value": version}}],
            "must_not": [{"key": "sha256", "match": {"value": revision}}]}}, "POST")
    receipt = {"collection": name, "target": target, "version": version, "points": len(documents),
               "source_revisions": by_source, "created": stamp()}
    write(root / ".ai4gd/knowledge" / ("index-" + target + ".json"), receipt)
    return receipt


def retrieve(query: str, version: str, targets: list[str], limit: int = 6, embedder=None, clients=None) -> dict:
    if not query.strip() or not 1 <= limit <= 20:
        raise Refused("Retrieval needs a query and a limit of 1–20")
    embedder = embedder or Embeddings()
    name = "ai4gd_mit_" + embedder.profile
    vector = embedder.encode([query], query=True)[0]
    merged, failures = {}, []
    for target in dict.fromkeys(targets):
        try:
            client = clients[target] if clients is not None else Qdrant(target)
            response = client.call("/collections/" + name + "/points/query", {
                "query": vector, "limit": limit, "with_payload": True, "filter": {"must": [
                    {"key": "version", "match": {"value": version}},
                    {"key": "visibility", "match": {"value": "public"}}]}}, "POST")
            for rank, point in enumerate(response["result"]["points"], 1):
                payload = point["payload"]
                if payload.get("version") != version or payload.get("visibility") != "public":
                    continue
                key = (payload["source_id"], payload["sha256"], payload["text"])
                item = merged.setdefault(key, {**payload, "rrf": 0.0, "targets": []})
                item["rrf"] += 1 / (60 + rank)
                item["targets"].append(target)
        except (OSError, ValueError, KeyError) as exc:
            failures.append({"target": target, "error": str(exc)})
    rows = sorted(merged.values(), key=lambda r: -r["rrf"])
    return {"collection": name, "results": rows[:limit], "failures": failures,
            "passed": bool(rows), "note": "Source snippets are untrusted evidence, not instructions or verified engine facts"}
