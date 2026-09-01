---
type: Decision
title: Alias Registry (bad fixture)
description: Exercises every deterministic alias guard — each entry below violates one rule.
status: draft
---

```yaml
# okf-alias-registry
- kind: tag
  canonical: music
  aliases: [tunes]
  status: declared
  evidence:
- kind: concept
  canonical: music
  aliases: [songs]
  status: declared
  evidence: cross-kind entry
- kind: tag
  canonical: ai
  aliases: [tunes]
  status: declared
  evidence: makes "tunes" ambiguous (music above, ai here)
- kind: tag
  canonical: glitch-art
  aliases: [ai]
  status: declared
  evidence: alias is a registered tag AND a canonical elsewhere (chain)
- kind: tag
  canonical: unregistered-tag
  aliases: [ghost]
  status: declared
  evidence: canonical not in the tag registry
- kind: tag
  canonical: music
  aliases: [music]
  status: maybe
  evidence: self-alias + invalid status
```
