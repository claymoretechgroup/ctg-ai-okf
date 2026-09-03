---
type: Decision
title: Bundle conventions
description: How footnotes are written in this bundle.
tags: [conventions, provenance]
generated: { by: claude-code/test, at: 2026-09-01T10:00:00Z }
sources:
  - id: spec
    resource: https://example.test/okf/SPEC.md
    title: OKF spec
    last_modified: 2026-08-20T00:00:00Z
---
# Bundle conventions

Cite a source with a footnote marker written as `[^text]` after the claim,
where `text` is the `sources[].id`. The marker in this sentence is prose
only when it is not inside code; this one is real.[^spec]

```markdown
Documented example: a claim.[^example]
```
