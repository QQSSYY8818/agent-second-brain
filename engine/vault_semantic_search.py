# -*- coding: utf-8 -*-
"""vault_semantic_search.py — WS1-S3 语义检索（SOP_v4）
用法: $env:PYTHONUTF8='1'; python vault_semantic_search.py "查询文本" [top_k]
检索协议 0.5 段：目录 grep 与全文 grep 都 miss 时用本工具。
"""
import sys, json, math, urllib.request
from pathlib import Path
from vault_lint import VAULT

IDX = VAULT / "_索引"
MODEL = "bge-m3"
API = "http://localhost:11434/api/embed"

def embed(text):
    req = urllib.request.Request(API, json.dumps({"model": MODEL, "input": text}).encode("utf-8"),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["embeddings"][0]

def cos(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)) + 1e-12)

def main():
    q = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    qv = embed(q)
    rows = [json.loads(l) for l in (IDX / "_向量库.jsonl").read_text(encoding="utf-8").splitlines()]
    scored = sorted(((cos(qv, r["vector"]), r["name"]) for r in rows), reverse=True)[:k]
    for s, n in scored: print(f"{s:.3f}  {n}")

if __name__ == "__main__":
    main()
