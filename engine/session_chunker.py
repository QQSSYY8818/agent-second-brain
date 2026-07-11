# -*- coding: utf-8 -*-
"""session_chunker.py — P2 历史回填切块（SOP_v3 S2.1）
两份 _session_state\日志\ 全部快照 → 按 ISO 周聚组、倒序 → chunk 文件（每块 ≤50KB，含源文件名头）。
用法: $env:PYTHONUTF8='1'; python session_chunker.py
输出: <BRAIN_ROOT>/_运行日志/P2_chunks/chunk_<ISO周>_<序号>.md + _清单.txt（源目录在 config.SESSION_LOG_DIRS 配置）
"""
import re, datetime
from pathlib import Path

from config import BRAIN_ROOT, SESSION_LOG_DIRS  # 路径唯一源，见 config.py
SRC_DIRS = [Path(p) for p in SESSION_LOG_DIRS]  # 在 config.py 里列出你的状态日志目录
OUT = BRAIN_ROOT / "_运行日志" / "P2_chunks"
MAX_BYTES = 50 * 1024

def file_date(p):
    m = re.search(r"(\d{8})", p.name)
    if m:
        try: return datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
        except ValueError: pass
    return datetime.date.fromtimestamp(p.stat().st_mtime)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items = []
    for d in SRC_DIRS:
        if not d.exists(): continue
        for p in d.glob("*.md"):
            dt = file_date(p)
            iso = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
            items.append((iso, dt, p))
    items.sort(key=lambda x: (x[0], x[1]), reverse=True)  # 倒序：新周优先
    weeks = {}
    for iso, dt, p in items: weeks.setdefault(iso, []).append((dt, p))
    manifest = []
    for iso in sorted(weeks, reverse=True):
        buf, size, part = [], 0, 1
        for dt, p in sorted(weeks[iso], reverse=True):
            try: text = p.read_text(encoding="utf-8", errors="replace")
            except Exception: continue
            block = f"\n\n===== 源文件: {p.name} ({dt}) 来源: {p.parent.name} =====\n\n{text}"
            if size + len(block.encode('utf-8')) > MAX_BYTES and buf:
                fn = OUT / f"chunk_{iso}_{part:02d}.md"
                fn.write_text("".join(buf), encoding="utf-8")
                manifest.append(fn.name); buf, size = [], 0; part += 1
            buf.append(block); size += len(block.encode('utf-8'))
        if buf:
            fn = OUT / f"chunk_{iso}_{part:02d}.md"
            fn.write_text("".join(buf), encoding="utf-8")
            manifest.append(fn.name)
    (OUT / "_清单.txt").write_text("\n".join(manifest), encoding="utf-8")
    print(f"weeks={len(weeks)} chunks={len(manifest)} -> {OUT}")

if __name__ == "__main__":
    main()
