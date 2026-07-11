# -*- coding: utf-8 -*-
r"""vault_routemap.py — D-57 关键词入脑第 0 跳：一屏路由地图生成器。
产出 vault\_索引\_路由地图.md：每项目 2 行（一句话定位｜高频关键词｜承重卡 top-5 按 度+used 排序）。
数据源：_卡片总目录.jsonl（真卡）+_邻接表.jsonl（度）+枢纽卡（一句话定位）+卡 frontmatter used。
跑法：$env:PYTHONUTF8='1'; python vault_routemap.py   （建议 lint/catalog 后顺跑）
"""
import json, re, datetime
from pathlib import Path

from config import VAULT  # 权威 vault 唯一源(项目大脑)，见 config.py
IDX = VAULT / "_索引"

def jsonl(p):
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)

# 1) 真卡目录
cards = {c["name"]: c for c in jsonl(IDX / "_卡片总目录.jsonl")}
# 2) 度（出边+入边）
deg = {}
for a in jsonl(IDX / "_邻接表.jsonl"):
    deg[a["卡"]] = len(a.get("出边", [])) + len(a.get("入边", []))
# 3) used + 枢纽定位行（只扫真卡文件，~200 个）
used, hub_line = {}, {}
for p in list(VAULT.rglob("*.md")):
    if p.parent.name in ("_模板", "_inbox") or p.parent.name.startswith("_"):
        continue
    name = p.stem
    if name not in cards:
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^used:\s*(\d+)", text, re.M)
    if m:
        used[name] = int(m.group(1))
    if name.startswith("枢纽-"):
        h = re.search(r"\*\*一句话定位\*\*：(.+)", text)
        if h:
            hub_line[name] = h.group(1).strip()

def score(n):
    return deg.get(n, 0) + 3 * used.get(n, 0)  # 使用权重×3：功能承重>结构承重

# 4) 按项目聚合（登记/编年不参与承重排序；枢纽/MOC 不占承重卡位）
proj_cards = {}
for n, c in cards.items():
    if c.get("type") in ("登记", "编年", "枢纽", "MOC"):
        continue
    for pj in c.get("projects", []):
        proj_cards.setdefault(str(pj), []).append(n)

hubs = sorted(hub_line)  # 枢纽-00 … 枢纽-97
today = datetime.date.today().isoformat()
out = [
    f"# 路由地图（D-57 关键词入脑第 0 跳；自动生成 {today}，勿手改——重生成 `python engine/vault_routemap.py`）",
    "",
    "> 用法：关键词先 grep/读本页（一屏）→定关联最强项目→第 1 跳读该项目 枢纽现况+MOC-内容 结论摘要（各 ≤10 行）→第 2 跳起顺（强）边/高 used 逐跳读卡（每跳 ≤2 张，可至 4-5 跳）。**全程累计 ≤8 次 Read 铁顶**；预算见 CLAUDE.md 检索协议 -3 条。",
    "",
]
for hub in hubs:
    pj = hub.split("-")[1]
    top = sorted(proj_cards.get(pj, []), key=score, reverse=True)[:5]
    kws = []
    for n in top:
        for a in cards[n].get("aliases", [])[:2]:
            a = a.strip('"').strip()
            if a and a not in kws:
                kws.append(a)
    line1 = f"**{pj}** ｜ {hub_line[hub][:70]}"
    line2 = ("  关键词: " + " / ".join(kws[:8]) + " ｜ 承重: " + " ".join(f"[[{n}]]" for n in top)) if top else "  （尚无知识卡，入口=枢纽现况）"
    out += [line1, line2]
# D-62 显性卡节（活性轴：当前在办的注意力集合，检索优先）
import re as _re
actives = []
for p in list(VAULT.rglob("*.md")):
    if p.parent.name.startswith("_"):
        continue
    try:
        head = p.read_text(encoding="utf-8", errors="replace")[:600]
    except Exception:
        continue
    if _re.search(r"^活性: 显性", head, _re.M) and not p.stem.startswith("枢纽-"):
        q = _re.search(r"^q_status: (\S+)", head, _re.M)
        actives.append(f"[[{p.stem}]]" + (f"({q.group(1)})" if q else ""))
out += ["", f"## 当前显性卡（D-62 活性轴，枢纽卡外加）", "  " + (" ".join(sorted(actives)) if actives else "（无）")]
(IDX / "_路由地图.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"路由地图已生成：{len(hubs)} 项目，{sum(1 for _ in out)} 行；显性非枢纽卡 {len(actives)} 张")
