# agent-second-brain

**[English](README.md)** | 简体中文

> **给 AI agent 装一个永不失忆的第二大脑。**
> 文件型知识卡网络 + 分层检索路由 + Claude Code 钩子自动注入/收割。纯 Python 标准库，**零第三方依赖**，clone 即用。
>
> A file-based second brain for AI agents: a card network with typed edges, budget-capped retrieval routing, and Claude Code hooks for automatic recall & harvest. Pure stdlib Python, zero dependencies.

---

## 为什么需要它：三个承诺

### 1. 永久性思维能力

会话会结束、上下文窗口会满、模型会换代——**卡片网络不会**。每个结论、决策、教训都固化成一张带 frontmatter 的 Markdown 卡，卡与卡之间用带理由的边连接。任何新会话开局，钩子自动把相关记忆注入上下文，agent 立刻"接上"过去所有的思考。知识只进化不丢失：**永不删除**，过时的卡走"降档"或"取代"（`取代者::` 边指向新结论），错误的历史也保留为可追溯的判断轨迹。

### 2. token 经济学

第二大脑不是把整个知识库塞进上下文——那是最贵也最笨的做法。这套系统的每一层都在省 token：

- **注入层**：每条用户消息只注入 top-4 相关卡的**一行描述**（词面+语义+使用频率三路加权，总分不过阈值宁可一张不注）；
- **检索层**：硬预算路由——第 0 跳读一屏路由地图 → 定项目 → 顺边逐跳读卡，**全程 ≤8 次文件读取封顶**，而不是全库扫描；
- **收割层**：会话结束钩子用纯正则从 transcript 提取结论候选和使用记录，**零 LLM token**；
- **索引层**：目录/邻接表/向量库全部预计算成 jsonl，grep 一击定位，不需要让模型"想起来"。

### 3. 关联性

边是一等公民。十种边型（支持/冲突/延伸/类比/上位/用法/用材/同理/出处/引用），**每条边必须带一行理由**——理由是判断的缓存，下次不用重新想。关联性还有三个自动回路：

- **上位轴 V 字跳**：实例卡 →（上位）→ 家族概念卡 →（反查）→ 其他领域的实例——跨项目联想的机械实现；
- **Hebbian 权重**：每次真实调用让卡的 `used` 计数 +1，常用知识自动浮到检索入口第 0 跳；
- **机械审计**：矛盾边、孤儿卡、上位环、层级倒挂——`brain_audit.py` 全库体检，网络健康可度量。

---

## 工作原理（一图流）

```
 用户消息 ──► [UserPromptSubmit 钩子] brain_inject.py
              词面 + 语义(可选Ollama) + used 三路加权 → top-4 卡描述注入上下文
                     │
 agent 答题 ──► 需要深挖时按检索协议走：
              路由地图(第0跳,一屏) → 枢纽现况(第1跳) → 顺边跳卡(≤2张/跳)
              → V字跳跨项目 → 全程 ≤8 次读取封顶
                     │
 会话结束 ──► [Stop 钩子] transcript_harvest.py（零token正则）
              结论候选 → vault/_inbox/   待人工分拣落卡
              本轮读过的卡 → used+1      （Hebbian 回路闭环）
                     │
 维护三连 ──► vault_lint → vault_catalog → vault_routemap (+ vault_rings)
              规范检查 → 目录/邻接表再生 → 路由地图刷新 → 三环注意力视图
```

## 快速开始

```bash
git clone https://github.com/QQSSYY8818/agent-second-brain.git
cd agent-second-brain

# Windows 先设 UTF-8（编码坑，见 docs/hooks-setup.md）
# PowerShell:  $env:PYTHONUTF8='1'

python engine/vault_lint.py --fix   # 首跑：校正 clone 产生的文件时间戳
python engine/vault_lint.py         # 自带 4 张演示卡，应输出 issues=0
python engine/vault_catalog.py      # 生成 卡片总目录 + 邻接表 + 热核
python engine/vault_routemap.py     # 生成第 0 跳路由地图
python engine/vault_rings.py        # 生成三环注意力视图
```

四条命令跑通 = 大脑骨架活了。接下来：

1. **接入 Claude Code**：把 `hooks/settings.example.json` 里的两个钩子合并进你的 `~/.claude/settings.json`（详见 [docs/zh/hooks-setup.md](docs/zh/hooks-setup.md)）；
2. **长出第一批卡**：照 `vault/_模板/` 建卡，或用 `python engine/brain_intake.py <文件>` 让机械层先生成卡骨架+候选边提名单；
3. **可选语义检索**：本地装 [Ollama](https://ollama.com) + `bge-m3` 嵌入模型，跑 `python engine/vault_embed.py` 建向量库——注入器自动升级为词面+语义双路（没有 Ollama 也能跑，自动降级纯词面）。

## 仓库结构

```
engine/            14 个引擎脚本（纯标准库）
  config.py          路径唯一源（环境变量可覆盖，默认 clone 即用）
  vault_lint.py      卡片规范检查 L1-L15（frontmatter/边型/理由/孤儿卡/时间戳）
  vault_catalog.py   总目录+邻接表+现况总览+热核 生成器
  vault_routemap.py  第 0 跳路由地图（度+3×used 承重排序）
  vault_rings.py     三环注意力视图（显性入口/在网层/沉淀层）+ 辅助标 7 天自动过期
  vault_touch.py     used+1 使用计数（Hebbian 回路的记账笔）
  vault_embed.py     向量库生成（可选，需 Ollama+bge-m3）
  vault_semantic_search.py  语义兜底检索
  vault_patrol.py    月度巡检（lint→索引再生→陈旧度→零入边→枢纽时效）
  brain_inject.py    UserPromptSubmit 钩子：三路加权注入 top-4
  brain_intake.py    入脑管线：新文件/要点 → 卡骨架+候选边提名单
  brain_audit.py     关联性全库审计（矛盾边/上位环/层级倒挂/星形卡）
  transcript_harvest.py  Stop 钩子：零 token 收割结论+自动 touch
  session_chunker.py 历史状态日志回填切块（存量记忆迁移用）
vault/             卡片库（自带 4 张演示卡，lint 全绿）
  卡片/  MOC/  登记/  _inbox/  _索引/  _模板/(11 张卡模板)  _回收站/
  HOME.md  _热核.md  _待办.md  _检索失败日志.md
docs/zh/  docs/en/   四份设计文档（中英双语）
  architecture.md        总体架构：双体大脑/入口金字塔/五个自动回路/三环视图
  card-spec.md           卡片规格：frontmatter/14 类卡型/边十型/活性轴
  retrieval-protocol.md  检索协议：≤8 次读取预算/题型路由/V 字跳/miss 升级
  hooks-setup.md         Claude Code 接入：两钩子配置+Ollama 可选件+已知坑
hooks/             settings.example.json（可直接合并的钩子片段）
```

## 设计渊源

这套架构不是凭空发明的，它综合了：**A-MEM**（卡=内容+关键词+语境+链接集，记忆进化）、**Zep/GraphRAG**（时间图与层级社区摘要）、**LYT/MOC** 与 **Evergreen notes**（人类 PKM 的成熟实践）、Discourse Graph（问题卡）——再加上在真实科研工作流里数百次会话的实战打磨。各设计点在文档中以 D-xx 决策编号引用，保持了可追溯性。

## FAQ

- **必须用 Claude Code 吗？** 不。钩子层是 Claude Code 专用的，但 vault+引擎是纯文件系统操作，任何能读文件的 agent（或人）都能用；Obsidian 可直接打开 vault 获得图谱视图。
- **中文写的，英文项目能用吗？** 卡片内容语言不限；卡型/边型关键字目前是中文枚举（`概念-`/`支持::`），fork 后改 `vault_lint.py` 顶部的枚举表即可本地化。
- **和 RAG 什么关系？** 互补。RAG 是"检索原文片段"，这里管理的是**判断层**——结论、决策、教训及其关联；向量检索只是本系统的兜底路，不是主干。

## License

MIT。卡片内容归你——这套系统的立场是：**判断必须由人（或你的 agent）做，框架只负责让判断不被遗忘。**
