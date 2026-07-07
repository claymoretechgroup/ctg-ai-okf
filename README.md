# CTG AI OKF

Generic Open Knowledge Format statics for Claude and Codex.

OKF defines **statics**: what a valid knowledge bundle is. GoE is
**dynamics**: construction, learning, trust, retrieval, alias lifecycle,
frontier queues, currentness, audit, and memory. Dependency direction:
GoE depends on OKF tooling; OKF does not depend on GoE.

## Contents

- `okf.py` — zero-dependency Python 3 statics commands:
  `validate`, `links`, `index`, `types`, and `tags`.
- `viz.py` — zero-dependency Python 3 HTML graph visualizer.
- `skills/` — agent-neutral statics skills, the ONE copy read by both
  models: `okf-create-node`, `okf-transform`, `okf-validate`. In a
  SKILL.md, `<suite>` means the install root (`${CLAUDE_PLUGIN_ROOT}`
  for Claude plugin installs, the repo clone path for Codex).
- `spec/` — vendored Open Knowledge Format v0.1 specification.
- `test/` — copied fixture bundles plus byte-parity receipts from the
  former JavaScript tools.
- `.claude-plugin/` — Claude wiring (`/plugin marketplace add` this
  repo, `/plugin install okf`; skills load from `./skills`).
- `AGENTS.md` — the Codex contract (install = clone the repo).

No `.mjs` files ship in this repo. The old JavaScript tools are retained
only as local verification twins in the superseded ancestor repo.

## CLI

```bash
python3 okf.py validate <bundle>
python3 okf.py links <bundle>
python3 okf.py index <bundle> [--write]
python3 okf.py types <bundle> [--taxonomy <file>]
python3 okf.py tags <bundle> [--registry <file>]
python3 viz.py <bundle> [--out <path>] [--name <title>]
```

`validate` exits 1 on conformance violations. `links` is informational:
broken internal links are tolerated by OKF §5.3 because they may mark
not-yet-written knowledge. `types` and `tags` exit 1 when a registry is
present and the bundle uses unregistered values.

## Install

**Claude Code** — the repo is its own marketplace; the plugin ships
the three statics skills (loaded from `skills/`, see
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

The plugin installs the whole repo; inside a SKILL.md, `<suite>`
resolves to `${CLAUDE_PLUGIN_ROOT}` (the installed repo root), so
skills reach `<suite>/okf.py` and `<suite>/viz.py` with no further
setup. Installing by copying skill dirs into `~/.claude/skills/` is
NOT supported — the skills need the tools shipped alongside them.

To update after the repo changes: `claude plugin marketplace update
ctg-ai-okf` (local marketplaces also need a `git pull` in the clone
first).

**Codex** — clone the repo and follow [AGENTS.md](AGENTS.md): skills
are plain markdown instructions, tools run by path from the clone
(`<clone>/okf.py`).

**Requirements**: Python ≥ 3.9; zero dependencies.

## What Lives In GoE

Use `ctg-ai-goe` for dynamics:

- `rank`, `govern`, `frontier`, `queues`
- `alias`, `current`, routing `lint`
- audit/join/extraction/proposers/eval
- `okf-audit`, `okf-build-graph`, `okf-lexicon`, `okf-memory`,
  `okf-onboard`

OKF remains the plain Markdown + YAML-frontmatter contract those tools
read and write.

## Migration

`ctg-claude-okf-skills` is the pre-split ancestor and is left as-is. This
repo is the canonical home for the three OKF statics skills and tools.
The dynamic skills now ship from `ctg-ai-goe`.

Compatibility facts:

- Bundles are untouched. Existing OKF Markdown remains valid.
- Skill names are unchanged: `okf-create-node`, `okf-transform`,
  `okf-validate`.
- Hardcoded paths to `ctg-claude-okf-skills`, `okf.mjs`, or `viz.mjs`
  should move to this repo's `okf.py` / `viz.py` for statics, or to
  `ctg-ai-goe` for dynamics.

## Tests

```bash
python3 test/run.py
```

The suite drives the Python tools natively and byte-compares their
outputs against individually ledgered old-tool receipts in
`test/receipts/old/`.
