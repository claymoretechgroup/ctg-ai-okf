---
name: okf-create-node
description: Create Open Knowledge Format (OKF) bundles and author new concept documents (markdown + YAML frontmatter). Use whenever the user wants to start a knowledge bundle, add a concept, playbook, metric, reference, or table doc to an OKF bundle, or capture new knowledge "in OKF" — even if they just say "add this to the bundle" or "document this as a concept". For converting existing artifacts into OKF use okf-transform; for memory and graph construction use ctg-ai-goe.
---

# OKF Create

Author new knowledge as OKF v0.1 concepts. A bundle is a directory of
markdown files; a concept is one file. The full spec is vendored in this
suite at `spec/SPEC.md` (pinned from upstream knowledge-catalog — see
`spec/NOTICE.md`). The rules below are the working digest — read the
spec only for edge cases.

## Core rules (OKF v0.1)

- Every concept file needs YAML frontmatter with a non-empty `type`.
  That is the only hard requirement; everything else is soft guidance.
- `index.md` and `log.md` are reserved at every directory level — never
  use them for concepts. `index.md` carries frontmatter only at the
  bundle root (for `okf_version: "0.1"`).
- Concept ID = file path minus `.md` (`tables/users.md` → `tables/users`).
- Cross-link with normal markdown links; prefer bundle-relative form
  (`/tables/users.md`) — it survives moves of the *linking* document.
- Broken links are legal: they mark not-yet-written knowledge.

## Workflow

### 1. Locate or initialize the bundle

If the user names a bundle directory, use it. Otherwise look for an
existing bundle (a tree of `.md` files with frontmatter, often with a
root `index.md`) before creating one. To initialize a new bundle:

```
<bundle>/
└── index.md        # frontmatter: okf_version: "0.1"
```

Organize subdirectories by whatever suits the domain (`tables/`,
`playbooks/`, `references/`, `decisions/` …) — the spec imposes nothing.

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
timestamp: <ISO 8601 — the SOURCE's date (publication/creation/last-true),
  not the build date. Provenance rule (Phase 5b, from the RFC flight's F3:
  build-dated concepts made every direction hint uninformative): when
  distilling from an artifact, carry the artifact's own date; fall back to
  `date -u +%Y-%m-%dT%H:%M:%SZ` only for knowledge born in this session>
---

<Body: favor structural markdown — headings, tables, lists, fenced code —
over prose walls. Agents and humans both retrieve better from structure.>

# Citations

[1] [Source backing a claim above](https://…)
```

Notes that matter:

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
  working as routing keys. `python3 okf.py tags <bundle>` (okf-validate) checks
  compliance. Where registry entries carry criteria ("earns this label
  when…", per ctg-ai-goe's okf-lexicon), labeling is rubric application: for
  non-obvious assignments note which criterion the concept meets.
  Establishing or revising the registry itself is ctg-ai-goe's okf-lexicon job,
  not an authoring-time side effect.
- **Aliases: declare naming variants at write time.** If the thing this
  concept describes goes by other names (a working title, an
  abbreviation, a name another extraction used), list them in
  frontmatter `aliases: [<variant>, …]` — they join the routing surface
  for GoE recall and audit joins, labeled there as alias-mediated. Rules: a
  variant names *this exact thing* (same referent — a broader or
  narrower term is a link or a tag, never an alias), and no variant may
  duplicate another concept's alias or shadow its id. Symbol-level equivalences not
  anchored to one concept (key↔key, tag↔tag) belong in the bundle's
  alias registry (`decisions/alias-registry.md`), not frontmatter.
- **Supersession: declare replacement at write time.** If this concept
  replaces an existing one, declare it —
  `supersedes: [/path/to/old-concept.md]` (bundle-absolute paths, list
  form). "Current" is derived from these links, never a status field;
  GoE recall is current-only by default, and the old concept stays in
  place as walkable history (never delete or stub it). Optional
  `slot: <name>` declares mutual exclusivity: no two *current*
  concepts may share a slot. ctg-ai-goe owns current/supersession validation. Only
  declare a slot where exclusivity is real — most concepts accumulate
  and never conflict.
- Always write a `description`. Index generation and recall both degrade
  without it.
- Conventional body headings, when applicable: `# Schema` (columns or
  fields of an asset), `# Examples` (fenced code), `# Citations`
  (numbered external sources, at the bottom).
- Extra frontmatter keys are welcome (producers may extend freely), but
  don't invent a key for something the body can say.
- Link related concepts as you write — links to concepts that don't
  exist yet are how the bundle grows deliberately.

### 3. Update the index and log

After writing concepts, regenerate indexes with the OKF statics tool:

```bash
python3 okf.py index <bundle> --write
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
python3 okf.py validate <bundle>
```

Fix any violation before finishing — conformance is the cheap oracle
that keeps a bundle machine-consumable; don't leave it red.
