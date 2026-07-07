# CTG AI OKF

Open Knowledge Format tooling for LLM coding agents (Claude and
Codex): everything an agent needs to create, transform, validate,
index, and visualize OKF knowledge bundles — plain markdown + YAML
frontmatter, zero dependencies, fully standalone.

## Contents

- `okf.py` — zero-dependency Python 3 statics commands:
  `validate`, `links`, `index`, `types`, and `tags`.
- `viz.py` — zero-dependency Python 3 HTML graph visualizer.
- `skills/` — agent-neutral statics skills, the ONE copy read by both
  models: `okf-create-node`, `okf-transform`, `okf-validate`. In a
  SKILL.md, `<suite>` means the install root (`${CLAUDE_PLUGIN_ROOT}`
  for Claude plugin installs, the repo clone path for Codex).
- `spec/` — vendored Open Knowledge Format v0.1 specification.
- `test/` — fixture bundles plus the byte-parity receipts the
  acceptance suite verifies against.
- `.claude-plugin/` — Claude wiring (`/plugin marketplace add` this
  repo, `/plugin install okf`; skills load from `./skills`).
- `AGENTS.md` — the Codex contract (install = clone the repo).

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

## Tests

```bash
python3 test/run.py
```

The suite drives the Python tools natively and byte-compares their
outputs against the individually ledgered receipts in
`test/receipts/old/`.

## License

Apache-2.0 — see [LICENSE](LICENSE). The vendored specification under
`spec/` is also Apache-2.0, from its upstream (see
[spec/NOTICE.md](spec/NOTICE.md)).
