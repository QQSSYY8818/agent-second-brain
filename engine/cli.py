# -*- coding: utf-8 -*-
"""asb — agent-second-brain 命令行 / the agent-second-brain CLI

用法 Usage:
  asb init [目录]     在目录（默认当前目录）脚手架一个新大脑 / scaffold a new brain
  asb up              维护四连 lint → catalog → routemap → rings
  asb lint [--fix] | catalog | routemap | rings | patrol | audit
  asb embed | search "问题" | touch 卡名... | intake <文件|--note "要点">

所有命令在"大脑根目录"（含 vault/ 的目录）下运行，或设 BRAIN_ROOT 环境变量。
Run inside your brain root (the directory containing vault/), or set BRAIN_ROOT.
"""
import sys, shutil, runpy
from pathlib import Path

PKG = Path(__file__).resolve().parent

SCRIPTS = {
    "lint": "vault_lint.py", "catalog": "vault_catalog.py", "routemap": "vault_routemap.py",
    "rings": "vault_rings.py", "patrol": "vault_patrol.py", "audit": "brain_audit.py",
    "embed": "vault_embed.py", "search": "vault_semantic_search.py", "touch": "vault_touch.py",
    "intake": "brain_intake.py", "inject": "brain_inject.py", "harvest": "transcript_harvest.py",
    "chunk": "session_chunker.py",
}
VAULT_DIRS = ["卡片", "MOC", "登记", "_inbox", "_索引", "_回收站"]


def run_script(script, args):
    """以脚本自身的 __main__ 方式运行（保持与 python engine/xxx.py 完全同构）。"""
    if str(PKG) not in sys.path:
        sys.path.insert(0, str(PKG))
    sys.argv = [script] + list(args)
    try:
        runpy.run_path(str(PKG / script), run_name="__main__")
        return 0
    except SystemExit as e:
        return int(e.code or 0)


def cmd_init(target):
    dst = Path(target).resolve()
    if (dst / "vault").exists():
        print(f"已存在 vault，跳过不覆盖 / vault already exists, not overwriting: {dst / 'vault'}")
        return 1
    src = PKG / "_scaffold" / "vault"
    if src.exists():
        shutil.copytree(src, dst / "vault")
    else:  # 源码运行且未打包 scaffold 时，退回仓库自带 vault
        repo_vault = PKG.parent / "vault"
        if not repo_vault.exists():
            print("找不到 vault 脚手架 / scaffold not found"); return 1
        shutil.copytree(repo_vault, dst / "vault",
                        ignore=shutil.ignore_patterns("_索引", "_现况总览.md", ".gitkeep"))
    for d in VAULT_DIRS:
        (dst / "vault" / d).mkdir(exist_ok=True)
    for d in ("_运行日志", "_入脑暂存", "_大脑审计"):
        (dst / d).mkdir(exist_ok=True)
    print(f"大脑已就位 / brain scaffolded: {dst}")
    print("下一步 next:  cd 进该目录后 → asb lint --fix → asb up")
    return 0


def cmd_up():
    """维护四连；lint 失败即停。"""
    for name, script in (("lint", "vault_lint.py"), ("catalog", "vault_catalog.py"),
                         ("routemap", "vault_routemap.py"), ("rings", "vault_rings.py")):
        print(f"== asb {name} ==")
        code = run_script(script, [])
        if name == "lint" and code != 0:
            print("lint 未通过，四连中止（先修卡或 asb lint --fix）/ lint failed, aborting")
            return code
    return 0


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = args[0], args[1:]
    if cmd == "init":
        return cmd_init(rest[0] if rest else ".")
    if cmd == "up":
        return cmd_up()
    if cmd in SCRIPTS:
        return run_script(SCRIPTS[cmd], rest)
    print(f"未知命令 unknown command: {cmd}\n")
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
