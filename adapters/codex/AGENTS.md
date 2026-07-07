# OKF — Codex Adapter Notes

The product tree is Python-only at v0.1.0: instruments run as
`python3 okf.py` and `python3 viz.py`. No `.mjs` files ship here.

Codex has no skill installer in this repo. Treat `skills/*/SKILL.md` as
plain markdown instructions, run instruments by path, and keep changes
delta-synced with receipts:

```bash
python3 test/run.py
```

Acceptance means all Python statics commands byte-match the old
verification receipts. Dynamics are outside this adapter: use
`ctg-ai-goe` for recall, governance, frontier queues, alias/current,
audit, memory, and onboarding.
