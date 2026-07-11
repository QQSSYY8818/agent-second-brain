# -*- coding: utf-8 -*-
r"""vault_rings.py — D-63 三环注意力视图（用户定：显性=入口，隐性分在网层/知识库层）。
环 0 显性：`活性: 显性` 标注卡（唯一手工动作）。
环 1 在网层：从环 0 沿邻接表（无向）≤2 跳可达的隐性卡=当前工作的支撑知识。
环 2 知识库：其余全部真卡（已结束话题/旧对话/未挂当前工作的知识）——入口=主题 MOC+编年层+总目录，不经显性辐射。
环是**计算视图**非静态标注：撤一个显性标，其支撑网自动沉入知识库。产出 `_索引\_活性环视图.md`。
跑法：catalog 之后顺跑（依赖邻接表新鲜）。
"""
import json, re, collections, datetime
from pathlib import Path

from config import VAULT  # 权威 vault 唯一源(项目大脑)，见 config.py
IDX = VAULT / "_索引"
TODAY = datetime.date.today().isoformat()

def jsonl(p):
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)

all_cards = {c["name"]: c for c in jsonl(IDX / "_卡片总目录.jsonl")}
# D-66 R1（用户定）：知识点卡=环外独立知识平面，不参与环计算；环内只留线性传输的工作卡
wiki = {n for n, c in all_cards.items() if c.get("type") == "知识点"}
cards = {n: c for n, c in all_cards.items() if n not in wiki}
# 无向邻接（只在真卡间；登记 T0 不参与环计算防淹没）
nbr = collections.defaultdict(set)
for a in jsonl(IDX / "_邻接表.jsonl"):
    n = a["卡"]
    for e in a.get("出边", []):
        t = e["目标"]
        if n in cards and t in cards:
            nbr[n].add(t); nbr[t].add(n)

# 环0：主线显性（活性: 显性）；辅助显性（活性: 辅助 YYYY-MM-DD）单列且 7 天自动过期（D-64 机械规则）
ring0, aux_fresh, aux_expired = set(), [], 0
cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
for p in VAULT.rglob("*.md"):
    if p.parent.name.startswith("_") or p.stem not in cards:
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^活性: (显性|辅助 (\d{4}-\d{2}-\d{2}))\s*$", text[:600], re.M)
    if not m:
        continue
    if m.group(1) == "显性":
        ring0.add(p.stem)
    elif m.group(2) >= cutoff:
        aux_fresh.append(f"{p.stem}（{m.group(2)}）")
    else:  # 过期辅助标→自动转隐性（只删这一行，关联不变）
        p.write_text(text.replace(m.group(0) + "\n", "", 1), encoding="utf-8")
        aux_expired += 1

# 环1：仅直接相连（1 跳）——用户定义：知识库层与显性"没有直接的关联"
ring1 = set()
for n in ring0:
    ring1 |= nbr.get(n, set())
ring1 -= ring0
ring2 = set(cards) - ring0 - ring1

by_type = lambda s: collections.Counter(cards[n]["type"] for n in s)
theme_mocs = [n for n in cards if n.startswith("MOC-") and not n.startswith("MOC-内容-")]

out = [f"# 活性环视图（D-63/64，自动生成 {TODAY}；环=计算视图，勿手改——重生成 vault_rings.py）", "",
       f"**环0 主线显性（入口，{len(ring0)} 张）**：项目工作从这里进（项目进程+开放问题+最新内容，不含辅助）。",
       f"**辅助显性（{len(aux_fresh)} 张，7 天保鲜；本次自动过期转隐 {aux_expired} 张）**：" + ("、".join(aux_fresh) if aux_fresh else "（无）"),
       f"**环1 在网层（{len(ring1)} 张）**：与显性卡直接相连的支撑知识，经显性辐射一跳可达。类型分布：{dict(by_type(ring1))}",
       f"**环2 沉淀层（{len(ring2)} 张）**：已结束/未挂当前工作的线性内容。类型分布：{dict(by_type(ring2))}",
       f"**环外·知识平面（{len(wiki)} 张，D-66 R1）**：知识点卡=维基式定义库，不参与环——出处可在环内，成卡即住环外，经关键词边被环内卡引用：" + (" ".join(f"[[{n}]]" for n in sorted(wiki)) if wiki else "（空，待抽提）"),
       "", "## 环2 沉淀层的框架入口（不经显性辐射）",
       "- 主题 MOC（按领域）：" + " ".join(f"[[{n}]]" for n in sorted(theme_mocs)),
       "- 编年层（按时间）：grep 卡片\\编年-*.md",
       "- 全量检索：grep _卡片总目录.jsonl / 语义兜底 vault_semantic_search.py",
       "", "## 环2 知识库清单（按类型）"]
grouped = collections.defaultdict(list)
for n in sorted(ring2):
    grouped[cards[n]["type"]].append(n)
for t in sorted(grouped):
    out.append(f"- **{t}**（{len(grouped[t])}）：" + " ".join(f"[[{n}]]" for n in grouped[t][:40]) +
               ("" if len(grouped[t]) <= 40 else f" …余{len(grouped[t])-40}"))
(IDX / "_活性环视图.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"环0={len(ring0)} 环1={len(ring1)} 环2={len(ring2)} → _索引\\_活性环视图.md")
