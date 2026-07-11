# -*- coding: utf-8 -*-
"""vault_lint.py — 第二大脑卡片规范检查 L1-L14（SOP_v3 附录C）
用法: $env:PYTHONUTF8='1'; python vault_lint.py [--fix]
唯一自动修复=L6(updated 落后 mtime 时校正, 需 --fix)。报告落 <BRAIN_ROOT>/_运行日志/lint_YYYYMMDD.md
"""
import os, re, sys, json, datetime
from pathlib import Path

from config import ROOT, VAULT, LOG_DIR  # 路径唯一源，见 config.py
CARD_DIRS = [VAULT / "卡片", VAULT / "登记", VAULT / "MOC"]

TYPES = {"概念","文献","方法","对话","关联","符号","事例","编年","枢纽","MOC","登记","问题","知识点","清单"}
TIERS = {"T0","T1","T2","T3"}
ACTIVE_RE = re.compile(r"^(显性|辅助 \d{4}-\d{2}-\d{2})$")  # D-62/64：显性=主线；辅助+日期=7 天保鲜自动降隐
CONF = {"已验证","文献","联想"}
STATUS = {"草稿","已审","已取代"}
EDGE_TYPES = {"用材","用法","同理","支持","冲突","延伸","类比","出处","取代者","引用","上位"}
EDGE_RE = re.compile(r"^(用材|用法|同理|支持|冲突|延伸|类比|出处|取代者|引用|上位)::\s*\[\[([^\]]+)\]\]\s*(?:—|--|-)?\s*(.*)$")
STRENGTH_RE = re.compile(r"^（([^）]{1,3})）")  # D-39: 理由前缀强弱标注，仅允许（强）/（弱）
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
BAD_NAME_RE = re.compile(r'[\\/:*?"<>|]')
CONFLICT_PAT = ("冲突", "-DESKTOP-", "-SURFACE-")
PREFIX = {"概念":"概念-","文献":"文献-","方法":"方法-","对话":"对话-","关联":"关联-","符号":"符号-","事例":"事例-","编年":"编年-","枢纽":"枢纽-","MOC":"MOC-","登记":"登记-","问题":"问题-","知识点":"知识点-","清单":"清单-"}
REQ = ["schema","type","tier","projects","confidence","status","origin","created","updated","source"]

def parse_front(text):
    if not text.startswith("---"): return None, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m: return None, text
    fm = {}
    for line in m.group(1).splitlines():
        line = line.split("#")[0].rstrip() if not line.strip().startswith("#") else ""
        if ":" not in line: continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            fm[k] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
        else:
            fm[k] = v
    return fm, text[m.end():]

def d(s):
    try: return datetime.date.fromisoformat(str(s))
    except Exception: return None

def lint(fix=False):
    issues, cards, edges = [], {}, []
    files = [p for cd in CARD_DIRS if cd.exists() for p in cd.rglob("*.md")]
    for p in files:
        rel = p.relative_to(VAULT).as_posix()
        name = p.stem
        if BAD_NAME_RE.search(name) or name != name.strip():
            issues.append(f"L13|{rel}|文件名禁字符或首尾空格")
        if any(pat in p.name for pat in CONFLICT_PAT[1:]) or "冲突" in p.name and "卡" not in p.name:
            issues.append(f"L11|{rel}|疑似同步冲突副本")
        try: text = p.read_text(encoding="utf-8")
        except Exception as e:
            issues.append(f"L1|{rel}|无法读取 {e}"); continue
        fm, body = parse_front(text)
        if fm is None or "schema" not in fm:
            issues.append(f"L1|{rel}|frontmatter 缺失或无 schema"); continue
        miss = [k for k in REQ if k not in fm or fm[k] in ("", [], None)]
        if miss: issues.append(f"L2|{rel}|缺必填字段 {miss}")
        t = fm.get("type","")
        if t not in TYPES: issues.append(f"L3|{rel}|type 非法 {t}")
        if fm.get("tier") not in TIERS: issues.append(f"L3|{rel}|tier 非法 {fm.get('tier')}")
        if fm.get("confidence") not in CONF: issues.append(f"L3|{rel}|confidence 非法")
        if fm.get("status") not in STATUS: issues.append(f"L3|{rel}|status 非法")
        if "活性" in fm and not ACTIVE_RE.match(str(fm.get("活性","")).strip()): issues.append(f"L3|{rel}|活性 非法（只允许=显性 或 辅助 YYYY-MM-DD；隐性不写此字段）")
        if t == "概念":
            if fm.get("provenance") not in {"文献共识","文献+自研","自研数据","自研推导"}:
                issues.append(f"L2|{rel}|概念卡缺 provenance 或枚举非法")
        if t in PREFIX and not name.startswith(PREFIX[t]):
            issues.append(f"L13|{rel}|文件名前缀与 type 不符")
        al = fm.get("aliases", [])
        if fm.get("tier") in {"T1","T2","T3"} and (not isinstance(al,list) or len(al) < 2):
            issues.append(f"L4|{rel}|aliases <2")
        o,c,u = d(fm.get("origin")), d(fm.get("created")), d(fm.get("updated"))
        if not (o and c and u): issues.append(f"L5|{rel}|时间戳缺失或格式错")
        elif not (o <= c <= u): issues.append(f"L5|{rel}|违反 origin<=created<=updated")
        mtime = datetime.date.fromtimestamp(p.stat().st_mtime)
        if u and u < mtime:
            if fix:
                new = re.sub(r"(^updated:\s*).*$", rf"\g<1>{mtime.isoformat()}", text, count=1, flags=re.M)
                p.write_text(new, encoding="utf-8")
                issues.append(f"L6|{rel}|updated 已自动校正为 {mtime}")
            else:
                issues.append(f"L6|{rel}|updated({u}) 落后 mtime({mtime})，--fix 可校正")
        out_edges, has_super, in_rel = [], False, False
        for line in body.splitlines():
            ls = line.strip()
            if ls.startswith("## "):
                in_rel = ls.startswith("## 关联")
            em = EDGE_RE.match(ls)
            if em:
                et, tgt, reason = em.group(1), em.group(2), em.group(3).strip()
                out_edges.append((et, tgt, reason))
                if et == "取代者": has_super = True
                if not reason: issues.append(f"L8|{rel}|{et} 边缺理由")
                sm = STRENGTH_RE.match(reason)
                if sm and sm.group(1) not in ("强", "弱"):
                    issues.append(f"L15|{rel}|强弱标注非法（只许（强）/（弱））: （{sm.group(1)}）")
            elif in_rel and "[[" in ls and not ls.startswith("#") and "::" not in ls:
                issues.append(f"L7|{rel}|关联节裸链接: {ls[:50]}")
            else:
                um = re.match(r"^(\S+?)::\s*\[\[", ls)
                if um and um.group(1) not in EDGE_TYPES:
                    issues.append(f"L8|{rel}|未知边型: {um.group(1)}::")
        if fm.get("status") == "已取代" and not has_super:
            issues.append(f"L12|{rel}|已取代卡缺 取代者:: 边")
        in_src = False
        for line in body.splitlines():
            if line.strip().startswith("## 出处"): in_src = True; continue
            if line.startswith("## "): in_src = False
            if in_src and line.strip().startswith("- "):
                seg = line.strip()[2:].split("｜")[0]
                path_part = (seg.rsplit("（", 1)[0] if "（" in seg else seg).strip().strip("`")
                if path_part.startswith(("文献依据", "http://", "https://", "联网核实", "WebSearch", "NAS", "//", "\\\\", "/volume")): continue
                if path_part and "/" in path_part.replace("\\","/"):
                    tgt = ROOT / path_part.replace("/", os.sep)
                    if not tgt.exists(): issues.append(f"L9|{rel}|出处路径不存在: {path_part}")
        body_lines = len([l for l in body.splitlines() if l.strip()])
        if t == "MOC" and len(out_edges) > 30: issues.append(f"L14|{rel}|MOC 超 30 链")
        if fm.get("tier") == "T2" and t not in ("枢纽","MOC") and body_lines > 40:
            issues.append(f"L14|{rel}|T2 卡过长({body_lines}行)")
        cards[name] = {"rel": rel, "fm": fm, "out": out_edges}
        for et, tgt, reason in out_edges: edges.append((name, et, tgt))
    linked = set()
    for src, et, tgt in edges: linked.add(src); linked.add(tgt)
    for name, info in cards.items():
        if info["fm"].get("type") in ("MOC","枢纽"): continue
        if name not in linked: issues.append(f"L10|卡片/{name}.md|孤儿卡（零边）——违反零孤立原则 D-21")
    home = VAULT / "HOME.md"
    if home.exists() and len(home.read_text(encoding="utf-8").splitlines()) > 100:
        issues.append("L14|HOME.md|超 100 行")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    rep = LOG_DIR / f"lint_{stamp}.md"
    lines = [f"# lint 报告 {stamp}", f"- 检查卡片数: {len(cards)}", f"- 问题数: {len(issues)}", ""]
    lines += [f"- {i}" for i in issues] or ["- 全部通过 ✅"]
    rep.write_text("\n".join(lines), encoding="utf-8")
    print(f"cards={len(cards)} issues={len(issues)} report={rep.name}")
    for i in issues: print(" ", i)
    return 0 if not issues else 1

if __name__ == "__main__":
    sys.exit(lint(fix="--fix" in sys.argv))
