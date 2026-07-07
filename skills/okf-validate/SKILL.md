---
name: okf-validate
description: Validate, index, and maintain OKF bundle statics: OKF v0.1 conformance, index.md regeneration, broken-link reports, tag inventory/registry checks, type inventory/registry checks, and static HTML visualization. Use whenever the user asks whether an OKF bundle is conformant, navigable, indexed, or statically healthy. For recall, governance, frontier queues, alias lifecycle, supersession/current checks, routing lint, audit, memory, or graph construction, use ctg-ai-goe.
---

# OKF Validate

Keep an OKF bundle conformant and navigable. OKF owns **statics**:
what a valid bundle is. GoE owns **dynamics**: construction, recall,
trust, identity lifecycle, supersession/current, frontier queues, and
memory protocols.

The deterministic statics tools live at the repo root:

```bash
python3 okf.py validate <bundle>          # conformance (§9); exit 1 on violations
python3 okf.py links    <bundle>          # broken internal links; always exit 0
python3 okf.py index    <bundle>          # dry-run: which index.md files are stale
python3 okf.py index    <bundle> --write  # regenerate them
python3 okf.py tags     <bundle>          # tag inventory + registry check; exit 1 on unregistered tags
python3 okf.py tags     <bundle> --registry <file>
python3 okf.py types    <bundle>          # type inventory + registry check; exit 1 on unregistered types
python3 okf.py types    <bundle> --taxonomy <file>
python3 viz.py <bundle> [--out <path>] [--name <title>]
```

The full spec is vendored at `spec/SPEC.md`. The statics/dynamics
boundary is: **OKF defines statics; GoE is dynamics.**

## What Moved To GoE

These are intentionally not in this skill or repo:

- recall/rank, demand logging, and evidence-weighted retrieval
- govern/trust posture and ratified-authority build gates
- frontier and queues
- alias registry guards and alias proposal lifecycle
- current/supersession alignment checks and conflict candidates
- routing-surface lint
- corpus audit, local graph extraction, memory, onboarding, and graph
  construction

Use `ctg-ai-goe` for those commands and skills:
`okf-audit`, `okf-build-graph`, `okf-lexicon`, `okf-memory`, and
`okf-onboard`.

## Interpreting Results

**Violations are hard failures.** The statics conformance rules are:
parseable frontmatter on every concept, non-empty `type`, and reserved
files (`index.md`, `log.md`) structurally correct. Fix violations before
finishing; a bundle that fails these is not reliably machine-consumable.

**Warnings are soft but useful.** A missing `description` does not break
the format, but it weakens indexes, previews, and routing surfaces.

**Broken links are legal** (§5.3). Each one is either a typo/stale path
or a deliberate marker for not-yet-written knowledge:

- Typo or stale path: fix the link.
- Genuine gap: leave it, or create a stub concept if the gap is now
  actionable.

Never “fix” a broken link by deleting it just to make the report quiet.

**Index regeneration** is mechanical. It lists concepts with titles and
descriptions, and preserves root `index.md` frontmatter
(`okf_version`). If a directory’s index is hand-curated with thematic
sections, update it by hand instead of overwriting it.

**Tag and type sweeps are inventory plus optional registry checks.**
When a registry/taxonomy authority exists, unregistered values are hard
failures. Near-duplicate tags, unused registry entries, and misplaced
typed files are review signals, not automatic edits.

`viz.py` writes `<bundle>/viz.html` by default: a self-contained graph
view colored by `type`, with detail panel, backlinks, search, and type
filters. Regenerate it whenever the bundle changes if the bundle keeps
the visualization artifact.

## Health-Check Routine

When asked for a statics audit, run and report in this order:

```bash
python3 okf.py validate <bundle>
python3 okf.py links <bundle>
python3 okf.py index <bundle>
python3 okf.py types <bundle>
python3 okf.py tags <bundle>
```

If the user also asks about recall quality, governance, identity,
currentness, coverage, or memory behavior, hand off to `ctg-ai-goe`.
