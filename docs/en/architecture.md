# Architecture

*[中文版](../zh/architecture.md)*

## 0. In one sentence

The second brain is **persistence for the judgment layer**: conclusions, decisions, and lessons an agent produces at work are frozen into a card network; layered entry points guarantee "any knowledge reachable in ≤8 reads"; automatic loops make the network evolve with use.

## 1. The dual-body brain

| Body | Content | Role |
|---|---|---|
| **Distilled body** (this repo's `vault/`) | hundreds of true cards + indexes | Judgment knowledge: conclusions / edges / reasons / decision threads. Small and entirely correct — every word has been judged |
| **Full-text body** (optional extension) | per-project full-text mirrors + mechanical links | Unlimited storage: rebuildable from scratch on error, never pollutes the original project files |

The distilled body always stays "one screen away" via routing; the full-text body scales out per project and is machine-generated. v1 of this repo ships the distilled-body framework only; the full-text builders belong to the literature/project pipeline, planned for v2.

## 2. No barriers: the entry pyramid

From "always in context" to "the outside world", retrieval radius widens layer by layer, each with a hard budget:

```
Hot core (read at session start, one screen: hand-pinned constants + top-20 knowledge atoms by degree)
 └─ Route map (hop 0, one screen: per project — positioning + keywords + top-5 load-bearing cards, ranked by degree+3×used)
     └─ Question-type routing table (pick the entry by the shape of the question)
         └─ Hub status section / MOC conclusion digest (hop 1, ≤10 lines each)
             └─ Cards (hop 2+, follow edges, ≤2 cards per hop)
                 └─ V-jump (is-a axis, lateral discovery across projects)
                     └─ Index layer (catalog / adjacency / vectors — one grep or one embedding)
                         └─ External search (miss escalation: find outside → MUST write back as a card)
```

**≤8 file reads total, hard cap** — hitting the cap without an answer = routing failure, logged to the miss log (a miss is itself a signal for improving the network).

## 3. Unlimited evolution: five automatic loops

1. **Intake loop**: something new appears → `brain_intake.py` → the mechanical layer drafts a card skeleton + candidate edges (with evidence terms) → the judgment layer confirms. One run, one confirmation, minutes.
2. **Miss loop**: retrieval bottoms out → verify externally → create a card → **it must be wired into the descent chain** (edges to the nearest cards touched on the way down, with a reason explaining why the answer wasn't there). Every failure grows new tissue.
3. **Weighting loop (Hebbian)**: real usage → `vault_touch.py` used+1 → route map re-ranks by degree+3×used → frequently-used knowledge floats to hop 0. The harvest hook does the bookkeeping automatically.
4. **Challenge loop**: monthly adversarial questioning of the highest-load cards (do these two contradict? does the data really support this?) → conflict edges / question cards / demotion proposals. Anti-ossification.
5. **Patrol loop**: `vault_patrol.py` (monthly) + `brain_audit.py` (network health) → promotion / demotion / edge-filling proposals for human triage.

## 4. The three-ring attention view (a core token-economy mechanism)

Cards have three activity states: **mainline-active** (currently being worked: project progress / open questions / latest content — frontmatter `活性: 显性`), **auxiliary-active** (process records of a live topic — `活性: 辅助 YYYY-MM-DD`, **auto-expires to latent after 7 days**), and **latent** (default, no field).

From these, `vault_rings.py` computes three rings (a computed view, not a static label):

- **Ring 0**: active cards = the entry point for project work;
- **Ring 1**: latent cards directly connected to ring 0 = the support knowledge of current work, one hop away;
- **Ring 2**: everything else = the sediment layer (closed topics + deep knowledge); its entries are theme MOCs / the chronicle / the catalog — *not* radiated from active cards.

**Remove one active mark and its whole support net silently sinks into the knowledge base — zero moving of files.** Project-work retrieval looks only at ring 0 → ring 1; historical/knowledge questions go straight to ring-2 entries. Attention and tokens are spent only where they should be.

There is also an **out-of-ring knowledge plane**: `知识点-` (wiki-point) cards form an encyclopedia layer that does not participate in ring computation; in-ring cards link to them by keyword, the way wiki links work.

## 5. Measuring network health

`brain_audit.py` runs ten mechanical checks: alias ambiguity / supports-conflicts pairs / is-a cycles / hierarchy inversions / tier-degree mismatch (high tier low degree, low tier high degree → promotion by backlinks) / star cards (connected only to hubs = not in the real network) / weak-reason edges / digest compliance / question-card status consistency / distribution stats. A healthy network: **zero contradictions, zero is-a cycles, zero inversions, zero orphans**.

## 6. The never-delete principle

Insufficient value = demotion (lower tier or reduced to an index line); outdated conclusion = `status: 已取代` (superseded) + a superseded-by edge to the new card; physical deletion only ever happens in `_回收站/` (recycle) with human approval. Historical judgment is an asset: knowing *why you were wrong then* is worth as much as knowing *what is right now*.

## 7. Design lineage

A-MEM (card = content + keywords + context + link set, evolving memory), Zep temporal graphs (the "supersede" mechanism is isomorphic), GraphRAG (hierarchical community summaries ↔ MOC digest sections), LYT-MOC / Evergreen notes (human PKM practice), Discourse Graph (question cards). D-xx numbers throughout are internal design-decision IDs, kept for traceability.
