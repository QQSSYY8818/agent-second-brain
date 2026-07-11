# agent-second-brain

English | **[简体中文](README.zh-CN.md)**

[![PyPI](https://img.shields.io/pypi/v/agent-second-brain)](https://pypi.org/project/agent-second-brain/)
[![Downloads](https://img.shields.io/pypi/dm/agent-second-brain)](https://pypi.org/project/agent-second-brain/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)

> **Give your AI agent a second brain that never forgets.**
> A file-based knowledge-card network + budget-capped retrieval routing + Claude Code hooks for automatic recall & harvest. Pure stdlib Python, **zero third-party dependencies**, works right after clone.

---

## Why: three promises

### 1. Permanent thinking capability

Sessions end, context windows fill up, models get replaced — **the card network survives all of it**. Every conclusion, decision, and lesson is frozen into a Markdown card with frontmatter, and cards are wired together with *reasoned* edges. When a new session starts, a hook automatically injects the relevant memories into context, and the agent picks up exactly where all its past thinking left off. Knowledge only evolves, never disappears: **nothing is ever deleted** — outdated cards are demoted or superseded (a `取代者::`/superseded-by edge points to the new conclusion), and even wrong historical judgments are kept as a traceable record.

### 2. Token economics

A second brain is *not* "stuff the whole knowledge base into the context window" — that is the most expensive and dumbest possible design. Every layer here is built to save tokens:

- **Injection layer**: for each user message, only the **one-line descriptions** of the top-4 relevant cards are injected (lexical + semantic + usage-frequency weighted; below the threshold, nothing gets injected at all);
- **Retrieval layer**: hard-budget routing — hop 0 reads a one-screen route map → pick the project → follow edges card by card, **≤8 file reads total, hard cap** — never a full-library scan;
- **Harvest layer**: an end-of-session hook extracts conclusion candidates and usage records from the transcript with pure regex — **zero LLM tokens**;
- **Index layer**: catalog / adjacency list / vector store are all precomputed jsonl — one grep locates a card; the model never has to "try to remember".

### 3. Associativity

Edges are first-class citizens. Ten edge types (supports / conflicts / extends / analogy / is-a / uses / …), and **every edge must carry a one-line reason** — the reason is a cached judgment, so you never have to re-derive it. Three automatic loops keep the network associative:

- **The V-jump**: instance card → (is-a edge) → family concept card → (reverse lookup) → instances in *other* domains — cross-project association, mechanized;
- **Hebbian weighting**: every real use bumps a card's `used` counter, so frequently-used knowledge floats up to hop 0 of retrieval;
- **Mechanical audits**: contradictory edges, orphan cards, is-a cycles, hierarchy inversions — `brain_audit.py` gives the whole network a measurable health check.

---

## How it works (one diagram)

```
 user message ──► [UserPromptSubmit hook] brain_inject.py
                  lexical + semantic(optional Ollama) + used, weighted → top-4 card
                  descriptions injected into context
                        │
 agent answers ──► when it needs to dig deeper, it follows the retrieval protocol:
                  route map (hop 0, one screen) → hub status (hop 1)
                  → follow edges (≤2 cards/hop) → V-jump across projects
                  → ≤8 file reads total, hard cap
                        │
 session ends ──► [Stop hook] transcript_harvest.py  (zero-token regex)
                  conclusion candidates → vault/_inbox/   for human triage
                  cards Read this session → used+1        (Hebbian loop closed)
                        │
 maintenance  ──► vault_lint → vault_catalog → vault_routemap (+ vault_rings)
                  spec check → index regen → route map refresh → attention rings
```

## Quick start

**Option A — pip (recommended):**

```bash
pip install agent-second-brain

mkdir my-brain && cd my-brain
asb init          # scaffold a vault with 4 demo cards
asb lint --fix    # first run: align file timestamps
asb up            # the maintenance quadruple: lint → catalog → routemap → rings
```

**Option B — git clone:**

```bash
git clone https://github.com/QQSSYY8818/agent-second-brain.git
cd agent-second-brain

# On Windows set UTF-8 first (see docs/en/hooks-setup.md)
# PowerShell:  $env:PYTHONUTF8='1'

python engine/vault_lint.py --fix   # first run: fix clone-time file timestamps
python engine/vault_lint.py         # ships with 4 demo cards, should print issues=0
python engine/vault_catalog.py      # build card catalog + adjacency list + hot core
python engine/vault_routemap.py     # build the hop-0 route map
python engine/vault_rings.py        # build the three-ring attention view
```

All green = the skeleton is alive. Next:

1. **Wire up Claude Code**: merge the two hooks from `hooks/settings.example.json` into your `~/.claude/settings.json` (see [docs/en/hooks-setup.md](docs/en/hooks-setup.md));
2. **Grow your first cards**: copy from `vault/_模板/` (templates), or run `python engine/brain_intake.py <file>` and let the mechanical layer draft a card skeleton + candidate edges for you to confirm;
3. **Optional semantic recall**: install [Ollama](https://ollama.com) + the `bge-m3` embedding model, run `python engine/vault_embed.py` — the injector automatically upgrades to lexical+semantic dual-path (and degrades gracefully without Ollama).

## Repository layout

```
engine/            14 engine scripts (pure stdlib)
  config.py          single source of truth for paths (env-var overridable)
  vault_lint.py      card spec checks L1-L15 (frontmatter/edges/reasons/orphans/timestamps)
  vault_catalog.py   catalog + adjacency list + status overview + hot core generator
  vault_routemap.py  hop-0 route map (cards ranked by degree + 3×used)
  vault_rings.py     three-ring attention view + 7-day auto-expiry of auxiliary marks
  vault_touch.py     used+1 usage counter (the pen that closes the Hebbian loop)
  vault_embed.py     vector store builder (optional, Ollama+bge-m3)
  vault_semantic_search.py  semantic fallback search
  vault_patrol.py    monthly patrol (lint → index regen → staleness → zero-inlink → hub freshness)
  brain_inject.py    UserPromptSubmit hook: 3-way weighted top-4 injection
  brain_intake.py    intake pipeline: new file/note → card skeleton + candidate edges
  brain_audit.py     network health audit (contradictions/cycles/inversions/star cards)
  transcript_harvest.py  Stop hook: zero-token harvest + auto-touch
  session_chunker.py backfill chunker for migrating legacy work logs
vault/             the card vault (ships with 4 demo cards, lint-clean)
  卡片(cards)/  MOC/  登记(registry)/  _inbox/  _索引(index)/  _模板(templates)/  _回收站(recycle)/
  HOME.md  _热核(hot core).md  _待办(todo).md  _检索失败日志(miss log).md
docs/en/  docs/zh/   four design docs, bilingual
  architecture.md        dual-body brain / entry pyramid / five auto-loops / three rings
  card-spec.md           card spec: frontmatter / 14 card types / 10 edge types / activity axis
  retrieval-protocol.md  ≤8-read budget / question-type routing / V-jump / miss escalation
  hooks-setup.md         Claude Code integration: hooks + optional Ollama + known pitfalls
hooks/             settings.example.json (merge-ready hook snippets)
```

## Design lineage

None of this is invented from thin air. It synthesizes **A-MEM** (card = content + keywords + context + link set, evolving memory), **Zep / GraphRAG** (temporal graphs and hierarchical community summaries), **LYT / MOC** and **Evergreen notes** (mature human PKM practice), and Discourse Graphs (question cards) — hardened by hundreds of real research-workflow sessions. Design decisions are referenced as D-xx numbers throughout the docs for traceability.

## FAQ

- **Do I need Claude Code?** No. The hook layer is Claude Code-specific, but the vault + engine are plain file operations — any agent (or human) that can read files can use it; Obsidian opens the vault directly and gives you the graph view.
- **The card keywords are Chinese — can I use this in an English project?** Card *content* can be in any language. Card-type and edge-type keywords are currently Chinese enums (`概念-`/`支持::`); to localize, fork and edit the enum tables at the top of `vault_lint.py`. An English keyword set is on the v2 roadmap.
- **How does this relate to RAG?** Complementary. RAG retrieves source-text fragments; this system manages the **judgment layer** — conclusions, decisions, lessons, and their reasoned associations. Vector search is only the fallback path here, not the backbone.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=QQSSYY8818/agent-second-brain&type=Date)](https://star-history.com/#QQSSYY8818/agent-second-brain&Date)

## License

MIT. Your cards belong to you — the stance of this framework: **judgment must be made by a human (or your agent); the framework's only job is to make sure judgment is never forgotten.**
