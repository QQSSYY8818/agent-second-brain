# Card Specification

*[中文版](../zh/card-spec.md)*

One card = one Markdown file = one indivisible unit of judgment. The file name is a stable ID — **never renamed**; forbidden characters `\/:*?"<>|` and trailing spaces.

> Note: card-type and edge-type keywords are Chinese enums in v1 (they are what the engine parses). English glosses are given below; to localize, edit the enum tables at the top of `vault_lint.py`.

## 1. Frontmatter (ten required fields)

```yaml
---
schema: 1
type: 概念            # card type, see §2
tier: T1              # T0 registry / T1 standard / T2 refined / T3 load-bearing
projects: [00]        # owning project number(s)
confidence: 已验证    # 已验证=verified / 文献=literature / 联想=speculative
status: 已审          # 草稿=draft / 已审=reviewed / 已取代=superseded (must carry a 取代者:: edge)
aliases: ["中文别名", "english alias"]   # ≥2 for T1+, include English (key to recall hit-rate)
origin: 2026-07-11    # date the knowledge was born ≤ created ≤ updated
created: 2026-07-11
updated: 2026-07-11
source: path or description of provenance
---
```

Optional fields: `used`/`last_hit` (usage counters, script-maintained), `活性` (activity: `显性`=active or `辅助 YYYY-MM-DD`=auxiliary, see architecture §4), `q_status` (question cards: open/partial/answered), `provenance` (required on concept cards: 文献共识=literature consensus / 文献+自研 / 自研数据=own data / 自研推导=own derivation).

## 2. Card types (14, file-name prefix = type)

| Prefix | Meaning | Use |
|--------|---------|-----|
| `概念-` | concept | a judged conclusion / mechanism / design (provenance required) |
| `文献-` | literature | key points and judgment of one external paper |
| `方法-` | method | a reusable procedure / pipeline / SOP digest |
| `事例-` | case | post-mortem of a finished campaign (goal / path / output / lessons) |
| `对话-` | dialogue | the decision scene of one key conversation |
| `问题-` | question | an open question (q_status tracked; answered must carry a supports edge to the answer card) |
| `知识点-` | wiki-point | encyclopedia definition (out-of-ring plane, referenced by keyword) |
| `符号-` | symbol | one formula symbol per card (definition + easily-confused neighbors) |
| `关联-` | association | carrier for speculative-only connections (confidence: 联想) |
| `清单-` | checklist | terminal resource list (local files must carry one-click file:/// links) |
| `编年-` | chronicle | the timeline ledger, one line per event ("have we done anything like this?") |
| `枢纽-` | hub | one per project: one-line positioning + status section (with last-verified date) + open questions |
| `MOC-` | map of content | theme map: conclusion digest (5-10 lines) + sectioned links |
| `登记-` | registry | T0 file registration (tens of thousands; kept out of the main retrieval entry) |

## 3. Edges (associations are first-class)

Written in the card's `## 关联` (associations) section. **Bare links are forbidden**; every edge carries a one-line reason:

```
边型:: [[target card name]] — one-line reason (why this connection exists)
```

Ten edge types: `支持`(supports) `冲突`(conflicts) `延伸`(extends) `类比`(analogy) `上位`(is-a) `用法`(uses) `用材`(uses-material) `同理`(same-principle) `出处`(provenance) `引用`(cites) — plus `取代者`(superseded-by), reserved for superseded cards.

- **Strength marks**: a reason may be prefixed `（强）`(strong)=functional dependency / same mechanism, `（弱）`(weak)=same-domain analogy / potential synergy; unmarked = neutral. Retrieval walks strong edges first.
- **The is-a axis**: instance cards point up to a family concept card; downward links are never edges — always reverse-look-up in the adjacency list. A family abstraction must be statable in one sentence; connecting for connection's sake is forbidden.
- **Strong-edge write-back**: creating a conflicts/supersedes/supports edge requires writing one line of reverse context into the target card and bumping its `updated`; weak edges don't write back.
- **Automatic edges are limited to provenance/cites** (mechanically provable); every other edge type is nomination-only — confirmed by a human (or the lead agent).

## 4. Writing discipline

- **Conclusion-first description**: the first 40 characters of the card's first narrative sentence must be self-sufficient — state *what the conclusion is* before qualifications and background. The catalog description is taken from this sentence; it determines injection and grep hit quality.
- **Plain-language formula duty**: every formula must be followed by one plain sentence ("— the equation says: ..."); bare formulas are forbidden.
- **Card-creation ritual = reverse check**: grep the catalog + scan related MOCs first, and ask "which existing card does this conflict with or duplicate?"
- **The two-question bar** (T1+): will you still use it in three months? does it still hold in another project? If not → an index line, not a card.
- **Zero-orphan rule**: every non-hub/MOC card must have at least one edge (lint L10 enforces).
- **Busy fallback**: one line in `_inbox/` (title + one sentence) is the minimum compliant action.
- Cards produced by sub-agents can only be `status: 草稿` (draft); only `已审` (reviewed) may be linked from MOC/HOME.
- External facts that can change must carry an inline "(as of YYYY-MM)".

## 5. Lint rules at a glance (L1-L15)

Frontmatter completeness (L1/L2), legal enums (L3), aliases≥2 (L4), timestamp order (L5), updated vs mtime (L6, auto-fixable with `--fix`), bare links (L7), edge types & reasons (L8/L15), provenance-path existence (L9), orphan cards (L10), sync-conflict copies (L11), superseded completeness (L12), naming (L13), length budgets (L14: MOC ≤30 links, T2 card ≤40 lines, HOME ≤100 lines).

**The maintenance triple**: after every change, run `vault_lint.py` → `vault_catalog.py` → `vault_routemap.py` (+ `vault_rings.py`) so indexes and cards never drift apart.
