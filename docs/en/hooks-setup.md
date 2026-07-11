# Claude Code Integration

*[中文版](../zh/hooks-setup.md)*

Two hooks turn the second brain from "a database you remember to query" into **an instinct**: the read side auto-injects relevant memory on every message, the write side auto-harvests conclusions at the end of every session — no manual steps, and the harvest side costs zero LLM tokens.

## 1. The two hooks

Merge the `hooks` section of `hooks/settings.example.json` into your `~/.claude/settings.json` (Windows: `C:\Users\<you>\.claude\settings.json`):

| Hook | Script | What it does |
|------|------|------|
| `UserPromptSubmit` | `engine/brain_inject.py` | Before each user message reaches the model: lexical + semantic + used, 3-way weighted → the one-line descriptions of the top-4 relevant cards are injected (below threshold = inject nothing; short acknowledgements are skipped) |
| `Stop` | `engine/transcript_harvest.py` | At the end of each turn: regex-scan the transcript → conclusion candidates land in `vault/_inbox/` for triage + every vault card Read this session gets used+1 (runs async, never blocks) |

**Fix the paths**: replace the example script paths with your actual clone location; Python 3.10+. **On Windows you must set `"PYTHONUTF8": "1"` in the settings.json `env` block**, or Chinese card content will be garbled.

## 2. Optional: local semantic recall (Ollama)

Works without it (the injector degrades to lexical+used). Better with it:

```bash
ollama pull bge-m3              # multilingual embedding model, ~1.2GB
python engine/vault_embed.py    # build the vector store (incremental: unchanged cards are skipped)
```

The injector pings Ollama with a 1.5-second liveness probe first — a half-dead service will never drag the hook to its timeout.

## 3. Routine maintenance

```bash
# after every card change (the maintenance triple + rings)
python engine/vault_lint.py         # fix what fails; --fix auto-corrects timestamps
python engine/vault_catalog.py      # regen catalog / adjacency / status overview / hot core
python engine/vault_routemap.py     # refresh the hop-0 route map
python engine/vault_rings.py        # refresh the three-ring view (also expires stale auxiliary marks)

# feeding the brain (generates a card skeleton + candidate edges for you to confirm)
python engine/brain_intake.py <file>
python engine/brain_intake.py --note "a key point"

# monthly
python engine/vault_patrol.py       # patrol report → _运行日志/
python engine/brain_audit.py        # network health → _大脑审计/
```

Recommended: schedule the patrol on the 1st of each month (Windows Task Scheduler / cron).

## 4. Known pitfalls (all personally stepped on)

| Pitfall | Fix |
|----|------|
| Garbled Chinese on Windows | `$env:PYTHONUTF8='1'` before any script; hard-code it in the settings.json env block |
| PowerShell 5.1 `Set-Content -Encoding UTF8` writes a BOM → lint reports missing frontmatter | Full-file rewrites must be UTF-8 *without* BOM (Python / `[IO.File]::WriteAllText`); appending with `Add-Content` is safe |
| Hooks slow the session down | the injector always exits 0 + 1.5s Ollama probe with circuit-break; set the harvest hook `"async": true` |
| Machine-generated notification messages trigger junk injections | the injector skips short messages / slash commands and carries a meta-word stoplist (anti self-reference noise when discussing the system itself) |
| Cards on a cloud-sync drive grow `-DESKTOP-`/`-SURFACE-` conflict copies | lint L11 catches them; keep the authoritative vault in exactly one place (NAS/local) and never let two machines write simultaneously |

## 5. Multi-machine use

Put the repo on a NAS/network share and point every machine at the same `BRAIN_ROOT` env var (or clone at the same UNC path) — the vault is plain files, naturally multi-reader. **There must be exactly one write authority** (enable the hooks on your main machine only), or you will get split-brain double-writes.
