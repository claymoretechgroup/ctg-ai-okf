---
type: Idea
title: Badly sourced
description: Provenance family present but malformed.
generated: { by: human:someone, at: 2026-06-20T22:53:05+02:00 }
sources:
  - id: dup
    resource: https://example.com/one
  - id: dup
    title: no resource at all
  - resource: https://example.com/three
    usage_count: 5
  - resource: /ideas/missing.md
    title: dangling in-bundle source
usage_window: { from: 2026-06-01T00:00:00Z }
---

A claim.[^ghost] Another.[^dup]

[^ghost]: nothing in sources carries this id
[^dup]: dup
