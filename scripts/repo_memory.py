#!/usr/bin/env python3
"""mq-hal repo memory: local repo indexing, search, ask, and map."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.environ.get("MQ_HAL_CONFIG_PATH", str(BASE_DIR / "config" / "repos.json"))).expanduser()
STATE_DIR = Path(os.environ.get("MQ_HAL_STATE_DIR", str(Path.home() / ".mq-hal"))).expanduser()
MEMORY_DIR = STATE_DIR / "repo_memory"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

SKIP_DIRS = {
    ".git", ".venv", "__pycache__", "node_modules", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".next", ".cache",
}
TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".sh", ".json", ".yaml", ".yml", ".toml",
    ".html", ".css", ".js", ".ts", ".tsx", ".jsx",
}
MAX_FILE_BYTES = 128_000
MAX_INDEX_FILES = 300


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {"repos": {}}


def resolve_repo(repo_name: str | None) -> tuple[str, Path]:
    config = load_config()
    repos = config.get("repos", {})
    if not isinstance(repos, dict) or not repos:
        raise ValueError("config/repos.json has no repos")
    selected = repo_name or str(config.get("default_repo") or next(iter(repos)))
    if selected not in repos:
        known = ", ".join(sorted(repos))
        raise ValueError(f"unknown repo: {selected}. Known repos: {known}")
    return selected, Path(str(repos[selected])).expanduser().resolve()


def index_path(repo_name: str) -> Path:
    return MEMORY_DIR / f"{repo_name}.json"


def is_text_file(path: Path) -> bool:
    if path.name in {"README", "LICENSE", "CHANGELOG", "VERSION"}:
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def iter_files(repo_path: Path) -> list[Path]:
    result: list[Path] = []
    for path in sorted(repo_path.rglob("*")):
        rel_parts = path.relative_to(repo_path).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if not path.is_file() or not is_text_file(path):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        result.append(path)
        if len(result) >= MAX_INDEX_FILES:
            break
    return result


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9_./-]{2,}", text)]


def classify(path: str) -> list[str]:
    tags: list[str] = []
    lower = path.lower()
    if "roadmap" in lower:
        tags.append("roadmap")
    if "readme" in lower:
        tags.append("overview")
    if "changelog" in lower:
        tags.append("release-history")
    if "architecture" in lower or "integration" in lower or "contract" in lower:
        tags.append("architecture")
    if lower.endswith((".py", ".sh")):
        tags.append("implementation")
    if lower.startswith("tests/"):
        tags.append("tests")
    return tags


def first_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def build_entry(repo_path: Path, path: Path) -> dict[str, Any]:
    rel = str(path.relative_to(repo_path))
    text = read_text(path)
    tokens = tokenize(text)
    counts = Counter(tokens)
    top_terms = [term for term, _count in counts.most_common(20)]
    preview = " ".join(text.strip().split())[:400]
    return {
        "path": rel,
        "title": first_heading(text),
        "tags": classify(rel),
        "size": len(text.encode("utf-8")),
        "tokens": len(tokens),
        "top_terms": top_terms,
        "preview": preview,
        "content": text[:20_000],
    }


def ollama_embedding(text: str, model: str) -> list[float] | None:
    payload = {"model": model, "prompt": text[:4000]}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_URL.rstrip('/')}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None
    embedding = body.get("embedding")
    return embedding if isinstance(embedding, list) else None


def write_index(repo_name: str, repo_path: Path, embeddings: bool, model: str) -> dict[str, Any]:
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"repo path does not exist: {repo_path}")
    entries = [build_entry(repo_path, path) for path in iter_files(repo_path)]
    embedding_count = 0
    if embeddings:
        for entry in entries:
            vector = ollama_embedding(entry["preview"] or entry["content"], model)
            if vector is not None:
                entry["embedding"] = vector
                embedding_count += 1
    data = {
        "schema": "mq-hal.repo-memory.v1",
        "repo": repo_name,
        "repo_path": str(repo_path),
        "generated_at": now_iso(),
        "mode": "lexical+embeddings" if embedding_count else "lexical",
        "embedding_model": model if embeddings else None,
        "embedding_count": embedding_count,
        "files": entries,
    }
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    index_path(repo_name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def load_index(repo_name: str) -> dict[str, Any]:
    path = index_path(repo_name)
    if not path.exists():
        raise ValueError(f"repo memory index missing for {repo_name}; run mq-hal index {repo_name}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid repo memory index: {exc}") from exc
    return data if isinstance(data, dict) else {}


def search_index(data: dict[str, Any], query: str, limit: int) -> list[dict[str, Any]]:
    terms = tokenize(query)
    results: list[dict[str, Any]] = []
    for entry in data.get("files", []):
        if not isinstance(entry, dict):
            continue
        haystack = " ".join([
            str(entry.get("path", "")),
            str(entry.get("title", "")),
            " ".join(entry.get("tags", [])),
            str(entry.get("preview", "")),
            " ".join(entry.get("top_terms", [])),
            str(entry.get("content", ""))[:2000],
        ]).lower()
        score = sum(haystack.count(term) for term in terms)
        if score <= 0:
            continue
        results.append({
            "path": entry.get("path", ""),
            "title": entry.get("title", ""),
            "tags": entry.get("tags", []),
            "score": score,
            "preview": entry.get("preview", ""),
        })
    return sorted(results, key=lambda item: (-int(item["score"]), str(item["path"])))[:limit]


def repo_map(data: dict[str, Any]) -> dict[str, Any]:
    dirs: dict[str, int] = {}
    tags: Counter[str] = Counter()
    for entry in data.get("files", []):
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path", ""))
        parent = str(Path(path).parent)
        dirs[parent if parent != "." else "/"] = dirs.get(parent if parent != "." else "/", 0) + 1
        tags.update(str(tag) for tag in entry.get("tags", []))
    return {
        "repo": data.get("repo", ""),
        "generated_at": data.get("generated_at", ""),
        "file_count": len(data.get("files", [])),
        "directories": dict(sorted(dirs.items())),
        "knowledge_tags": dict(sorted(tags.items())),
    }


def render_index(data: dict[str, Any]) -> None:
    print("HAL Repo Memory Index")
    print("=====================")
    print()
    print(f"Repo:   {data['repo']}")
    print(f"Files:  {len(data.get('files', []))}")
    print(f"Mode:   {data.get('mode', 'lexical')}")
    print(f"Path:   {index_path(str(data['repo']))}")


def render_search(results: list[dict[str, Any]], query: str) -> None:
    print("HAL Repo Memory Search")
    print("======================")
    print()
    print(f"Query: {query}")
    print()
    if not results:
        print("No matches.")
        return
    for item in results:
        tags = ",".join(item.get("tags", [])) or "-"
        print(f"[{item['score']}] {item['path']}  tags={tags}")
        if item.get("title"):
            print(f"    {item['title']}")
        print(f"    {item.get('preview', '')[:180]}")


def render_ask(results: list[dict[str, Any]], question: str) -> None:
    print("HAL Repo Answer")
    print("===============")
    print()
    print(f"Question: {question}")
    print()
    if not results:
        print("No indexed context matched. Run a broader search or re-index the repo.")
        return
    print("Most relevant context:")
    for item in results[:3]:
        print(f"- {item['path']} (score {item['score']}): {item.get('preview', '')[:180]}")
    print()
    print("Answer:")
    print("Use the matched files above as the grounded starting point. This deterministic")
    print("answer does not invent beyond indexed repo memory.")


def render_map(summary: dict[str, Any]) -> None:
    print("HAL Repo Map")
    print("============")
    print()
    print(f"Repo:  {summary['repo']}")
    print(f"Files: {summary['file_count']}")
    print()
    print("Directories")
    print("-----------")
    for name, count in summary["directories"].items():
        print(f"  {name:<30} {count}")
    if summary["knowledge_tags"]:
        print()
        print("Knowledge tags")
        print("--------------")
        for name, count in summary["knowledge_tags"].items():
            print(f"  {name:<20} {count}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="mq-hal repo-memory")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index a configured repo")
    p_index.add_argument("repo", nargs="?")
    p_index.add_argument("--json", action="store_true")
    p_index.add_argument("--embeddings", action="store_true")
    p_index.add_argument("--embedding-model", default=os.environ.get("MQ_HAL_EMBEDDING_MODEL", "nomic-embed-text"))

    p_search = sub.add_parser("search", help="Search indexed repo memory")
    p_search.add_argument("query", nargs="+")
    p_search.add_argument("--repo")
    p_search.add_argument("--limit", type=int, default=5)
    p_search.add_argument("--json", action="store_true")

    p_ask = sub.add_parser("ask-repo", help="Answer from indexed repo memory")
    p_ask.add_argument("question", nargs="+")
    p_ask.add_argument("--repo")
    p_ask.add_argument("--limit", type=int, default=5)
    p_ask.add_argument("--json", action="store_true")

    p_map = sub.add_parser("repo-map", help="Summarize indexed repo memory")
    p_map.add_argument("--repo")
    p_map.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "index":
            repo_name, repo_path = resolve_repo(args.repo)
            data = write_index(repo_name, repo_path, args.embeddings, args.embedding_model)
            print(json.dumps(data, indent=2, ensure_ascii=False) if args.json else "", end="")
            if not args.json:
                render_index(data)
            return 0
        if args.command == "search":
            repo_name, _repo_path = resolve_repo(args.repo)
            results = search_index(load_index(repo_name), " ".join(args.query), args.limit)
            if args.json:
                print(json.dumps({"repo": repo_name, "results": results}, indent=2, ensure_ascii=False))
            else:
                render_search(results, " ".join(args.query))
            return 0
        if args.command == "ask-repo":
            repo_name, _repo_path = resolve_repo(args.repo)
            question = " ".join(args.question)
            results = search_index(load_index(repo_name), question, args.limit)
            if args.json:
                print(json.dumps({"repo": repo_name, "question": question, "context": results}, indent=2, ensure_ascii=False))
            else:
                render_ask(results, question)
            return 0
        if args.command == "repo-map":
            repo_name, _repo_path = resolve_repo(args.repo)
            summary = repo_map(load_index(repo_name))
            if args.json:
                print(json.dumps(summary, indent=2, ensure_ascii=False))
            else:
                render_map(summary)
            return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
