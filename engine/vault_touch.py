# -*- coding: utf-8 -*-
"""vault_touch.py — D-50 使用计数最小版（2026-07-10 加 --hops）。
用法: python vault_touch.py [--hops N] 卡名1 卡名2 ...   （卡名不带 .md，可带路径不带亦可）
效果: 对每张卡 frontmatter 的 used +1、last_hit=今天；带 --hops N 则另记 last_hops: N（本次命中跳数，
供巡检 KPI 统计检索效率）；无该字段则插入。不动 updated（使用≠内容修改）。
备份：_备份/vault_touch_20260710.py（升级前旧版）。
"""
import sys, re, datetime
from pathlib import Path

from config import VAULT  # 权威 vault 唯一源(项目大脑)，见 config.py
TODAY = datetime.date.today().isoformat()

def find_card(name: str):
    name = name.removesuffix(".md")
    hits = [p for p in VAULT.rglob(f"{name}.md") if "_模板" not in str(p)]
    return hits[0] if hits else None

def touch(path: Path, hops=None):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return f"SKIP(no frontmatter): {path.name}"
    fm = m.group(1)
    um = re.search(r"^used:\s*(\d+)\s*$", fm, re.M)
    if um:
        fm = re.sub(r"^used:\s*\d+\s*$", f"used: {int(um.group(1))+1}", fm, count=1, flags=re.M)
    else:
        fm += "\nused: 1"
    if re.search(r"^last_hit:", fm, re.M):
        fm = re.sub(r"^last_hit:.*$", f"last_hit: {TODAY}", fm, count=1, flags=re.M)
    else:
        fm += f"\nlast_hit: {TODAY}"
    if hops is not None:
        if re.search(r"^last_hops:", fm, re.M):
            fm = re.sub(r"^last_hops:.*$", f"last_hops: {int(hops)}", fm, count=1, flags=re.M)
        else:
            fm += f"\nlast_hops: {int(hops)}"
    path.write_text(f"---\n{fm}\n---\n" + text[m.end():], encoding="utf-8")
    return f"OK: {path.name}"

if __name__ == "__main__":
    args = sys.argv[1:]
    hops = None
    if "--hops" in args:
        i = args.index("--hops")
        try:
            hops = int(args[i + 1])
            del args[i:i + 2]
        except (IndexError, ValueError):
            print("--hops 需跟整数"); sys.exit(0)
    if not args:
        print(__doc__); sys.exit(0)
    for arg in args:
        p = find_card(Path(arg).name)
        print(touch(p, hops) if p else f"MISS: {arg}")
