# -*- coding: utf-8 -*-
"""brain_inject.py — 本能引擎（UserPromptSubmit 钩子，D-34；2026-07-10 检索干净化两段式升级）
用户每条消息到达 Claude 之前：词面(瘦目录)+bge-m3 语义 双路候选 → 加权(语义0.5+词面0.3+used0.2)
→ top-4 → 总分低于 INJECT_THRESHOLD 宁可不注 → description 空的卡禁入 → 元词负词表防自指噪声。
恒 exit 0；Ollama 不在则词面+used 两路降级（权重 0.6/0.4）；短指令/斜杠命令跳过。stdout 即注入内容。
每次实际注入追加一行遥测到 vault/_索引/_注入日志.jsonl（供每周抽样评相关率，<50% 调阈值）。
"""
import sys, json, re, datetime, urllib.request
from pathlib import Path

from config import VAULT  # 权威 vault 唯一源(项目大脑)，见 config.py
SKIP_EXACT = {"继续", "好", "好的", "嗯", "开工", "开工吧", "ok", "OK", "收到", "谢谢", "停", "等一下", "继续任务吧", "可以", "行"}

# ===== 检索干净化常量（2026-07-10 定标，调阈值只改这里）=====
# 注入阈值：加权总分(0~1)低于此值一张不注（宁缺毋滥）。定标逻辑：
#   纯语义命中：cos≥0.68 才独立过线（0.5*0.68=0.34）——bge-m3 无关中文对本底约 0.3~0.45，0.68=确有含义关联；
#   词面强命中(lex=1.0,≥5词)+语义弱贴边(0.45)：0.5*0.45+0.3=0.525 过线；纯词面碎片(1~2词)无语义=过不了线。
INJECT_THRESHOLD = 0.34
TOP_K = 4          # 最多注入卡数（旧版 6 → 收窄）
SEM_FLOOR = 0.45   # 语义余弦低于此不计分（bge-m3 无关文本对的相似度本底）
LEX_CAP = 5        # 词面命中词数达此数记满分 1.0
USED_CAP = 8       # used 计数达此数记满分 1.0
# 负词表：讨论第二大脑系统自身时，这些元词在大量卡的 name/描述里都出现，词面匹配=纯噪声；
# 查询含这些词时，这些词不参与词面匹配（语义路不受影响——元讨论题靠语义命中审计/规范卡）。
META_WORDS = ("第二大脑", "总目录", "邻接表", "检索", "卡片", "枢纽", "大脑", "注入", "钩子", "索引", "目录", "vault")


def main():
    try:
        data = json.load(sys.stdin)
        prompt = (data.get("prompt") or "").strip()
        if len(prompt) < 4 or prompt.startswith("/") or prompt in SKIP_EXACT:
            return
        idx = VAULT / "_索引"
        # —— 候选卡池：瘦目录（真卡目录），排除编年与空 description ——
        cat_file = idx / "_结论卡目录.jsonl"
        if not cat_file.exists():
            cat_file = idx / "_卡片总目录.jsonl"
        cards = {}
        for line in cat_file.read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            name = str(c.get("name", ""))
            if c.get("type") == "登记" or name.startswith("编年"):
                continue
            if not (c.get("description") or "").strip():
                continue  # description 空的卡禁入注入（空描述=注了也无判别力，治理靠巡检）
            cards[name] = c
        # —— 词面路（负词表先剔除元词，再抽词）——
        lex_prompt = prompt
        for w in META_WORDS:
            lex_prompt = lex_prompt.replace(w, " ")
        terms = set(re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", lex_prompt))
        for w in re.findall(r"[一-鿿]{2,}", lex_prompt):
            for i in range(len(w) - 1):
                terms.add(w[i:i + 2])
        lex = {}
        for name, c in cards.items():
            hay = (name + " " + " ".join(c.get("aliases") or []) + " " + (c.get("description") or "")).lower()
            n = sum(1 for t in terms if t.lower() in hay)
            if n:
                lex[name] = min(n / LEX_CAP, 1.0)
        # —— 语义路（调 vault_semantic_search 的检索函数；Ollama 不在则静默降级两路）——
        sem, sem_ok = {}, False
        try:
            with urllib.request.urlopen("http://localhost:11434/api/version", timeout=1.5):
                pass  # 快速探活，避免 Ollama 半死时钩子拖满 timeout
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from vault_semantic_search import embed, cos
            qv = embed(prompt[:500])
            for l in (idx / "_向量库.jsonl").read_text(encoding="utf-8").splitlines():
                v = json.loads(l)
                if v["name"] not in cards:
                    continue
                cs = cos(qv, v["vector"])
                if cs >= SEM_FLOOR:
                    sem[v["name"]] = cs
            sem_ok = True
        except Exception:
            pass
        # —— 加权合并（used 从目录行读，目录由 vault_catalog 从卡 frontmatter used: 提取，无=0）——
        scored = []
        for name in set(lex) | set(sem):
            try:
                used_raw = int(cards[name].get("used", 0) or 0)
            except Exception:
                used_raw = 0
            u = min(used_raw / USED_CAP, 1.0)
            if sem_ok:
                total = 0.5 * sem.get(name, 0.0) + 0.3 * lex.get(name, 0.0) + 0.2 * u
            else:
                total = 0.6 * lex.get(name, 0.0) + 0.4 * u  # 降级两路：语义缺席时按比例重分权
            scored.append((total, name, sem.get(name, 0.0), lex.get(name, 0.0), u))
        top = [x for x in sorted(scored, reverse=True)[:TOP_K] if x[0] >= INJECT_THRESHOLD]
        # 脑暴可见协议（2026-07-10 用户定，烧进本能层防遗忘）：零命中也必须输出空报告——
        # Claude 与用户都要看见"查过了没有"。标记=[头脑风暴中... ...]/[脑暴结束]/[脑暴内容已产出]/[头脑空空，寻求外部资源]
        PROTO = ("（脑暴协议：答前发[头脑风暴中... ...]→检完发[脑暴结束]→上列卡确有帮助=[脑暴内容已产出]并在正文引卡名；"
                 "无帮助或本报告为空=[头脑空空，寻求外部资源]并如实标注答案来源。纯确认短消息免。）")
        if not top:
            print("【第二大脑·预检索注入】本条查询库内零命中（阈值 0.34 下宁缺勿滥）。\n" + PROTO)
            return
        out = ["【第二大脑·预检索注入（自动系统信息，非用户输入）】与本条消息可能相关的已有知识："]
        for total, name, *_ in top:
            out.append(f"- [[{name}]]：{cards[name].get('description', '')[:60]}")
        out.append("（相关则先读卡再答；引用结论前核对是否已被取代。卡在 vault\\卡片\\ 或 vault\\MOC\\。）")
        out.append(PROTO)
        print("\n".join(out))
        try:  # ⑤ 注入遥测：每次实际注入追加一行（每周抽 10 条人判相关率，<50% 调 INJECT_THRESHOLD）
            rec = {"ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "query": prompt[:40], "sem_ok": sem_ok,
                   "cards": [{"name": n, "total": round(t, 3), "sem": round(s, 3),
                              "lex": round(lx, 3), "used": round(u, 3)}
                             for t, n, s, lx, u in top]}
            with open(idx / "_注入日志.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
    except Exception:
        pass
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
