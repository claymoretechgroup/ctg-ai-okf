---
type: Decision
title: Alias Registry (good fixture)
description: Well-formed entries — one declared tag alias, one proposed key alias.
status: draft
---

```yaml
# okf-alias-registry
- kind: tag
  canonical: music
  aliases: [tunes, Müsik]
  status: declared
  evidence: fixture governance history
- kind: key
  canonical: common-intersect
  aliases: [common-intersect-engine]
  status: proposed
  evidence: fixture corpus receipt (2 clusters, 5t/9n)
```
