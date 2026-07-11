# -*- coding: utf-8 -*-
"""vault_patrol.py — 月度巡检（SOP_v3 S4.3，Windows 计划任务每月 1 日跑，零 token）
内容：lint 全检(--fix) → 总目录/邻接表再生 → 评测集机械回归(目标卡存在) → 陈旧度报告 →
inbox/待办/miss 汇总 → 报告落 <BRAIN_ROOT>/_运行日志/巡检_YYYYMM.md（判断件由 Claude 在月度首会话按报告处理）
"""
import json, datetime, subprocess, sys, re
from pathlib import Path

SCRIPT = Path(__file__).resolve()
from config import VAULT, LOG_DIR  # 路径唯一源，见 config.py
IDX = VAULT / "_索引"
LOG = LOG_DIR
PY = sys.executable

def run(args):
    r = subprocess.run([PY, str(SCRIPT.parent / args[0])] + args[1:],
                       capture_output=True, text=True, encoding="utf-8")
    return (r.stdout or "") + (r.stderr or "")

def main():
    now = datetime.datetime.now()
    lines = [f"# 巡检报告 {now:%Y-%m}（生成 {now:%Y-%m-%d %H:%M}）", ""]
    # 三保险 KPI：先测覆盖率（=钩子净效果），再跑增量扫描兜底补漏（registry_sweep 为可选组件，不在则跳过）
    if (SCRIPT.parent / "registry_sweep.py").exists():
        lines += ["## 过程文件登记覆盖率（三保险KPI，兜底扫描前=钩子净效果，目标100%）", "```",
                  run(["registry_sweep.py", "--kpi"]).strip()[:1500], "```"]
        lines += ["## 过程文件增量登记（registry_sweep 兜底）", "```",
                  run(["registry_sweep.py", "--incremental"]).strip()[:1200], "```"]
    lines += ["## lint", "```", run(["vault_lint.py", "--fix"]).strip()[:3000], "```"]
    lines += ["## 索引再生", "```", run(["vault_catalog.py"]).strip()[:1000], "```"]
    emb = run(["vault_embed.py"]).strip()
    if "向量库" in emb:
        lines += ["## 向量库增量再生", "```", emb[-300:], "```"]
    else:
        lines += ["## 向量库增量再生", "- ⚠ 跳过（Ollama 服务未运行？需本地 Ollama + bge-m3 模型，起服务后手动跑 vault_embed.py）"]
    cat = {}
    f = IDX / "_卡片总目录.jsonl"
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            c = json.loads(l); cat[c["name"]] = c
    eva = VAULT / "_评测集.md"; missing = []
    if eva.exists():
        for m in re.finditer(r"\|\s*\d+\s*\|[^|]*\|\s*([^|]+?)\s*\|", eva.read_text(encoding="utf-8")):
            tgt = m.group(1).strip()
            if tgt and tgt not in ("期望卡",) and not tgt.startswith("-") and tgt not in cat:
                missing.append(tgt)
    lines += ["## 评测集机械回归", f"- 目标卡缺失: {missing if missing else '无 ✅'}"]
    stale = [c["name"] for c in cat.values()
             if c.get("status") == "已审" and c.get("tier") in ("T2","T3") and c.get("updated")
             and (now.date() - datetime.date.fromisoformat(c["updated"])).days > 180]
    lines += ["## 陈旧度（已审 T2/T3 且 180 天未更新）", f"- {len(stale)} 张：" + ", ".join(stale[:30])]
    adj_f = IDX / "_邻接表.jsonl"
    if adj_f.exists():
        deg = {}
        for l in adj_f.read_text(encoding="utf-8").splitlines():
            a = json.loads(l)
            if a["卡"].startswith("登记-"): continue
            deg[a["卡"]] = len(a.get("出边", [])) + len(a.get("入边", []))
        top = sorted(deg.items(), key=lambda x: -x[1])[:10]
        zin = []
        for l in adj_f.read_text(encoding="utf-8").splitlines():
            a0 = json.loads(l)
            n = a0["卡"]
            if n.startswith("登记-") or n.startswith("枢纽-") or n.startswith("MOC-") or n.startswith("编年-"): continue
            if not a0.get("入边"): zin.append(n)
        lines += ["## 零入边知识卡（D-37 入边责任，需补织）", f"- {len(zin)} 张：" + ", ".join(zin[:20]) if zin else "- 无 ✅"]
        lines += ["## 度中心性 Top-10（网络枢纽，外部 PKM 审计实践引入 D-27）",
                  *[f"- {n}：{d} 边" for n, d in top]]
        hot_stale = [n for n, d in deg.items() if d >= 8 and n in cat
                     and cat[n].get("updated") and (now.date() - datetime.date.fromisoformat(cat[n]["updated"])).days > 90]
        lines += ["## 高被链但 90 天未更新（疑似断桥/须复核）", f"- {hot_stale[:15] if hot_stale else '无 ✅'}"]
    import re as _re
    hub_stale = []
    chron_latest = {}
    for p in (VAULT / "卡片").glob("编年-*.md"):
        for m in _re.finditer(r"^- (\d{2})-(\d{2}) ｜([\d,\s]+)｜", p.read_text(encoding="utf-8"), _re.M):
            dt = f"2026-{m.group(1)}-{m.group(2)}"
            for proj in m.group(3).replace(" ", "").split(","):
                if dt > chron_latest.get(proj, ""): chron_latest[proj] = dt
    for p in (VAULT / "MOC").glob("枢纽-*.md"):
        text = p.read_text(encoding="utf-8")
        hm = _re.search(r"## 现况（最后核实：(\d{4}-\d{2}-\d{2})）", text)
        pm = _re.match(r"枢纽-(\d+)", p.stem)
        if not pm: continue
        proj = pm.group(1)
        if proj not in chron_latest: continue
        if not hm:
            hub_stale.append(f"{p.stem}（无现况节）")
        elif (datetime.date.fromisoformat(chron_latest[proj]) - datetime.date.fromisoformat(hm.group(1))).days > 3:
            hub_stale.append(f"{p.stem}（核实 {hm.group(1)} < 编年 {chron_latest[proj]}）")
    lines += ["## 枢纽现况时效（D-30：编年更新而现况落后>3天）", f"- {hub_stale if hub_stale else '全部新鲜 ✅'}"]
    inbox = list((VAULT / "_inbox").glob("*.md"))
    lines += ["## inbox 待分拣", f"- {len(inbox)} 条：" + ", ".join(p.name for p in inbox[:20])]
    miss_f = VAULT / "_检索失败日志.md"
    miss_n = len([l for l in miss_f.read_text(encoding='utf-8').splitlines() if l.startswith("| 2")]) if miss_f.exists() else 0
    lines += ["## 检索失败日志", f"- 未消化 miss 记录 {miss_n} 条（详见 _检索失败日志.md）"]
    todo_f = VAULT / "_待办.md"
    todo_n = todo_f.read_text(encoding="utf-8").count("- [ ]") if todo_f.exists() else 0
    lines += ["## 待办存量", f"- 未勾 {todo_n} 项（详见 _待办.md）", "",
              "## 需 Claude 判断处置（月度首会话）",
              "- inbox 分拣（不合门槛降索引行，永不删除）/ 晋升评定 / 取代标记 / miss 转补卡 / 陈旧高频卡复核 / 降档取代清单呈用户"]
    LOG.mkdir(parents=True, exist_ok=True)
    out = LOG / f"巡检_{now:%Y%m}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"patrol done -> {out.name}")

if __name__ == "__main__":
    main()
