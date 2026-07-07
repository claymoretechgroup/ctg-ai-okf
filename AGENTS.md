# OKF — Codex Notes

The product tree is Python-only: instruments run as
`python3 okf.py` and `python3 viz.py` from the repo root. No `.mjs`
files ship here.

There is exactly one copy of everything: `okf.py`/`viz.py` are the
tools, `skills/` is the shared, agent-neutral skill source — both
models read the same SKILL.md files. In a SKILL.md, `<suite>` means
the install root: the repo clone for Codex,
`${CLAUDE_PLUGIN_ROOT}` for Claude plugin installs (see
`.claude-plugin/plugin.json`).

Codex has no skill installer. Treat `skills/*/SKILL.md` as plain
markdown instructions, run instruments by path, and keep changes
delta-synced with receipts:

```bash
python3 test/run.py
```

Acceptance means all Python statics commands byte-match the old
verification receipts. Dynamics are outside this product: use
`ctg-ai-goe` for recall, governance, frontier queues, alias/current,
audit, memory, and onboarding.
