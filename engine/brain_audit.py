# -*- coding: utf-8 -*-
r"""brain_audit.py — 第二大脑关联性全库机械审计（/goal #4）。
检查：①别名歧义 ②对称矛盾边(支持vs冲突) ③上位环 ④上位层级倒挂 ⑤tier-度错配
⑥星形卡(只连枢纽) ⑦弱理由边 ⑧D-49 摘要合规 ⑨q_status 一致性 ⑩分布统计。
产出：<BRAIN_ROOT>\_大脑审计\审计_<日期>.md（只读原库，零写入 vault）。
"""
import json, re, datetime, collections
from pathlib import Path

from config import VAULT, AUDIT_DIR  # 路径唯一源，见 config.py
IDX = VAULT / "_索引"
OUT = AUDIT_DIR
TODAY = datetime.date.today().isoformat()
TIER_ORD = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}

def jsonl(p):
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)

cards = {c["name"]: c for c in jsonl(IDX / "_卡片总目录.jsonl")}
adj = {a["卡"]: a for a in jsonl(IDX / "_邻接表.jsonl")}

R = collections.defaultdict(list)  # 分节报告

# ① 别名歧义
alias_map = collections.defaultdict(list)
for n, c in cards.items():
    for a in c.get("aliases", []):
        key = a.strip('"').strip().lower()
        if key:
            alias_map[key].append(n)
for a, ns in sorted(alias_map.items()):
    if len(ns) > 1:
        R["①别名歧义（同 alias 指多卡=路由错向源）"].append(f"`{a}` → {' / '.join(ns)}")

# 边集（出边为准，含全边类型）
edges = []  # (src, type, dst, reason)
for n, a in adj.items():
    for e in a.get("出边", []):
        edges.append((n, e["类型"], e["目标"], e.get("理由", "")))
pair_types = collections.defaultdict(set)
for s, t, d, r in edges:
    pair_types[frozenset((s, d))].add(t)

# ② 对称矛盾：同一对卡之间既有支持又有冲突
for pair, ts in pair_types.items():
    if "支持" in ts and "冲突" in ts and len(pair) == 2:
        R["②支持/冲突并存对（需人判：真矛盾还是边型误用）"].append(" ↔ ".join(sorted(pair)) + f"（{'/'.join(sorted(ts))}）")

# ③ 上位环
up = collections.defaultdict(list)
for s, t, d, r in edges:
    if t == "上位":
        up[s].append(d)
def find_cycle(start):
    stack, seen = [(start, [start])], set()
    while stack:
        node, path = stack.pop()
        for nxt in up.get(node, []):
            if nxt == start:
                return path + [nxt]
            if nxt not in seen:
                seen.add(nxt)
                stack.append((nxt, path + [nxt]))
    return None
for s in list(up):
    cyc = find_cycle(s)
    if cyc:
        R["③上位环（层级不允许成环）"].append(" → ".join(cyc))

# ④ 上位层级倒挂：家族卡 tier 低于实例卡
for s, t, d, r in edges:
    if t == "上位" and s in cards and d in cards:
        if TIER_ORD.get(cards[d].get("tier"), 0) < TIER_ORD.get(cards[s].get("tier"), 0):
            R["④上位层级倒挂（家族卡 tier < 实例卡）"].append(f"{s}({cards[s]['tier']}) →上位→ {d}({cards[d]['tier']})")

# ⑤ tier-度错配 + ⑥ 星形卡
deg = collections.Counter()
nbrs = collections.defaultdict(set)
for s, t, d, r in edges:
    deg[s] += 1; deg[d] += 1
    nbrs[s].add(d); nbrs[d].add(s)
for n, c in cards.items():
    ty = c.get("type")
    if ty in ("登记", "编年"):
        continue
    dg = deg.get(n, 0)
    tier = c.get("tier", "")
    if tier in ("T2", "T3") and dg <= 1 and ty not in ("枢纽",):
        R["⑤a 高档低连（T2/T3 度≤1，补边或降档提名）"].append(f"{n}（{tier}，度{dg}）")
    if tier in ("T1", "T2") and dg >= 15:
        R["⑤b 低档高连（度≥15，升 T3 提名——反链升档规则）"].append(f"{n}（{tier}，度{dg}）")
    ns = nbrs.get(n, set())
    if ns and all(x.startswith("枢纽-") for x in ns) and ty not in ("枢纽", "MOC"):
        R["⑥星形卡（只连枢纽=没进真网络）"].append(f"{n}（{tier}）")

# ⑦ 弱理由边
for s, t, d, r in edges:
    if t not in ("出处", "引用") and len(r.strip()) < 6:
        R["⑦弱理由边（<6 字，判断缓存无信息量）"].append(f"{s} —{t}→ {d}：「{r}」")

# ⑧ D-49 摘要合规 + ⑨ q_status
for p in list((VAULT / "MOC").glob("*.md")) + list((VAULT / "卡片").glob("问题-*.md")):
    text = p.read_text(encoding="utf-8", errors="replace")
    n = p.stem
    if n.startswith("MOC-内容-") and "结论摘要" not in text:
        R["⑧MOC 缺结论摘要节（D-49 未达标清单=C1 批量任务对象）"].append(n)
    if n.startswith("枢纽-") and "现况" not in text:
        R["⑧枢纽缺现况节"].append(n)
    if n.startswith("问题-"):
        qm = re.search(r"^q_status:\s*(\S+)", text, re.M)
        if qm and qm.group(1) == "answered" and "支持::" not in text:
            R["⑨answered 问题卡缺答案边"].append(n)

# ⑩ 统计
type_cnt = collections.Counter(c.get("type") for c in cards.values())
etype_cnt = collections.Counter(t for _, t, _, _ in edges)
top = deg.most_common(12)

lines = [f"# 第二大脑关联性审计报告 {TODAY}", "",
         f"真卡 {len(cards)}｜出边记录 {len(edges)}｜审计脚本 brain_audit.py（只读，零写入）", "",
         "## 统计", f"- 卡型分布：{dict(type_cnt)}", f"- 边型分布：{dict(etype_cnt)}",
         "- 度 Top12：" + "、".join(f"{n}({d})" for n, d in top), ""]
total_issues = 0
for sec in sorted(R):
    lines.append(f"## {sec}（{len(R[sec])} 条）")
    lines += [f"- {x}" for x in R[sec][:80]]
    if len(R[sec]) > 80:
        lines.append(f"- …余 {len(R[sec])-80} 条略")
    lines.append("")
    total_issues += len(R[sec])
lines.insert(3, f"**问题总数：{total_issues}**")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / f"审计_{TODAY}.md").write_text("\n".join(lines), encoding="utf-8")
print(f"审计完成：{total_issues} 条 → {OUT}\\审计_{TODAY}.md")
