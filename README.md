# CTG AI OKF

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
---
We chose SQLite because … Standard markdown links to
[related concepts](/decisions/related-concept.md) weave the bundle
into a navigable graph.
```

Directories group concepts by kind (`decisions/`, `findings/`,
`ideas/`, …); each directory carries an `index.md` so the bundle is
browsable; internal markdown links make it a graph. The full
specification is vendored at [spec/SPEC.md](spec/SPEC.md) (OKF v0.1).

## The skills

Three skills cover the write / restructure / verify lifecycle. After
install they trigger on natural requests — you talk about knowledge,
the skill handles the format:

| Skill | What it does | Say things like |
|---|---|---|
| **okf-create-node** | Starts new bundles and authors new concepts from scratch — correct frontmatter, the right directory, index and log kept current as part of the write. | "start a knowledge bundle", "add this decision to the bundle", "document this as a concept" |
| **okf-transform** | Ingests *existing* artifacts (design docs, specs, READMEs, meeting notes) into a bundle, and restructures bundles — move, rename, split, merge, with every internal link rewritten. | "OKF-ify this design doc", "import these notes into the bundle", "split this concept in two" |
| **okf-validate** | The health check: spec conformance, stale indexes, broken links, tag/type inventory against the bundle's registries, and the HTML graph view. Run after anything mutates a bundle. | "is the bundle healthy?", "validate and reindex", "show me the graph" |

The skills are agent-neutral markdown — Claude loads them through the
plugin; Codex reads the same files per [AGENTS.md](AGENTS.md). In a
SKILL.md, `<suite>` means the install root (`${CLAUDE_PLUGIN_ROOT}`
for Claude plugin installs, the repo clone path for Codex).

## The tools

Two zero-dependency Python 3 programs the skills run underneath —
equally usable by hand or in CI:

```bash
python3 okf.py validate <bundle>   # spec conformance (§9): parseable frontmatter,
                                   #   required fields, reserved-name rules — exit 1 on violations
python3 okf.py index <bundle>      # which index.md files are stale (--write regenerates them)
python3 okf.py links <bundle>      # broken internal links, informational — OKF §5.3 tolerates
                                   #   them as markers for not-yet-written knowledge
python3 okf.py types <bundle>      # every `type:` in use; with a taxonomy file (--taxonomy or
                                   #   the bundle's own), exit 1 on unregistered types
python3 okf.py tags <bundle>       # every tag in use; with a registry (--registry or the
                                   #   bundle's own), exit 1 on unregistered tags
python3 viz.py <bundle>            # self-contained HTML graph view of the bundle — concepts as
                                   #   nodes, links as edges (--out <path>, --name <title>)
```

`validate` is the hard gate — wire it into CI if the bundle matters.
`types` and `tags` keep vocabularies controlled so labels stay useful
as routing keys instead of decaying into one-tag-per-concept. `viz`
renders a single HTML file with no external assets — open it in any
browser.

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
`test/receipts/old/`.

## Layout

```
okf.py           the statics commands (validate/links/index/types/tags)
viz.py           the HTML graph visualizer
skills/          the three skills — agent-neutral, the ONE copy read
                 by both models
spec/            vendored OKF v0.1 specification
test/            fixture bundles + byte-parity receipts + run.py
.claude-plugin/  Claude wiring (marketplace + plugin manifest)
AGENTS.md        the Codex contract
```

## License

Apache-2.0 — see [LICENSE](LICENSE). The vendored specification under
`spec/` is also Apache-2.0, from its upstream (see
[spec/NOTICE.md](spec/NOTICE.md)).
