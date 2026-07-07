# Claude Adapter

Claude Code consumes these skills by copying skill directories into
`~/.claude/skills/` or through the plugin manifest.

For the split install, copy:

```bash
cp -a skills/okf-create-node ~/.claude/skills/
cp -a skills/okf-transform ~/.claude/skills/
cp -a skills/okf-validate ~/.claude/skills/
```

Refresh the five dynamic skills from `ctg-ai-goe`, not from this repo:

```bash
cp -a /home/mastergray/claymoretechgroup/github/projects/ctg-ai-goe/adapters/claude/skills/okf-audit ~/.claude/skills/
cp -a /home/mastergray/claymoretechgroup/github/projects/ctg-ai-goe/adapters/claude/skills/okf-build-graph ~/.claude/skills/
cp -a /home/mastergray/claymoretechgroup/github/projects/ctg-ai-goe/adapters/claude/skills/okf-lexicon ~/.claude/skills/
cp -a /home/mastergray/claymoretechgroup/github/projects/ctg-ai-goe/adapters/claude/skills/okf-memory ~/.claude/skills/
cp -a /home/mastergray/claymoretechgroup/github/projects/ctg-ai-goe/adapters/claude/skills/okf-onboard ~/.claude/skills/
```

After any copy, run `python3 test/run.py` in this repo before building on
the sync.
