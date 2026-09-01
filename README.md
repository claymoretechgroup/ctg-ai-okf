# ctg-ai-okf

Open Knowledge Format tooling for LLM coding agents (Claude and
Codex): everything an agent needs to create, transform, validate,
index, and visualize OKF knowledge bundles — plain markdown + YAML
frontmatter, zero dependencies, fully standalone.

**Why**: agents forget everything between sessions, and project
knowledge scattered across READMEs, notes, and chat logs is neither
navigable nor checkable. An OKF bundle is a knowledge base that lives
in your repo as ordinary files — diffable, greppable, reviewable in a
PR — with enough structure that tools can verify its health instead
of taking it on faith.

## What is an OKF bundle?

A **bundle** is a directory of markdown files. Each file is one
**concept** — one idea, decision, finding, playbook, or reference —
with YAML frontmatter carrying its metadata:

```markdown
---
title: Use SQLite for the job queue
type: Decision
tags: [architecture, persistence]
description: Why the job queue is SQLite rather than Redis.
generated: { by: claude-code/claude-fable-5, at: 2026-08-31T14:00:00Z }
sources:
  - id: bench
    resource: /findings/queue-benchmark.md
    title: Queue benchmark
---
We chose SQLite because it won the benchmark.[^bench] Standard
markdown links to [related concepts](/decisions/related-concept.md)
weave the bundle into a navigable graph.

[^bench]: Queue benchmark
```

Directories group concepts by kind (`decisions/`, `findings/`,
`ideas/`, …); each directory carries an `index.md` so the bundle is
browsable; internal markdown links make it a graph. Optional
frontmatter families make an agent-maintained bundle *trustable*:
`sources` (provenance, with `[^id]` footnotes attributing claims),
`generated` / `verified` (who wrote it, who confirmed it — trust tiers
derive from the `human:` prefix), `status` / `stale_after` (lifecycle),
and `Attested Computation` concepts carrying a sanctioned way to
compute a number. The full specification is vendored at
[spec/SPEC.md](spec/SPEC.md) (OKF v0.2).

## Install

**Claude Code** — the repo is its own marketplace; the plugin ships
the three skills (loaded from `skills/`, see
`.claude-plugin/plugin.json`) plus the tools:

```
/plugin marketplace add claymoretechgroup/ctg-ai-okf
/plugin install okf
```

Or from a local clone (equivalent CLI form):

```bash
claude plugin marketplace add <path>/ctg-ai-okf
claude plugin install okf@ctg-ai-okf --scope user
```

The plugin installs the whole repo; `<suite>` resolves to
`${CLAUDE_PLUGIN_ROOT}` (the installed repo root), so skills reach
`<suite>/okf.py` and `<suite>/viz.py` with no further setup.
Installing by copying skill dirs into `~/.claude/skills/` is NOT
supported — the skills need the tools shipped alongside them.

To update after the repo changes: `claude plugin marketplace update
ctg-ai-okf` (local marketplaces also need a `git pull` in the clone
first).

**Codex** — clone the repo and follow [AGENTS.md](AGENTS.md): skills
are plain markdown instructions, tools run by path from the clone
(`<clone>/okf.py`).

**Requirements**: Python ≥ 3.9; zero dependencies.

## Onboarding a project

Install once (above), then per project it's one conversation:

- *"Start a knowledge bundle in `knowledge/`"* — okf-create-node
  initializes the layout **and wires the project**: it writes a
  knowledge-base block into the project's `CLAUDE.md`/`AGENTS.md` so
  every future session finds the bundle without being told. (If the
  knowledge already exists as prose — NOTES.md, docs/ — say *"ingest
  it into a bundle"* and okf-transform does the conversion.)
- *"Gate the bundle"* — okf-validate installs the mechanical health
  check where you want it: a git pre-commit hook or a CI step running
  `okf.py validate` (deterministic, zero-dependency, exit 1 on
  violations). Health becomes enforced, not remembered.

After that, sessions in the project just use it: durable decisions
get captured as concepts, imports go through okf-transform, and
validation runs after changes — per the wired-in protocol block.

## Tests

```bash
python3 test/run.py
```

The suite drives the Python tools natively and byte-compares their
outputs against the individually ledgered receipts in
`test/receipts/old/`. After an intentional output change,
`python3 test/run.py --accept` rewrites the receipts from current
output — review the result with `git diff` before committing.

## Skills

Three skills cover the write / restructure / verify lifecycle. After
install they trigger on natural requests — you talk about knowledge,
the skill handles the format:

| Skill | What it does | Say things like |
|---|---|---|
| **okf-create-node** | Starts new bundles and authors new concepts from scratch — correct frontmatter, the right directory, index and log kept current as part of the write. Initializing a bundle includes wiring the project's `CLAUDE.md`/`AGENTS.md`. | "start a knowledge bundle", "add this decision to the bundle", "document this as a concept" |
| **okf-transform** | Ingests *existing* artifacts (design docs, specs, READMEs, meeting notes) into a bundle, restructures bundles — move, rename, split, merge, with every internal link rewritten — and migrates v0.1 bundles to v0.2. | "OKF-ify this design doc", "import these notes into the bundle", "split this concept in two", "upgrade the bundle to v0.2" |
| **okf-validate** | The health check: spec conformance including the v0.2 families, stale indexes, broken links and dangling paths, tag/type inventory against the bundle's registries, and the HTML graph view. Run after anything mutates a bundle; installs the pre-commit/CI gate on request. | "is the bundle healthy?", "validate and reindex", "gate the bundle", "show me the graph" |

The skills are agent-neutral markdown — Claude loads them through the
plugin; Codex reads the same files per [AGENTS.md](AGENTS.md). In a
SKILL.md, `<suite>` means the install root (`${CLAUDE_PLUGIN_ROOT}`
for Claude plugin installs, the repo clone path for Codex).

## Tools

Two zero-dependency Python 3 programs the skills run underneath —
equally usable by hand or in CI:

| Command | What it does | Why / when |
|---|---|---|
| `python3 okf.py validate <bundle>` | Spec conformance (§11): parseable frontmatter, non-empty `type`, reserved-name rules — plus the family rules when a family is present (§5, §7, §10): `generated.by`, `verified[].by`, `sources[].resource`, `runtime` on an Attested Computation. **Exit 1 on violations.** Timestamps without an offset, actors outside the convention, non-spec `status`, orphan footnotes, and v0.1 leftovers (`timestamp`, `# Citations`) are warnings. | The hard gate — wire it into CI or a pre-commit hook if the bundle matters. |
| `python3 okf.py index <bundle> [--write]` | Reports stale `index.md` files; `--write` regenerates them. | Run after adding or moving concepts so the bundle stays browsable. |
| `python3 okf.py links <bundle>` | Lists broken internal links and dangling path-valued fields (`computation`, `executor.resource`, `attester.resource`, explicit-path `sources[].resource`). Informational, always exit 0. | OKF §6.1 tolerates broken links as markers for not-yet-written knowledge — review, don't auto-fix. |
| `python3 okf.py types <bundle> [--taxonomy <file>]` | Inventories every `type:` in use; with a taxonomy (given or the bundle's own), exit 1 on unregistered types. | Keeps the type vocabulary controlled so consumers can filter and route on it. |
| `python3 okf.py tags <bundle> [--registry <file>]` | Inventories every tag in use; with a registry (given or the bundle's own), exit 1 on unregistered tags. | Keeps labels useful as routing keys instead of decaying into one-tag-per-concept. |
| `python3 viz.py <bundle> [--out <path>] [--name <title>]` | Renders the bundle as an interactive graph — concepts as nodes, links as edges, source derivations as dashed edges; status / trust-tier / stale chips and a provenance block per concept. | Single self-contained HTML file, no external assets — open it in any browser. |

## Layout

```
okf.py           the statics commands (validate/links/index/types/tags)
viz.py           the HTML graph visualizer
skills/          the three skills — agent-neutral, the ONE copy read
                 by both models
spec/            vendored OKF v0.2 specification
test/            fixture bundles + byte-parity receipts + run.py
.claude-plugin/  Claude wiring (marketplace + plugin manifest)
AGENTS.md        the Codex contract
```

## Upgrading from v0.1

Release `v0.1.0` of this repo targets OKF v0.1; `v0.2.0` and later
target OKF v0.2. The tools stay permissive: a v0.1 bundle still
validates green, with its leftovers reported as warnings (legacy
`timestamp`, `# Citations`, `okf_version: "0.1"`). To bring a bundle
forward, ask okf-transform to *"upgrade the bundle to v0.2"* — it maps
`timestamp` → `generated`, citations → `sources` + footnotes, and bumps
`okf_version`. The two spec-level breaking changes and the additive
families are summarized in [spec/SPEC.md §13](spec/SPEC.md).

## License

Apache-2.0 — see [LICENSE](LICENSE). The vendored specification under
`spec/` is also Apache-2.0, from its upstream (see
[spec/NOTICE.md](spec/NOTICE.md)).
