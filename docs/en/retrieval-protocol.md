# Retrieval Protocol (≤8 reads, hard cap)

*[中文版](../zh/retrieval-protocol.md)*

The first principle of retrieval: **not "can it be found" but "found with the fewest tokens"**. A full-library scan always finds it — it's just the most expensive path. This protocol gives every layer a hard budget.

## 0. The descent backbone (keyword → brain)

| Hop | Action | Budget |
|----|------|------|
| Hop 0 | read/grep `_索引/_路由地图.md` (route map: per project — positioning + keywords + top-5 load-bearing cards, ranked by degree+3×used) → pick the strongest project(s) | ≤40 lines |
| Hop 1 | read that project's hub status section + MOC conclusion digest (never the full text) | ≤10 lines each |
| Hop 2+ | follow edges: strong-marked and high-used edges first; weak edges only when strong ones miss | ≤2 cards per hop, up to 4-5 hops |
| Total | **≤8 file reads, iron cap** | cap hit = routing failure → log the miss, fall back to grepping the catalog |

## 1. The V-jump (lateral discovery across projects)

Whenever a hop lands on an instance card, you may climb its is-a edge to the family concept card → reverse-look-up the family's other instances in the adjacency list → descend into a *different* project where the association is stronger. The climb and the descent each count as one read, still within the 8-read cap. **When the current project isn't yielding, reach for the V-jump before digging deeper in-project** — this is mechanized association.

## 2. Question-type routing table (pick the entry by the shape of the question)

| The question looks like | First entry |
|---|---|
| latest status/progress of X | hub-X status section |
| why was it designed this way / what detours / what was rejected | MOC-X decision thread + case cards |
| need a specific number/formula/conclusion | grep the catalog → concept cards |
| have we done anything like this | chronicle layer → case cards |
| what's still unsolved | question cards (q_status=open) + hub open-questions section |
| what does this term mean | wiki-point cards (out-of-ring plane) |

## 3. Four retrieval radii (cheap → expensive)

1. **L0 injection** (free): `brain_inject.py` already put the top-4 relevant card descriptions into context — look at the injected block first.
2. **L1 grep the catalog**: `_索引/_卡片总目录.jsonl` (name/aliases/description, one-shot location). On hit, read the card directly.
3. **L2 adjacency list**: reverse traversal and multi-hop queries always read `_索引/_邻接表.jsonl` — never grep card-by-card.
4. **L3 semantic fallback**: when catalog and adjacency both miss, `python engine/vault_semantic_search.py "question"` (needs Ollama+bge-m3).
5. **L4 external search** (most expensive, the miss escalation): web/literature verification (with URLs) → **must be written back as a card** (confidence=literature or speculative; changeable external facts carry "(as of YYYY-MM)") → **the new card must be wired into the descent chain**: edges to the nearest cards touched on the way down, the reason explaining why the answer wasn't there. Finding without carding = wasted; carding without wiring = the island comes back.

## 4. Miss discipline

- No answer found → append one line to `_检索失败日志.md` (date / question / what was missing). The miss log feeds the monthly patrol — repeatedly-missed topics are exactly the cards you should create.
- Hitting a superseded card → you must also return its superseded-by target, and any citation of the old conclusion must state "overturned by X".

## 5. Post-use bookkeeping (closing the Hebbian loop)

At the end of a task, run `python engine/vault_touch.py card1 card2 ...` on the cards actually used (or let the harvest hook do it automatically) — used+1 makes the card float higher next time. **A missed entry is a hole in the weighting loop.**
