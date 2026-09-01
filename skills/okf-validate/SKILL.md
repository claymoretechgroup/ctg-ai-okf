---
name: okf-validate
description: Validate, index, and maintain OKF bundle statics: OKF v0.2 conformance (including the provenance, trust, lifecycle, and attested-computation families), index.md regeneration, broken-link and dangling-path reports, tag inventory/registry checks, type inventory/registry checks, and static HTML visualization. Use whenever the user asks whether an OKF bundle is conformant, navigable, indexed, or statically healthy, after any other skill has mutated a bundle, or to enforce bundle health mechanically (pre-commit hook, CI gate).
---

# OKF Validate

Keep an OKF bundle conformant and navigable. This suite covers
**statics** — what a valid bundle is: format conformance, indexes,
links, tag/type inventories, and visualization.

The deterministic statics tools live at the suite root — `<suite>` is the install root (`${CLAUDE_PLUGIN_ROOT}` for Claude plugin installs, the repo clone path for Codex):

```bash
python3 <suite>/okf.py validate <bundle>          # conformance (§11) + family rules (§5, §7, §10); exit 1 on violations
python3 <suite>/okf.py links    <bundle>          # broken body links + dangling path-valued fields; always exit 0
python3 <suite>/okf.py index    <bundle>          # dry-run: which index.md files are stale
python3 <suite>/okf.py index    <bundle> --write  # regenerate them
python3 <suite>/okf.py tags     <bundle>          # tag inventory + registry check; exit 1 on unregistered tags
python3 <suite>/okf.py tags     <bundle> --registry <file>
python3 <suite>/okf.py types    <bundle>          # type inventory + registry check; exit 1 on unregistered types
python3 <suite>/okf.py types    <bundle> --taxonomy <file>
python3 <suite>/viz.py <bundle> [--out <path>] [--name <title>]
```

The full spec is vendored at `spec/SPEC.md`.

## Interpreting Results

**Violations are hard failures.** Bundle conformance (§11) is:
parseable frontmatter on every concept, non-empty `type`, and reserved
files (`index.md`, `log.md`) structurally correct. On top of that, a
frontmatter family that is *present* must carry its REQUIRED fields:
`generated.by`, `verified[].by`, `sources[].resource`, and `runtime` on
an `Attested Computation` — and be the right shape (a mapping, a list of
mappings). Fix violations before finishing; a bundle that fails these
is not reliably machine-consumable.

**Warnings are soft but useful.** A missing `description` weakens
indexes and previews. The family warnings are the ones consumers trip
over later: a timestamp without an explicit offset, an actor outside
the `<producer>/<version>` / `human:<id>` / `process:<id>` convention,
a `status` outside `draft | stable | deprecated`, a footnote with no
matching `sources[].id`, a duplicate source id, a `usage_count` with no
`usage_window`, an Attested Computation with no computation. Fix them
when the concept is in front of you.

**v0.1 leftovers are warnings too** — legacy `timestamp`, `# Citations`
sections, `okf_version: "0.1"`. They mean the bundle needs the
migration in okf-transform, not a quick edit.

**Broken links are legal** (§6.1). Each one is either a typo/stale path
or a deliberate marker for not-yet-written knowledge:

- Typo or stale path: fix the link.
- Genuine gap: leave it, or create a stub concept if the gap is now
  actionable.

`links` also reports path-valued frontmatter that points nowhere
(`computation`, `executor.resource`, `attester.resource`, and the
explicit-path forms of `resource` / `sources[].resource`, §6.2). Those
are usually mistakes, not markers — an attester that doesn't exist
can't attest anything.

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
filters. v0.2 families show as chips (status, trust tier, stale) and a
provenance block (generated / verified / stale_after / sources);
staleness is computed when the page is opened; `sources[].resource`
pointing at another concept draws a dashed derivation edge. Regenerate
it whenever the bundle changes if the bundle keeps the visualization
artifact.

## Health-Check Routine

When asked for a statics audit, run and report in this order:

```bash
python3 <suite>/okf.py validate <bundle>
python3 <suite>/okf.py links <bundle>
python3 <suite>/okf.py index <bundle>
python3 <suite>/okf.py types <bundle>
python3 <suite>/okf.py tags <bundle>
```

## Mechanical Gate (on request)

When the user wants bundle health enforced rather than remembered
("gate the bundle", "check it in CI", "add a pre-commit hook"), wire
`validate` in — it is deterministic, zero-dependency, and exits 1 on
violations, so it works anywhere a shell does.

Git pre-commit (`.git/hooks/pre-commit`, `chmod +x`):

```bash
#!/bin/sh
python3 <suite>/okf.py validate <bundle> || exit 1
```

CI: add `python3 <suite>/okf.py validate <bundle>` as a step (a
checkout of this suite's repo is enough — there are no dependencies
to install). Use the repo-clone form for `<suite>` in hooks and CI —
`${CLAUDE_PLUGIN_ROOT}` only exists inside agent sessions.

Recall quality, governance, identity, currentness, coverage, memory
behavior, and running or attesting computations are out of this
suite's scope.
