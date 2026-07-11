# -*- coding: utf-8 -*-
"""agent-second-brain 路径配置 —— 所有脚本唯一的路径来源，禁止在脚本里各自硬编码。

默认约定（clone 即用，零配置）：
    <仓库根>/
      engine/     ← 本文件所在目录
      vault/      ← 卡片库（VAULT）
      _运行日志/   ← lint/巡检报告（自动创建）
      _入脑暂存/   ← brain_intake 提名单（自动创建）
      _大脑审计/   ← brain_audit 报告（自动创建）

自定义（把大脑放到 NAS/别的盘时）：设环境变量
    BRAIN_ROOT          大脑根目录（vault 的上级）
    BRAIN_VAULT         直接指定 vault（优先级高于 BRAIN_ROOT/vault）
    BRAIN_PROJECTS_ROOT 你的项目文件区根目录（lint 的「出处路径存在性」检查用；不设=跳过该检查基准）
"""
import os
from pathlib import Path

# 大脑根解析顺序：BRAIN_ROOT 环境变量 > 当前目录含 vault/（pip 安装后 asb 的工作模式）> 本文件上级（git clone 模式）
_env_root = os.environ.get("BRAIN_ROOT")
if _env_root:
    BRAIN_ROOT = Path(_env_root)
elif (Path.cwd() / "vault").exists():
    BRAIN_ROOT = Path.cwd()
else:
    BRAIN_ROOT = Path(__file__).resolve().parents[1]

# 权威 vault —— 全系统唯一真相
VAULT = Path(os.environ.get("BRAIN_VAULT", BRAIN_ROOT / "vault"))

# 项目文件区根（卡片「出处」节里的相对路径以此为基；不设则退回 BRAIN_ROOT）
PROJECTS_ROOT = Path(os.environ.get("BRAIN_PROJECTS_ROOT", BRAIN_ROOT))
ROOT = PROJECTS_ROOT  # 兼容别名：vault_lint 等旧引用

# 运行产物目录（脚本自动创建）
LOG_DIR = BRAIN_ROOT / "_运行日志"
INTAKE_DIR = BRAIN_ROOT / "_入脑暂存"
AUDIT_DIR = BRAIN_ROOT / "_大脑审计"

# session_chunker 的历史快照来源（可选：状态日志目录列表，按需在此添加）
SESSION_LOG_DIRS = []
