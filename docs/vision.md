# vision: loretools

## long-term scope

The library operates across two coupled layers — reference and knowledge — and the long-term vision develops both in parallel. The reference layer is the foundation; the knowledge layer is what makes it intellectually productive.

### reference layer
- **semantic search** — find references by meaning, not just keywords; query the library with natural language and get ranked, contextually relevant results
- **epistemological pluralism** — first-class authority types beyond peer review: field observation, oral tradition, community archive, activist documentation, clinical case, legal record — each with its own retrieval promise and evidence standard, not mapped onto journal-article conventions
- **authority provenance chains** — trace how a claim moves from primary source through citation network; surface when a secondary citation has drifted from its origin, when authority is disputed, or when the epistemological framework of a source has been stripped in transit
- **multi-agent library coordination** — multiple agents operating on the same reference state: parallel search, conflict resolution, shared curation across a research team or organization

### knowledge layer
- **wiki as living document** — the wiki grows with the library; as references are added, the agent extends existing concept pages, revises synthesis notes, and flags new tensions — the knowledge layer is never finished, only current
- **citation graph analysis** — map relationships between references: who cites whom, influence chains, research lineages, gap detection; surface this as navigable wiki structure, not just metadata
- **cross-domain concept translation** — bridge specialized vocabularies between fields (legal, medical, academic, policy) within the knowledge layer so the same reference set generates intelligible concept pages for different audiences
- **reading list generation** — agent-curated reading paths with importance scoring, gap analysis, and progressive disclosure tuned to the human's current understanding — generated from wiki structure, not just reference metadata
- **automated recommendations** — proactive reference surfacing and wiki expansion based on the human's active research questions, writing context, or agent task
- **social annotation and shared knowledge** — structured annotations on reference objects feed the wiki; multiple stakeholders (agents, humans, teams) contribute to a shared knowledge layer across a collection — a paper is not just metadata, it is a node in a living collaborative understanding

### plugin ecosystem
- **community-contributed source adapters** — the search plugin interface is open; any community can write an adapter for their archive, database, or knowledge system and distribute it as `loretools-<name>`; no academic index has a privileged position in this architecture
- **discipline-specific plugins** — legal databases, pharmaceutical registries, indigenous knowledge archives, clinical trials, activist documentation systems — each community can integrate its sources at the same level as Crossref, without translating into academic conventions
- **composable environment profiles** — a researcher in an air-gapped institution, a team using cloud sync, and a journalist in a sandboxed agent all install the same core and the plugins their environment supports; the function interface never changes

## non-goals (ever)

- not a writing assistant or document editor
- not a general-purpose personal knowledge manager (not Obsidian, not Roam) — every knowledge object must be anchored to a reference in the library; ungrounded notes have no place here
- not a Zotero replacement for human-operated workflows — it replaces Zotero's *function*, not its interface paradigm
- not a paper hosting or publishing platform
- not a proprietary silo — the local-first default and open data formats are permanent, not a phase

## why it matters

Reference infrastructure is not neutral. Every reference manager encodes a theory of what counts as knowledge: which sources are citable, which authority types are legitimate, which retrieval promises are sufficient. Susan Star showed that classification systems — and bibliographic systems are classification systems — carry the politics of the communities that built them. The current infrastructure was built by and for Western academic publishing: DOI-backed, journal-indexed, peer-reviewed. Everything else has to translate or be excluded.

This is an epistemic asymmetry problem, not a formatting problem. A researcher drawing on field interviews, community archives, indigenous knowledge systems, or ephemeral events cannot express the epistemic warrant of those sources in a system that treats "journal article with DOI" as the default shape of knowledge. The infrastructure forces a translation that strips authority and context.

loretools is built on a different premise: a reference is a *boundary object* — it sits at the intersection of multiple communities, carries a type of authority claim, and embeds an epistemological framework. The library's job is to preserve that structure, not flatten it.

The plugin architecture is where this premise becomes structural. When search adapters are optional and community-contributed rather than built in, no epistemological source is privileged by the infrastructure itself. The current generation of reference managers bake Crossref and DOI resolution into their core — that is not a neutral technical decision. It is a choice about which knowledge sources count as fundamental. loretools makes the opposite choice: core is agnostic about where references come from. A Crossref adapter and a community archive adapter have identical architectural standing. Neither is more "real" than the other.

When this vision is realized: researchers spend their cognitive budget on ideas, not information logistics. Agents handle discovery, normalization, deduplication, and curation with zero friction. The knowledge layer turns a reference library into a living wiki — a paper is no longer just metadata, it is a node in a growing, agent-maintained understanding that researchers can navigate, challenge, and extend. Citation quality improves because agents can audit and trace authority chains through both layers: the reference tells you *what was claimed and by whom*; the wiki tells you *how that claim connects to everything else you know*.

Knowledge that was locked inside specialized domains — or excluded from dominant systems — becomes not just citable but *intelligible across contexts*, from peer-reviewed research to policy briefs to community documentation. The knowledge layer is where epistemological pluralism becomes practically useful: an indigenous oral account and a peer-reviewed study can sit in the same wiki, each encoded with its own authority type, both contributing to concept pages that no single epistemological framework could have generated alone.

The result is not just faster research — it's research infrastructure that does not require marginalized knowledge systems to disappear in order to participate, and that turns the act of building a library into the act of building understanding.

---
## current v0

Core reference layer with monolithic structure (no plugin separation yet): search, fetch, extract from PDF, CRUD on a local CSL-JSON database, file archive management, citekey generation, deduplication, and audit. Local-first, no UI, optimized for agent consumption. The knowledge layer is not yet built. The plugin architecture is not yet implemented — v0 is the working reference base that will be refactored into core + plugins.
