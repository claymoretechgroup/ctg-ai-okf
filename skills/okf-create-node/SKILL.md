---
name: okf-create-node
description: Create Open Knowledge Format (OKF) bundles and author new concept documents (markdown + YAML frontmatter). Use whenever the user wants to start a knowledge bundle, add a concept, playbook, metric, reference, or table doc to an OKF bundle, or capture new knowledge "in OKF" — even if they just say "add this to the bundle" or "document this as a concept". Also onboards projects: initializing a bundle includes wiring the project's CLAUDE.md/AGENTS.md so future sessions are bundle-aware. For converting existing artifacts into OKF use okf-transform.
---

# OKF Create

Author new knowledge as OKF v0.2 concepts. A bundle is a directory of
markdown files; a concept is one file. The full spec is vendored in this
suite at `spec/SPEC.md` (pinned from upstream knowledge-catalog — see
`spec/NOTICE.md`). The rules below are the working digest — read the
spec only for edge cases.

## Core rules (OKF v0.2)

- Every concept file needs YAML frontmatter with a non-empty `type`.
  That is the only hard requirement (§11); everything else is soft
  guidance — but when you *use* the provenance, trust, or lifecycle
  families (§5), use them as specified, because consumers derive trust
  and staleness from them mechanically.
- `index.md` and `log.md` are reserved at every directory level — never
  use them for concepts. `index.md` carries frontmatter only at the
  bundle root (for `okf_version: "0.2"`).
- Concept ID = file path minus `.md` (`tables/users.md` → `tables/users`).
- Cross-link with normal markdown links; prefer bundle-relative form
  (`/tables/users.md`) — it survives moves of the *linking* document.
- Broken links are legal (§6.1): they mark not-yet-written knowledge.
- Every timestamp is an ISO 8601 datetime **with an explicit offset**
  (`2026-08-31T14:00:00Z`); a bare date is not a timestamp (§5).
- Actors (§7): `<producer>/<version>` for agents and tools,
  `human:<id>` for people, `process:<id>` for automation. You are an
  agent — write yourself as e.g. `claude-code/<model>` or
  `codex/<model>`, never as `human:`; consumers key trust tiers off the
  `human:` prefix.

## Workflow

### 1. Locate or initialize the bundle

If the user names a bundle directory, use it. Otherwise look for an
existing bundle (a tree of `.md` files with frontmatter, often with a
root `index.md`) before creating one. To initialize a new bundle:

```
<bundle>/
└── index.md        # frontmatter: okf_version: "0.2"
```

Organize subdirectories by whatever suits the domain (`tables/`,
`playbooks/`, `references/`, `decisions/` …) — the spec imposes nothing.
`references/` is the conventional home for mirrored external material,
run instructions, and attester code (§6.3).

**When initializing a NEW bundle, finish by wiring the project** so
every future session is bundle-aware without being told. Offer to add
this block to the project's `CLAUDE.md` (and `AGENTS.md`, if the
project keeps one for other agents), adjusting the path:

```markdown
## Knowledge base

`<bundle>/` is this repo's knowledge base — an OKF bundle (markdown +
YAML frontmatter; start at `<bundle>/index.md`). Consult it when
working here. Capture durable decisions and findings as concepts
(okf-create-node); ingest existing docs with okf-transform; after any
bundle change, validate and reindex (okf-validate).
```

If the user wants the health check enforced rather than remembered,
hand off to okf-validate's mechanical gate (pre-commit / CI).

### 2. Write the concept

Path choice is an API decision: the path *is* the concept ID other
documents will link against, so pick a stable, descriptive slug.

Template:

```markdown
---
type: <Kind of concept — e.g. Playbook, Metric, Design Decision, API Endpoint>
title: <Human-readable display name>
description: <One sentence — this feeds indexes, search snippets, previews>
resource: <Canonical URI of the underlying asset — omit for abstract concepts>
tags: [<short>, <cross-cutting>, <labels>]
generated: { by: <you, e.g. claude-code/<model>>, at: <now — date -u +%Y-%m-%dT%H:%M:%SZ> }
status: <draft while incomplete or unreviewed; omit when stable>
sources:
  - id: <short-stable-key>
    resource: <URL, /bundle/path.md, or a scope descriptor like "all PRs in repo X">
    title: <Human label>
    last_modified: <the SOURCE's own date — publication / last-true — ISO 8601>
---

<Body: favor structural markdown — headings, tables, lists, fenced code —
over prose walls. Agents and humans both retrieve better from structure.
Attribute specific claims to a source with a footnote keyed to its id:>

The sharded tables roll daily.[^short-stable-key]

[^short-stable-key]: <Human label>
```

Notes that matter:

- **Two dates, two meanings.** `generated.at` is when *this concept's
  content* last changed — the build date. The source's own date goes on
  `sources[].last_modified`. Provenance rule (from the RFC flight's F3:
  build-dated concepts made every direction hint uninformative): when
  distilling from an artifact, always carry the artifact's own date in
  `last_modified`; never let the build date stand in for it.
- **`sources` is the provenance record** (§5.1). One entry per material
  the concept derives from; `resource` is required, `id` whenever the
  body cites it. Footnote labels `[^id]` are the join key — keyed, not
  positional, so reordering never misattributes. There is no
  `# Citations` section in v0.2.
- **`verified` records what actually happened** (§5.2). Only add a
  verification event for a confirmation that took place: if the user
  reviewed and confirmed the concept in-session, add
  `verified: { by: human:<id>, at: <now> }`; record yourself as a
  verifier only after actually checking the content against its sources
  or `resource`. Absent `verified` means *unverified* — that is honest,
  not a defect. Never write `human:` for an agent check.
- **`status`** (§5.4): `draft` while incomplete or unreviewed; omit (=
  `stable`) when ready; `deprecated` when replaced but kept for links and
  history. **`stale_after`** (§5.5): set only when the knowledge has a
  known expiry (a quarter's figures, a rate limit, a config known to be
  changing) — an absolute instant, never a relative TTL.
- **Attested Computation** (§10): when the concept *is* a sanctioned
  computation whose output consumers must be able to verify (a SQL, dbt,
  or Python definition of a number), use `type: Attested Computation`
  with `runtime` (required), typed `parameters`, the computation either
  inline under `# Computation` or at a `computation:` path, and
  `executor`/`attester` resources. A Metric that *uses* the number links
  to the computation rather than embedding SQL. Read §10 before writing
  one.
- `type` values aren't registered anywhere; pick something descriptive
  and reuse the same value for the same kind of thing within a bundle —
  consumers filter and route on it.
- **Tags: consult the registry before coining.** If the bundle has a
  tag authority file (conventionally `decisions/tag-vocabulary.md` with
  an `# okf-tag-registry` block), reuse its tags; a genuinely new tag
  is added to the registry *in the same change* that first uses it,
  never silently. If there's no registry, reuse tags already present in
  the bundle (grep `tags:`) rather than inventing near-synonyms —
  uncontrolled tag vocabularies decay into one-tag-per-concept and stop
  working as routing keys. `python3 <suite>/okf.py tags <bundle>` (okf-validate; `<suite>` is the install root — `${CLAUDE_PLUGIN_ROOT}` for Claude plugin installs, the repo clone for Codex) checks
  compliance. Where registry entries carry criteria ("earns this label
  when…"), labeling is rubric application: for
  non-obvious assignments note which criterion the concept meets.
  Establishing or revising the registry itself is a governance act,
  not an authoring-time side effect.
- **Aliases: declare naming variants at write time.** If the thing this
  concept describes goes by other names (a working title, an
  abbreviation, a name another extraction used), list them in
  frontmatter `aliases: [<variant>, …]` — they join the routing surface
  for downstream retrieval and joins, labeled there as alias-mediated. Rules: a
  variant names *this exact thing* (same referent — a broader or
  narrower term is a link or a tag, never an alias), and no variant may
  duplicate another concept's alias or shadow its id. Symbol-level equivalences not
  anchored to one concept (key↔key, tag↔tag) belong in the bundle's
  alias registry (`decisions/alias-registry.md`), not frontmatter.
- **Supersession: declare replacement at write time.** If this concept
  replaces an existing one, declare it —
  `supersedes: [/path/to/old-concept.md]` (bundle-absolute paths, list
  form) — and set `status: deprecated` on the old concept in the same
  change, so v0.2 consumers see it without walking the graph. The link
  stays the walkable history; the old concept stays in place (never
  delete or stub it). Optional `slot: <name>` declares mutual
  exclusivity: no two *current* concepts may share a slot. Only declare
  a slot where exclusivity is real — most concepts accumulate and never
  conflict.
- Always write a `description`. Index generation and recall both degrade
  without it.
- Conventional body headings, when applicable: `# Schema` (columns or
  fields of an asset), `# Examples` (fenced code), `# Computation` (an
  Attested Computation's inline computation).
- Extra frontmatter keys are welcome (producers may extend freely), but
  don't invent a key for something the body can say, and don't reuse a
  spec key (`status`, `sources`, `generated`, …) with your own meaning.
- Link related concepts as you write — links to concepts that don't
  exist yet are how the bundle grows deliberately.

### 3. Update the index and log

After writing concepts, regenerate indexes with the OKF statics tool:

```bash
python3 <suite>/okf.py index <bundle> --write
```

Then add a log entry by hand — the log is curated prose, not generated.
`log.md` at the bundle root (or the affected subdirectory), newest date
first, `## YYYY-MM-DD` headings:

```markdown
## 2026-07-01
* **Creation**: Added [Freshness Playbook](/playbooks/freshness.md) covering the orders SLA alert.
```

### 4. Validate

```bash
python3 <suite>/okf.py validate <bundle>
```

Fix any violation before finishing — conformance is the cheap oracle
that keeps a bundle machine-consumable; don't leave it red. Warnings
about the families you just wrote (a timestamp without an offset, an
actor outside the convention, a footnote with no matching source id)
are cheap to fix now and expensive to find later — fix those too.
