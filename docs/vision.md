# vision: scholartools

## long-term scope

- **semantic search** — find references by meaning, not just keywords; query the library with natural language and get ranked, contextually relevant results
- **citation graph analysis** — map relationships between references: who cites whom, influence chains, research lineages, gap detection
- **social annotation** — attach structured, shareable annotations to reference objects; enable conversation layers on top of the library that multiple stakeholders (agents, humans, teams) can read and contribute to
- **multi-agent library coordination** — multiple agents operating on the same reference state: parallel search, conflict resolution, shared curation across a research team or organization
- **cross-domain translation** — bridge specialized vocabularies between fields (legal, medical, academic, policy) so the same reference set can be surfaced meaningfully for different audiences and use cases
- **reading list generation** — agent-curated reading paths with importance scoring, gap analysis, and progressive disclosure tuned to the human's current understanding
- **automated recommendations** — proactive reference surfacing based on the human's active research questions, writing context, or agent task

## non-goals (ever)

- not a writing assistant or document editor
- not a note-taking app — annotations live on reference objects, not as a general knowledge base
- not a Zotero replacement for human-operated workflows — it replaces Zotero's *function*, not its interface paradigm
- not a paper hosting or publishing platform
- not a proprietary silo — the local-first default and open data formats are permanent, not a phase

## why it matters

The boundary between what an agent can do autonomously and what requires human judgment is not fixed — it moves as tools, models, and trust evolve. scholartools is infrastructure for that moving boundary: it handles the deterministic, high-reliability layer of reference work so that both agents and humans can operate at the level where they have the most impact.

When this vision is realized: researchers spend their cognitive budget on ideas, not information logistics. Agents handle discovery, normalization, deduplication, and curation with zero friction. Social annotation turns isolated reference databases into shared epistemic objects — a paper is no longer just metadata, it's a node in a living conversation between humans and agents across disciplines. Citation quality improves because agents can audit and trace influence chains. Knowledge that was locked inside specialized domains becomes navigable across contexts, from peer-reviewed research to policy briefs to everyday language.

The result is not just faster research — it's a broader and more diverse participation in knowledge production.

---
## current v0

Core reference management as atomic Python functions: search, fetch, extract from PDF, CRUD on a local CSL-JSON database, file archive management, citekey generation, deduplication, and audit. Local-first, no UI, optimized for agent consumption.
