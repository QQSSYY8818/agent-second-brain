# -*- coding: utf-8 -*-
"""transcript_harvest.py — 写侧本能·零token捕获层（Stop 钩子，D-35；2026-07-10 加自动 touch）
每轮对话结束：增量扫 transcript → ①结论句候选（正则模式）②编年行候选（工具证据）
③本轮 Read 过的 vault 卡片 → 批量 vault_touch（used 闭环全自动，检索干净化③）→ vault/_inbox/收割_日期.md
④本轮 Write/Edit 命中过程目录的文件 → registry_sweep.register_file 自动产 T0 登记卡（三保险①，2026-07-10）
⑤_最新状态.md 本轮新增 ★ 行 → 编年行草稿进 inbox（三保险特例条款）
纯本地正则零 LLM token；断点=字节偏移表；恒 exit 0。备份：_备份/transcript_harvest_20260710b.py。
"""
import os, sys, json, re, datetime
from pathlib import Path

# 双机双账户通用：扫全部项目取最新 transcript；HARVEST_PROJ_BASE 仅供测试注入假 transcript
PROJ_BASE = Path(os.environ.get("HARVEST_PROJ_BASE") or (Path.home() / ".claude" / "projects"))
from config import VAULT  # 权威 vault 唯一源(项目大脑)，见 config.py
STATE = VAULT / "_索引" / "已收割偏移.json"
CONC_RE = re.compile(r"[^。\n]*(结论|定案|教训|坑[：:]|发现了|实测|——式子在说|判定[=＝]|归因|铁律|红线)[^。\n]{6,}。?")
PROJ_RE = re.compile(r"(\d{2})_[^\\/]+[\\/]")
ACT = [("vault_lint|vault_catalog|巡检", "巡检"), ("卡片|MOC", "建卡"), ("docx|排版", "排版"),
       ("拟合|fit|model", "建模"), ("SOP|决策日志", "建规"), ("server|index.html|app", "开发"),
       ("思考_", "交接归档")]

def main():
    try:
        try: json.load(sys.stdin)
        except Exception: pass
        offsets = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
        conclusions, events, read_cards, written = [], [], set(), set()
        files = sorted(PROJ_BASE.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:2]
        for f in files:
            key, size = f.name, f.stat().st_size
            off = offsets.get(key, 0)
            if size <= off: continue
            with open(f, "rb") as fh:
                fh.seek(off); chunk = fh.read().decode("utf-8", "replace")
            offsets[key] = size
            for line in chunk.split("\n"):
                try: e = json.loads(line)
                except Exception: continue
                ts = (e.get("timestamp") or "")[:16].replace("T", " ")
                content = (e.get("message") or {}).get("content")
                if e.get("type") == "assistant" and isinstance(content, list):
                    for b in content:
                        if b.get("type") == "text" and b.get("text"):
                            for m in CONC_RE.finditer(b["text"]):
                                s = m.group(0).strip()
                                if 20 < len(s) < 300: conclusions.append(f"- {ts}｜{s}")
                        elif b.get("type") == "tool_use" and b.get("name") == "Read":
                            # 检索干净化③：收集本轮 Read 过的 vault 卡片路径 → 收尾批量 touch
                            fp = str((b.get("input") or {}).get("file_path", "")).replace("/", "\\")
                            if fp.endswith(".md") and "_模板" not in fp and (
                                    "\\vault\\卡片\\" in fp or "\\vault\\MOC\\" in fp):
                                read_cards.add(Path(fp).stem)
                        elif b.get("type") == "tool_use" and b.get("name") in ("Write", "Edit"):
                            fp = str((b.get("input") or {}).get("file_path", ""))
                            if not fp or "\\vault\\" in fp or "/vault/" in fp: continue
                            written.add(fp)  # 三保险①：收尾统一喂 register_file（幂等）
                            if Path(fp).name == "_最新状态.md":
                                # 特例条款：滚动文件不卡片化，但本轮新增 ★ 行同步为编年行草稿
                                inp = b.get("input") or {}
                                txt = str(inp.get("content") or inp.get("new_string") or "")
                                for ln in txt.splitlines():
                                    if ln.strip().startswith("★"):
                                        events.append(f"- {ts[5:10]} ｜00｜[编年草稿★] {ln.strip()[:150]}")
                            pm = PROJ_RE.search(fp)
                            proj = pm.group(1) if pm else "00"
                            act = next((a for pat, a in ACT if re.search(pat, fp, re.I)), "开发")
                            events.append(f"- {ts[:10] and ts[5:10]} ｜{proj}｜[{act}] {b['name']} {Path(fp).name} → {fp.split(chr(92))[-3] if chr(92) in fp else fp}")
        if read_cards:  # 自动 touch（used+1/last_hit），任何异常吞掉不碍收割主流程
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                from vault_touch import find_card, touch
                for name in sorted(read_cards):
                    p = find_card(name)
                    if p:
                        touch(p)
            except Exception:
                pass
        if written:  # 三保险①：过程文件自动 T0 登记（与 touch 分开 try，互不拖累；幂等由 register_file 保证）
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                from registry_sweep import register_file
                for fp in sorted(written):
                    try:
                        register_file(fp)
                    except Exception:
                        pass
            except Exception:
                pass
        if conclusions or events:
            out = VAULT / "_inbox" / f"收割_{datetime.date.today():%m%d}.md"
            old = out.read_text(encoding="utf-8") if out.exists() else "# 自动收割（零token，待分拣：结论→卡候选；事件→编年行候选）\n"
            seen = set(old.splitlines())
            add = [l for l in ["## 候选结论 " + datetime.datetime.now().strftime("%H:%M")] + conclusions[:20]
                   + ["## 候选编年行"] + list(dict.fromkeys(events))[:30] if l not in seen]
            if len(add) > 2: out.write_text(old + "\n".join(add) + "\n", encoding="utf-8")
        STATE.write_text(json.dumps(offsets), encoding="utf-8")
    except Exception:
        pass
    finally:
        sys.exit(0)

if __name__ == "__main__":
    main()
