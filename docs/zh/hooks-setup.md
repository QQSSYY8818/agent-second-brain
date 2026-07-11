# Claude Code 接入指南

*[English](../en/hooks-setup.md)*

两个钩子把第二大脑从"手动查的资料库"变成"本能"：读侧每条消息自动注入相关记忆，写侧每轮会话自动收割结论——全程零人工、收割侧零 LLM token。

## 1. 两个钩子

合并 `hooks/settings.example.json` 的 `hooks` 节到你的 `~/.claude/settings.json`（Windows: `C:\Users\<你>\.claude\settings.json`）：

| 钩子 | 脚本 | 作用 |
|------|------|------|
| `UserPromptSubmit` | `engine/brain_inject.py` | 每条用户消息到达模型前：词面+语义+used 三路加权 → top-4 相关卡的一行描述注入上下文（总分低于阈值宁可不注；短确认消息跳过） |
| `Stop` | `engine/transcript_harvest.py` | 每轮会话结束：正则扫 transcript → 结论候选落 `vault/_inbox/` 待分拣 + 本轮读过的卡自动 used+1（异步执行不阻塞） |

**改路径**：示例里的脚本路径换成你 clone 的实际位置；Python 用 3.10+。**Windows 务必在 settings.json 的 `env` 里设 `"PYTHONUTF8": "1"`**，否则中文卡片乱码。

## 2. 可选件：本地语义检索（Ollama）

不装也能用（注入器自动降级为词面+used 两路）。装了更准：

```bash
ollama pull bge-m3          # 多语嵌入模型，~1.2GB
python engine/vault_embed.py    # 建向量库（增量，卡 updated 不变则跳过）
```

注入器每次会先 1.5 秒探活 Ollama——服务半死不会拖满钩子超时。

## 3. 日常维护

```bash
# 每次改卡后（维护三连+三环）
python engine/vault_lint.py         # 不过就修，--fix 可自动校正 updated
python engine/vault_catalog.py      # 再生 总目录/邻接表/现况总览/热核
python engine/vault_routemap.py     # 刷新第 0 跳路由地图
python engine/vault_rings.py        # 刷新三环视图（顺带清过期辅助标）

# 新东西入脑（生成卡骨架+候选边提名单，人工确认后落卡）
python engine/brain_intake.py <文件路径>
python engine/brain_intake.py --note "一段要点"

# 月度
python engine/vault_patrol.py       # 巡检报告 → _运行日志/
python engine/brain_audit.py        # 关联性体检 → _大脑审计/
```

建议把 patrol 挂系统计划任务（Windows 任务计划程序 / cron）每月 1 日跑。

## 4. 已知坑（都踩过）

| 坑 | 解法 |
|----|------|
| Windows 中文乱码 | 任何脚本前 `$env:PYTHONUTF8='1'`；settings.json 的 env 节写死 |
| PowerShell 5.1 `Set-Content -Encoding UTF8` 写卡带 BOM → lint 报 frontmatter 缺失 | 整文件重写用 UTF-8 无 BOM（Python/`[IO.File]::WriteAllText`）；追加用 `Add-Content` 无此问题 |
| 钩子把会话拖慢 | 注入钩子恒 exit 0 + Ollama 1.5s 探活熔断；收割钩子设 `"async": true` |
| 机器通知类消息触发无意义注入 | 注入器内置短消息/斜杠命令跳过 + 元词负词表（讨论系统自身时防自指噪声） |
| 卡放云同步盘出现 `-DESKTOP-`/`-SURFACE-` 冲突副本 | lint L11 会抓；权威库放固定一处（NAS/本地），别让两台机器同时写 |

## 5. 多机共用

把仓库放 NAS/网络盘，各机器设同一 `BRAIN_ROOT` 环境变量（或都用 UNC 路径 clone 位置）即可——vault 是纯文件，天然多机可读。**写权威只能有一个来源**（钩子只在主力机开），否则会出现双写分裂。
