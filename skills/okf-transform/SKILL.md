---
name: okf-transform
description: Convert existing artifacts (design docs, specs, READMEs, code, notes, meeting/conversation summaries) into OKF concept documents, and restructure existing OKF bundles (move, rename, split, merge concepts and rewrite links). Use whenever the user wants to "OKF-ify" something, import or ingest content into a knowledge bundle, migrate docs to OKF, or reorganize a bundle's layout. For authoring brand-new concepts use okf-create-node; for memory and graph construction use ctg-ai-goe.
---

# OKF Transform

Two behaviors, both ending in a conformant bundle: **ingest** (artifact →
concepts) and **restructure** (reshape an existing bundle). Working spec
digest is in `okf-create-node/SKILL.md`; the full spec is vendored in this
suite at `spec/SPEC.md`.

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
4. **Record provenance.** Cite the source under `# Citations` (URL,
   repo path, or a `references/` concept mirroring external material).
   If the bundle uses provenance frontmatter keys (`produced_by`,
   `derived_from`), populate them — record what actually happened, don't
   infer.
5. **Cross-link on the way in.** New concepts that join an existing
   bundle should link to the concepts they relate to, and get linked
   *from* them where the relationship matters in both directions. An
   unlinked concept is invisible to graph traversal.

## Restructure: move / rename / split / merge

Moving or renaming a concept **changes its ID** (the ID is the path), so
the real work is link integrity:

1. Before moving, find inbound links:
   `grep -rn "old/path.md" <bundle> --include="*.md"`.
2. Move the file, rewrite every inbound link to the new path
   (bundle-relative `/new/path.md` form preferred), and rewrite the
   moved document's own relative links, which now resolve from a new
   directory.
3. **Split** when one document holds several independently-linkable
   units of knowledge; leave a link from each fragment to its siblings.
   **Merge** when concepts are near-duplicates fragmenting retrieval;
   keep the better-linked ID as the survivor and rewrite links to the
   absorbed one.
4. Consider leaving a breadcrumb: external consumers may hold old IDs.
   For high-traffic concepts, keep a stub at the old path whose body is
   one line linking to the new home, `type: Moved`.

## Always finish the same way

```bash
python3 okf.py index <bundle> --write
python3 okf.py links <bundle>
python3 okf.py validate <bundle>
```

Broken links that existed before your change are tolerable (spec §5.3);
broken links your change *introduced* are not — fix those. Then log the
transformation in `log.md` (newest first, `## YYYY-MM-DD`):

```markdown
## 2026-07-01
* **Update**: Ingested the v2 queue design doc as [Queue Design](/designs/queue.md) + two [decisions](/decisions/).
* **Update**: Moved `notes/retry.md` → [Retry Policy](/decisions/retry-policy.md); inbound links rewritten.
```
