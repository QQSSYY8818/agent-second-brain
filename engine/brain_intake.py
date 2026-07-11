# -*- coding: utf-8 -*-
r"""brain_intake.py — 入脑管线 v0（D-60）：新东西出现→最快路径生成卡骨架+候选边提名单。
用法：
  python brain_intake.py <文件路径> [--type 概念|文献|方法|事例|对话|关联]
  python brain_intake.py --note "一段对话要点或新知识" [--projects 03,09]
流程：①元数据+正文取样 ②关键词（本地 glm-4.7-flash 零 token，失败退回词元匹配）
     ③候选项目（路由地图）+候选边（总目录 name/aliases/description 打分，带证据词）
     ④产出提名单 → <BRAIN_ROOT>\_入脑暂存\提名单_<名>_<日期>.md
判断层（Fable/用户）确认后：照骨架落卡 vault\卡片\，候选边逐条采/拒。机械部分零判断零污染。
"""
import sys, json, re, datetime, urllib.request
from pathlib import Path

SCRIPT = Path(__file__).resolve()
from config import VAULT, INTAKE_DIR  # 路径唯一源，见 config.py
IDX = VAULT / "_索引"
OUT = INTAKE_DIR
TODAY = datetime.date.today().isoformat()

def jsonl(p):
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)

def ollama_keywords(text):
    try:
        body = json.dumps({"model": "glm-4.7-flash", "think": False, "stream": False,
                           "prompt": "从下文提取5-8个中英文关键词（学术/技术名词优先），只输出逗号分隔的一行，不解释：\n" + text[:1500]}).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", body,
                                     {"Content-Type": "application/json"})
        resp = json.load(urllib.request.urlopen(req, timeout=30))
        raw = (resp.get("response") or "").strip()
        ks = [k.strip(" -•*\t") for k in re.split(r"[,，、/\n]", raw)]
        return [k for k in ks if 1 < len(k) < 40][:8]
    except Exception:
        return []

STOP = {"paper", "draft", "figure", "results", "data", "model", "method", "file",
        "analysis", "study", "version", "note", "test", "修改", "说明", "文件",
        "数据", "结果", "分析", "版本", "草稿", "报告", "文档"}

def tokens_of(s):
    out = []
    for t in re.split(r"[^0-9A-Za-z一-鿿µσΓ√₀]+", s):
        if not t or re.fullmatch(r"\d+", t) or re.match(r"^20\d\d", t):
            continue  # 纯数字/年份/日期词元=噪声，剔除
        if re.search(r"[一-鿿]", t):
            if len(t) >= 2: out.append(t)
        elif len(t) >= 3:
            out.append(t)
    return out

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    note = None
    if "--note" in args:
        note = args[args.index("--note") + 1]
    ctype = args[args.index("--type") + 1] if "--type" in args else None
    projs = args[args.index("--projects") + 1].split(",") if "--projects" in args else []

    if note:
        name, src, text, origin = f"对话要点_{TODAY}", f"会话 {TODAY}", note, TODAY
    else:
        f = Path(args[0])
        if not f.exists():
            print(f"文件不存在: {f}"); return
        name, src = f.stem, str(f)
        origin = datetime.date.fromtimestamp(f.stat().st_mtime).isoformat()
        text = ""
        if f.suffix.lower() in (".md", ".txt", ".py", ".ps1", ".json", ".csv"):
            text = f.read_text(encoding="utf-8", errors="replace")[:4000]
        m = re.search(r"[\\/](\d{2})_[^\\/]+[\\/]", str(f))
        if m and not projs:
            projs = [m.group(1)]

    kws = ollama_keywords(text or name)
    kw_src = "glm-4.7-flash" if kws else "词元回退"
    if not kws:
        kws = tokens_of(name)[:8]
    terms = set()
    for k in kws:
        terms.update(t.lower() for t in tokens_of(k))
        if len(k) >= 3:
            terms.add(k.lower())
    terms.update(t.lower() for t in tokens_of(name))
    terms -= STOP

    # 候选项目：路由地图行匹配
    proj_hits = []
    for ln in (IDX / "_路由地图.md").read_text(encoding="utf-8").splitlines():
        low = ln.lower()
        hit = [t for t in terms if t in low]
        if hit and (ln.startswith("**") or ln.strip().startswith("关键词")):
            proj_hits.append((ln[:70], sorted(hit)[:4]))

    # 候选边：总目录打分（name×3 / aliases×2 / description×1）
    scored = []
    for c in jsonl(IDX / "_卡片总目录.jsonl"):
        hay_n, hay_a = c["name"].lower(), " ".join(c.get("aliases", [])).lower()
        hay_d = (c.get("description") or "").lower()
        sc, ev = 0, []
        for t in terms:
            if t in hay_n: sc += 3; ev.append(t)
            elif t in hay_a: sc += 2; ev.append(t)
            elif t in hay_d: sc += 1; ev.append(t)
        if sc:
            scored.append((sc, c["name"], sorted(set(ev))[:4]))
    scored.sort(reverse=True)

    guess = ctype or ("方法" if name.endswith((".py", ".ps1")) or "脚本" in name else "概念")
    lines = [f"# 入脑提名单：{name}（{TODAY}，机械层产出，待判断层确认）", "",
             f"- 源：`{src}`（origin={origin}）",
             f"- 关键词（{kw_src}）：{'、'.join(kws)}",
             f"- 项目归属候选：{','.join(projs) or '未定'}", "",
             "## 卡骨架（确认后落 vault\\卡片\\）", "```yaml",
             "schema: 1", f"type: {guess}", "tier: T1",
             f"projects: [{', '.join(projs) or 'XX'}]",
             "confidence: 已验证  # 或 文献/联想", "status: 草稿",
             f'aliases: ["{kws[0] if kws else name}", "<English alias 必填>"]',
             f"origin: {origin}", f"created: {TODAY}", f"updated: {TODAY}",
             f"source: {src}", "```", "",
             "## 候选边（提名制：逐条采/拒，采则补边型+一行理由；上位候选想一下家族伞卡）"]
    for sc, n, ev in scored[:8]:
        lines.append(f"- [ ] [[{n}]]（分{sc}，证据词：{'、'.join(ev)}）")
    lines += ["", "## 路由地图命中（项目层证据）"] + [f"- {l}（{'、'.join(h)}）" for l, h in proj_hits[:6]]
    lines += ["", "> 落卡后跑 lint→catalog→routemap 三连；强边（支持/冲突/取代）记得 D-52 回写目标卡。"]

    OUT.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|]', "_", name)[:60]
    out = OUT / f"提名单_{safe}_{TODAY}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"提名单已出：{out}（候选边 {min(len(scored),8)} 条，关键词源={kw_src}）")

if __name__ == "__main__":
    main()
