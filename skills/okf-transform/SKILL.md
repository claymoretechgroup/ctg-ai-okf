---
name: okf-transform
description: Convert existing artifacts (design docs, specs, READMEs, code, notes, meeting/conversation summaries) into OKF concept documents, restructure existing OKF bundles (move, rename, split, merge concepts and rewrite links), and migrate v0.1 bundles to v0.2. Use whenever the user wants to "OKF-ify" something, import or ingest content into a knowledge bundle, migrate docs to OKF, upgrade a bundle to the current OKF version, or reorganize a bundle's layout. For authoring brand-new concepts use okf-create-node.
---

# OKF Transform

Three behaviors, all ending in a conformant OKF v0.2 bundle: **ingest**
(artifact → concepts), **restructure** (reshape an existing bundle), and
**migrate** (v0.1 bundle → v0.2). Working spec digest is in
`okf-create-node/SKILL.md`; the full spec is vendored in this suite at
`spec/SPEC.md`.

## Ingest: artifact → concepts

The central judgment call: a concept is a **unit of knowledge**, not a
unit of source. Don't map one file to one concept by reflex.

1. **Read the artifact and list the distinct things it knows.** A design
   doc might yield one Design concept, two Decision concepts, and a
   Reference. A schema file might yield one concept per table. A long
   README might be one concept with good structure.
2. **Decide what the concept is *about*.** Knowledge *about* an artifact
   (why it exists, how to use it, what reviewing it found) is distinct
   from the artifact itself. Usually the right move is to distill —
   summarize the durable knowledge, structure it, and cite the source —
   not to paste the artifact wholesale. Copy verbatim only when the
   artifact already *is* knowledge in prose form (a runbook, an ADR) and
   needs only frontmatter.
3. **Choose types deliberately.** Reuse type values already present in
   the bundle (`grep -rh '^type:' <bundle> | sort | uniq -c`) before
   minting new ones — consumers route on `type`, and five synonyms for
   "design note" fragment retrieval.
4. **Record provenance in frontmatter** (§5.1). Every ingested concept
   gets a `sources` entry per material it derives from — `resource`
   (URL, repo path, `/references/...` concept mirroring external
   material, or a scope descriptor), an `id`, a `title`, and
   `last_modified` / `author` when the artifact tells you. Attribute
   specific claims in the body with `[^id]` footnotes. Set
   `generated: { by: <you>, at: <now> }` — *you* produced the concept,
   now; the artifact's own date belongs on `sources[].last_modified`,
   not on `generated.at`. Do not add `verified` — ingestion is not
   verification. If the bundle carries additional provenance keys of its
   own, populate them; record what actually happened, don't infer.
5. **Cross-link on the way in.** New concepts that join an existing
   bundle should link to the concepts they relate to, and get linked
   *from* them where the relationship matters in both directions. An
   unlinked concept is invisible to graph traversal.

## Restructure: move / rename / split / merge

Moving or renaming a concept **changes its ID** (the ID is the path), so
the real work is link integrity:

1. Before moving, find inbound references — body links *and*
   path-valued frontmatter (`sources[].resource`, `computation`,
   `executor.resource`, `attester.resource`, §6.2):
   `grep -rn "old/path" <bundle> --include="*.md"`.
2. Move the file, rewrite every inbound reference to the new path
   (bundle-relative `/new/path.md` form preferred), and rewrite the
   moved document's own relative links and paths, which now resolve
   from a new directory.
3. **Split** when one document holds several independently-linkable
   units of knowledge; leave a link from each fragment to its siblings.
   **Merge** when concepts are near-duplicates fragmenting retrieval;
   keep the better-linked ID as the survivor and rewrite links to the
   absorbed one.
4. Consider leaving a breadcrumb: external consumers may hold old IDs.
   For high-traffic concepts, keep a stub at the old path whose body is
   one line linking to the new home, `type: Moved`, `status: deprecated`.

## Migrate: v0.1 bundle → v0.2

`python3 <suite>/okf.py validate <bundle>` on a v0.1 bundle stays green
(v0.2 is permissive) but reports every leftover as a warning — legacy
`timestamp`, `# Citations` sections, `okf_version: "0.1"`, `status`
values outside the spec's vocabulary. Work through them:

1. **`timestamp` → `generated: { by, at }`** (§13.1). `at` is the old
   timestamp value. `by` is the actual producer — git history
   (`git log --format='%an %ad' -- <file>`) or the bundle's own
   provenance keys tell you; people become `human:<id>`, tools
   `<tool>/<version>`. If the producer is genuinely unknowable, keep
   `timestamp` and leave `generated` absent (consumers fall back to it)
   — never fabricate an actor.
2. **`# Citations` → `sources`** (§13.1). One entry per citation with an
   `id`; convert `[1]`-style references in the body to `[^id]` footnotes
   with matching definitions; delete the section.
3. **`status` outside `draft | stable | deprecated`** (§5.4). Either map
   the producer's vocabulary onto the spec's (e.g. `proposed → draft`,
   `ratified → stable`) or move it to a producer key of its own
   (`decision_status:`) so `status` keeps its spec meaning.
4. **Timestamps without an offset** (`2026-06-01`, `2026-06-01T09:00`):
   add the offset the source actually meant (`T00:00:00Z` for a date).
5. Bump the root `index.md` to `okf_version: "0.2"`, then log the
   migration.

## Always finish the same way

```bash
python3 <suite>/okf.py index <bundle> --write
python3 <suite>/okf.py links <bundle>
python3 <suite>/okf.py validate <bundle>
```

(`<suite>` is the install root: `${CLAUDE_PLUGIN_ROOT}` for Claude plugin installs, the repo clone path for Codex.)

Broken links that existed before your change are tolerable (spec §6.1);
broken links your change *introduced* are not — fix those. Then log the
transformation in `log.md` (newest first, `## YYYY-MM-DD`):

```markdown
## 2026-07-01
* **Update**: Ingested the v2 queue design doc as [Queue Design](/designs/queue.md) + two [decisions](/decisions/).
* **Update**: Moved `notes/retry.md` → [Retry Policy](/decisions/retry-policy.md); inbound links rewritten.
* **Update**: Migrated the bundle to OKF v0.2 — `timestamp` → `generated`, citations → `sources`.
```
