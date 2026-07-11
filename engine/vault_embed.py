# -*- coding: utf-8 -*-
"""vault_embed.py — WS1-S2 知识卡向量库生成（SOP_v4）
读 卡片\+MOC\ 全部知识卡（不含登记层），name+aliases+正文前500字 → Ollama /api/embed → _索引/_向量库.jsonl
增量：已有向量且卡 updated 未变则跳过。用法: $env:PYTHONUTF8='1'; python vault_embed.py
"""
import json, urllib.request
from pathlib import Path
from vault_lint import parse_front, VAULT

IDX = VAULT / "_索引"
OUT = IDX / "_向量库.jsonl"
MODEL = "bge-m3"
API = "http://localhost:11434/api/embed"

def embed(text):
    req = urllib.request.Request(API, json.dumps({"model": MODEL, "input": text}).encode("utf-8"),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["embeddings"][0]

def main():
    old = {}
    if OUT.exists():
        for l in OUT.read_text(encoding="utf-8").splitlines():
            r = json.loads(l); old[r["name"]] = r
    rows, new_count = [], 0
    for d in (VAULT / "卡片", VAULT / "MOC"):
        for p in sorted(d.glob("*.md")):
            fm, body = parse_front(p.read_text(encoding="utf-8"))
            if not fm: continue
            name, upd = p.stem, str(fm.get("updated", ""))
            if name in old and old[name].get("updated") == upd:
                rows.append(old[name]); continue
            text = name + " " + " ".join(fm.get("aliases", [])) + "\n" + body[:500]
            try:
                vec = embed(text)
            except Exception as e:
                print(f"  embed失败 {name}: {e}"); continue
            rows.append({"name": name, "updated": upd, "vector": vec}); new_count += 1
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"向量库 {len(rows)} 卡（新算 {new_count}）-> {OUT.name}")

if __name__ == "__main__":
    main()
