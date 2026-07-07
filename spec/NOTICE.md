# Vendored OKF specification

`SPEC.md` is the **Open Knowledge Format v0.1** specification, copied
verbatim (byte-identical, for diffability against upstream) from:

- Repo: https://github.com/GoogleCloudPlatform/knowledge-catalog
- Path: `okf/SPEC.md`
- Pinned at commit: `ba17dd5dfd72d357418966318466d345bf63dcfb` (2026-06-17)
- License: Apache-2.0 (see `LICENSE.md` in this directory)

It is vendored here because this spec is the contract the skills in this
repo implement — the suite must be self-contained and pin the exact spec
text it targets. When upstream revises the spec, re-vendor deliberately
and update the skills in the same commit.

The upstream repo is NOT otherwise a dependency of these skills. It is
only needed for its reference tooling (the bundle visualizer) and sample
bundles.
