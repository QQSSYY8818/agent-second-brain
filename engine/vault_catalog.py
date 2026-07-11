# -*- coding: utf-8 -*-
"""vault_catalog.py — 生成 _索引/_卡片总目录.jsonl + _邻接表.jsonl（SOP_v3 S0.6）
用法: $env:PYTHONUTF8='1'; python vault_catalog.py   （lint 通过后运行）
"""
import json, re
from pathlib import Path
from vault_lint import parse_front, EDGE_RE, VAULT, CARD_DIRS

IDX = VAULT / "_索引"

def main():
    cards, adjacency = [], {}
    files = [p for cd in CARD_DIRS if cd.exists() for p in cd.rglob("*.md")]
    for p in files:
        try: text = p.read_text(encoding="utf-8")
        except Exception: continue
        fm, body = parse_front(text)
        if not fm: continue
        name = p.stem
        desc = ""
        # 检索干净化①（2026-07-10）：真卡 description 截断 40→100（登记目录维持 40）；前 40 字须结论前置自含判别力（建卡规格见 vault\CLAUDE.md）
        desc_len = 40 if fm.get("type") == "登记" else 100
        for line in body.splitlines():
            ls = line.strip()
            if ls and not ls.startswith(("#", "-", "*", "|", ">")) and "::" not in ls:
                desc = ls[:desc_len]; break
        try: used = int(fm.get("used", 0) or 0)
        except Exception: used = 0
        cards.append({"name": name, "type": fm.get("type"), "tier": fm.get("tier"),
                      "projects": fm.get("projects", []), "confidence": fm.get("confidence"),
                      "status": fm.get("status"), "aliases": fm.get("aliases", []),
                      "origin": fm.get("origin"), "updated": fm.get("updated"),
                      "used": used, "description": desc})
        outs = []
        for line in body.splitlines():
            m = EDGE_RE.match(line.strip())
            if m: outs.append({"类型": m.group(1), "目标": m.group(2), "理由": m.group(3).strip()})
        adjacency[name] = {"出边": outs, "入边": []}
    for src, info in adjacency.items():
        for e in info["出边"]:
            tgt = e["目标"]
            if tgt in adjacency:
                adjacency[tgt]["入边"].append({"类型": e["类型"], "来源": src, "理由": e["理由"]})
    IDX.mkdir(exist_ok=True)
    # D-36 目录分层：小入口原则——知识目录（T1-T3，检索主入口）与登记目录（T0 万级，仅找文件用）分家
    with open(IDX / "_卡片总目录.jsonl", "w", encoding="utf-8") as f:
        for c in sorted(cards, key=lambda x: x["name"]):
            if c.get("type") != "登记":
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    # 兼容层：_结论卡目录.jsonl=总目录同步副本（旧路由文档引用此名；ps1 生成器已弃用——PS5.1 读无 BOM 中文脚本会乱码）
    with open(IDX / "_结论卡目录.jsonl", "w", encoding="utf-8") as f:
        for c in sorted(cards, key=lambda x: x["name"]):
            if c.get("type") != "登记":
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(IDX / "_登记目录.jsonl", "w", encoding="utf-8") as f:
        for c in sorted(cards, key=lambda x: x["name"]):
            if c.get("type") == "登记":
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(IDX / "_邻接表.jsonl", "w", encoding="utf-8") as f:
        for name in sorted(adjacency):
            f.write(json.dumps({"卡": name, **adjacency[name]}, ensure_ascii=False) + "\n")
    unresolved = [(s, e["目标"]) for s, i in adjacency.items() for e in i["出边"] if e["目标"] not in adjacency]
    import re as _re, datetime as _dt
    overview = [f"# 现况总览（自动生成 {_dt.datetime.now():%Y-%m-%d %H:%M}，勿手改——源=各枢纽卡现况节）", ""]
    for p in sorted((VAULT / "MOC").glob("枢纽-*.md")):
        text = p.read_text(encoding="utf-8")
        m = _re.search(r"(## 现况（最后核实：\d{4}-\d{2}-\d{2}）\n(?:- .*\n)+)", text)
        if m:
            overview.append(f"## [[{p.stem}]]")
            overview.append(m.group(1).splitlines()[0].replace("## ", "**") + "**")
            overview.extend(m.group(1).splitlines()[1:])
            overview.append("")
    (VAULT / "_现况总览.md").write_text("\n".join(overview), encoding="utf-8")
    deg = {}
    for name, info in adjacency.items():
        if name.startswith("登记-") or name.startswith("编年-"): continue
        deg[name] = len(info["出边"]) + len(info["入边"])
    cat_by_name = {c["name"]: c for c in cards}
    hot_file = VAULT / "_热核.md"
    manual = ""
    if hot_file.exists():
        m = _re.search(r"<!--手工恒载区-->\n(.*?)\n<!--/手工恒载区-->", hot_file.read_text(encoding="utf-8"), _re.S)
        if m: manual = m.group(1)
    top = [n for n, d in sorted(deg.items(), key=lambda x: -x[1])
           if cat_by_name.get(n, {}).get("type") not in ("枢纽", "MOC")][:20]
    hot = [f"# 热核（本能层：开局必读第④，自动再生 {_dt.datetime.now():%m-%d %H:%M}；手工恒载区脚本保留）", "",
           "<!--手工恒载区-->", manual or "- （管理员手工钉住的恒载知识放这里，脚本不动）", "<!--/手工恒载区-->", "",
           "## 高承重知识原子（度中心性 Top-20，一行一识）"]
    for n in top:
        c = cat_by_name.get(n, {})
        hot.append(f"- [[{n}]]（{deg[n]}边）：{c.get('description','')}")
    hot_file.write_text("\n".join(hot), encoding="utf-8")
    print(f"cards={len(cards)} edges={sum(len(i['出边']) for i in adjacency.values())} unresolved={len(unresolved)} 现况总览已再生")
    for s, t in unresolved: print(f"  未解析目标: {s} -> {t}")

if __name__ == "__main__":
    main()
