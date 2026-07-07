# OKF — Codex Notes

The product tree is Python-only: instruments run as
`python3 okf.py` and `python3 viz.py` from the repo root.

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

Acceptance means all Python commands byte-match the verification
receipts committed under `test/receipts/`.
