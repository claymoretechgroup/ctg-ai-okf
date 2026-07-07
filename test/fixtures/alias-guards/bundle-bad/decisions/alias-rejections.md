---
type: Decision
title: Alias Rejections (bad fixture)
description: Rules out a pair the registry declares — the conflict guard must fire.
status: proposed
---

```yaml
# okf-alias-rejections
- kind: tag
  a: tunes
  b: music
  verdict: related-not-same
  reason: fixture; judged not co-referent
- kind: key
  a: something
  b: anything
  verdict: cant-tell
  reason: fixture; unenforced verdict
```
