# Vendored OKF specification

`SPEC.md` is the **Open Knowledge Format v0.2** specification, copied
verbatim (byte-identical, for diffability against upstream) from:

- Repo: https://github.com/GoogleCloudPlatform/knowledge-catalog
- Path: `okf/SPEC.md`
- Pinned at commit: `891034c0ab63d51f6a8c32490843b8c869d07ec1` (2026-08-30);
  the spec text itself last changed at `62432a0` (2026-08-20, every
  timestamp becomes an ISO 8601 datetime with an explicit offset)
- License: Apache-2.0 (same as this repo — see `LICENSE` at the repo root)

It is vendored here because this spec is the contract the skills in this
repo implement — the suite must be self-contained and pin the exact spec
text it targets. When upstream revises the spec, re-vendor deliberately
and update the skills in the same commit.

Previous pin: OKF v0.1 at `ba17dd5dfd72d357418966318466d345bf63dcfb`
(2026-06-17) — this repo's `v0.1.0` tag is the last release against it.

The upstream repo is NOT otherwise a dependency of these skills. It is
only needed for its reference tooling (the bundle visualizer) and sample
bundles.
