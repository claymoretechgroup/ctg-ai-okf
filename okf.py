#!/usr/bin/env python3
"""okf.py - zero-dependency tooling for OKF v0.2 bundles."""

import os
import re
import sys


OKF_VERSION = "0.2"
RESERVED = {"index.md", "log.md"}
SKIP_DIRS = {".git", "node_modules"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FOOTNOTE_RE = re.compile(r"\[\^([^\]\s]+)\]")
URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
# ISO 8601 datetime with an explicit UTC offset (SPEC §5).
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})$")
# Actor convention (SPEC §7): <producer>/<version>, human:<id>, process:<id>.
ACTOR_RE = re.compile(r"^(?:\S+/\S+|human:\S+|process:\S+)$")
STATUS_VALUES = ("draft", "stable", "deprecated")
ATTESTED_COMPUTATION = "Attested Computation"


class OkfError(Exception):
    pass


def walk(root, files=None):
    if files is None:
        files = []
    for entry in sorted(os.scandir(root), key=lambda e: e.name):
        if entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        path = os.path.join(root, entry.name)
        if entry.is_dir():
            walk(path, files)
        elif entry.name.endswith(".md"):
            files.append(path)
    return files


def subdirs_of(path):
    out = []
    for entry in os.scandir(path):
        if entry.is_dir() and not entry.name.startswith(".") and entry.name not in SKIP_DIRS:
            out.append(entry.name)
    return sorted(out)


def rel(root, path):
    r = os.path.relpath(path, root)
    return "" if r == "." else r.replace(os.sep, "/")


def split_frontmatter(text):
    if not text.startswith("---\n") and text != "---":
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        raise OkfError("frontmatter block opened but not closed")
    after = text.find("\n", end + 1)
    return text[4:end], "" if after == -1 else text[after + 1 :]


# --- YAML-lite -------------------------------------------------------------
#
# The subset of YAML that OKF frontmatter uses: block mappings, block
# sequences (of scalars, flow mappings, or block mappings), flow sequences
# `[a, b]`, flow mappings `{ by: x, at: y }`, quoted and plain scalars,
# `|`/`>` block scalars, comments. Scalars stay strings — the tools only
# ever compare and print them.

KEY_RE = re.compile(r"^([^:\s\[{\"'#-][^:]*):(.*)$")
INLINE_KEY_RE = re.compile(r"^([^:\s\[{\"'#-][^:]*):(?:\s|$)")


def strip_comment(raw):
    s = raw.strip()
    if not s or s[0] in "\"'":
        return s
    for i, ch in enumerate(s):
        if ch == "#" and i > 0 and s[i - 1] in " \t":
            return s[:i].rstrip()
    return s


def split_top_level(inner):
    parts, depth, quote, cur = [], 0, None, []
    for ch in inner:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    tail = "".join(cur)
    if tail.strip() != "" or parts:
        parts.append(tail)
    return [p.strip() for p in parts if p.strip() != ""]


def parse_scalar(raw):
    value = strip_comment(raw)
    if value.startswith("[") and value.endswith("]"):
        return [parse_scalar(part) for part in split_top_level(value[1:-1])]
    if value.startswith("{") and value.endswith("}"):
        out = {}
        for part in split_top_level(value[1:-1]):
            m = re.match(r"^([^:\s\"'][^:]*?)\s*:(?:\s+(.*)|$)", part)
            if not m:
                raise OkfError(f"unparseable flow mapping entry: {json_string(part)}")
            out[m.group(1).strip()] = parse_scalar(m.group(2) or "")
        return out
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace('\\"', '"') if value[0] == '"' else inner.replace("''", "'")
    return value


class _Lines:
    def __init__(self, src):
        self.items = []
        for line in src.split("\n"):
            if line.strip() == "" or line.strip().startswith("#"):
                continue
            expanded = line.replace("\t", "  ")
            self.items.append((len(expanded) - len(expanded.lstrip(" ")), expanded.strip(), line))
        self.i = 0

    def peek(self):
        return self.items[self.i] if self.i < len(self.items) else None


def _is_item(content):
    return content == "-" or content.startswith("- ")


def _parse_block(lines, indent):
    cur = lines.peek()
    if cur is None or cur[0] < indent:
        return None
    if _is_item(cur[1]):
        return _parse_sequence(lines, cur[0])
    return _parse_mapping(lines, cur[0])


def _collect_block_scalar(lines, indent, folded):
    parts = []
    while True:
        cur = lines.peek()
        if cur is None or cur[0] <= indent:
            break
        parts.append(cur[1])
        lines.i += 1
    return (" " if folded else "\n").join(parts)


def _parse_mapping(lines, indent):
    out = {}
    last_key = None
    while True:
        cur = lines.peek()
        if cur is None or cur[0] < indent:
            return out
        if cur[0] > indent:
            if last_key is not None and isinstance(out.get(last_key), str) and not _is_item(cur[1]):
                out[last_key] = f"{out[last_key]} {strip_comment(cur[1])}".strip()
                lines.i += 1
                continue
            raise OkfError(f"unparseable frontmatter line: {json_string(cur[2])}")
        if _is_item(cur[1]):
            if last_key is not None and out.get(last_key) is None:
                out[last_key] = _parse_sequence(lines, indent)
                continue
            raise OkfError(f"unparseable frontmatter line: {json_string(cur[2])}")
        m = KEY_RE.match(cur[1])
        if not m:
            raise OkfError(f"unparseable frontmatter line: {json_string(cur[2])}")
        key = m.group(1).strip()
        rest = strip_comment(m.group(2))
        lines.i += 1
        last_key = key
        if rest == "":
            nxt = lines.peek()
            if nxt is not None and nxt[0] > indent:
                out[key] = _parse_block(lines, nxt[0])
            elif nxt is not None and nxt[0] == indent and _is_item(nxt[1]):
                out[key] = None  # sequence at the same indent; picked up above
            else:
                out[key] = None
        elif re.match(r"^[>|][+-]?$", rest):
            out[key] = _collect_block_scalar(lines, indent, rest[0] == ">")
        else:
            out[key] = parse_scalar(rest)


def _parse_sequence(lines, indent):
    items = []
    while True:
        cur = lines.peek()
        if cur is None or cur[0] != indent or not _is_item(cur[1]):
            if cur is not None and cur[0] > indent:
                raise OkfError(f"unparseable frontmatter line: {json_string(cur[2])}")
            return items
        after = cur[1][1:]
        rest = after.lstrip()
        col = indent + 1 + (len(after) - len(rest))
        if rest == "":
            lines.i += 1
            nxt = lines.peek()
            items.append(_parse_block(lines, nxt[0]) if nxt is not None and nxt[0] > indent else None)
        elif INLINE_KEY_RE.match(rest):
            lines.items[lines.i] = (col, rest, cur[2])
            items.append(_parse_mapping(lines, col))
        else:
            lines.i += 1
            items.append(parse_scalar(rest))


def parse_yaml_lite(src):
    lines = _Lines(src)
    if lines.peek() is None:
        return {}
    if _is_item(lines.peek()[1]):
        raise OkfError(f"unparseable frontmatter line: {json_string(lines.peek()[2])}")
    out = _parse_mapping(lines, lines.peek()[0])
    if lines.peek() is not None:
        raise OkfError(f"unparseable frontmatter line: {json_string(lines.peek()[2])}")
    return out


def json_string(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_doc(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    frontmatter, body = split_frontmatter(text)
    return {
        "frontmatter": None if frontmatter is None else parse_yaml_lite(frontmatter),
        "body": body,
        "raw_frontmatter": frontmatter,
    }


def title_for(path, frontmatter):
    if isinstance(frontmatter, dict) and frontmatter.get("title"):
        return frontmatter["title"]
    name = os.path.splitext(os.path.basename(path))[0]
    text = re.sub(r"[-_]+", " ", name)
    return re.sub(r"\b\w", lambda m: m.group(0).upper(), text)


# --- v0.2 frontmatter families (SPEC §5, §7, §10) ---------------------------


def normalize_verified(fm):
    """`verified` as a list of events; a bare mapping is a one-element list (§5.2)."""
    v = fm.get("verified") if isinstance(fm, dict) else None
    if isinstance(v, dict):
        return [v]
    if isinstance(v, list):
        return [e for e in v if isinstance(e, dict)]
    return []


def trust_tier(fm):
    """unverified | machine-confirmed | human-reviewed (§5.3)."""
    if not isinstance(fm, dict) or "verified" not in fm:
        return "unverified"
    events = normalize_verified(fm)
    if any(str(e.get("by", "")).startswith("human:") for e in events):
        return "human-reviewed"
    return "machine-confirmed" if events else "unverified"


def status_of(fm):
    s = fm.get("status") if isinstance(fm, dict) else None
    return s if isinstance(s, str) and s.strip() else "stable"


def sources_of(fm):
    s = fm.get("sources") if isinstance(fm, dict) else None
    return [e for e in s if isinstance(e, dict)] if isinstance(s, list) else []


def is_timestamp(value):
    return isinstance(value, str) and TIMESTAMP_RE.match(value.strip()) is not None


FENCE_RE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")


def strip_code(body):
    """Body text with fenced blocks and inline code spans removed, so that
    markers inside code (a documented `[^example]`, say) are not read as
    references (SPEC §5.1 joins footnotes on prose references only)."""
    return INLINE_CODE_RE.sub("", FENCE_RE.sub("", body))


def check_families(r, fm, body, violations, warnings):
    """Family-level checks for one concept. REQUIRED-within-family fields are
    violations; format and convention problems are warnings (§11)."""

    def ts(label, value, ref):
        if value is not None and not is_timestamp(value):
            warnings.append(f"{r}: {label} {json_string(value)} is not an ISO 8601 datetime with an explicit offset (SPEC {ref})")

    def actor(label, value):
        if not isinstance(value, str) or not ACTOR_RE.match(value.strip()):
            warnings.append(f"{r}: {label} {json_string(value)} does not follow the actor convention <producer>/<version>, human:<id>, process:<id> (SPEC §7)")

    # lifecycle
    if "status" in fm and status_of(fm) not in STATUS_VALUES:
        warnings.append(f"{r}: status {json_string(fm.get('status'))} is not one of draft | stable | deprecated (SPEC §5.4)")
    if "stale_after" in fm:
        ts("stale_after", fm.get("stale_after"), "§5.5")

    # trust
    if "generated" in fm:
        g = fm.get("generated")
        if not isinstance(g, dict):
            violations.append(f"{r}: generated must be a {{ by, at }} mapping (SPEC §5.2)")
        else:
            if not g.get("by"):
                violations.append(f"{r}: generated.by is required within generated (SPEC §5.2)")
            else:
                actor("generated.by", g.get("by"))
            ts("generated.at", g.get("at"), "§5.2")
    if "verified" in fm:
        v = fm.get("verified")
        if not isinstance(v, (dict, list)):
            violations.append(f"{r}: verified must be a {{ by, at }} mapping or a list of them (SPEC §5.2)")
        else:
            for i, e in enumerate(v if isinstance(v, list) else [v]):
                if not isinstance(e, dict):
                    violations.append(f"{r}: verified[{i}] must be a {{ by, at }} mapping (SPEC §5.2)")
                    continue
                if not e.get("by"):
                    violations.append(f"{r}: verified[{i}].by is required (SPEC §5.2)")
                else:
                    actor(f"verified[{i}].by", e.get("by"))
                if "at" not in e:
                    warnings.append(f"{r}: verified[{i}] has no at — recency is the latest at (SPEC §5.2)")
                else:
                    ts(f"verified[{i}].at", e.get("at"), "§5.2")

    # provenance
    ids = set()
    has_shared_window = "usage_window" in fm
    if "usage_window" in fm:
        check_window(r, "usage_window", fm.get("usage_window"), warnings)
    if "sources" in fm:
        s = fm.get("sources")
        if not isinstance(s, list):
            violations.append(f"{r}: sources must be a list of entries (SPEC §5.1)")
        else:
            for i, e in enumerate(s):
                if not isinstance(e, dict):
                    violations.append(f"{r}: sources[{i}] must be a mapping with a resource (SPEC §5.1)")
                    continue
                if not e.get("resource"):
                    violations.append(f"{r}: sources[{i}] has no resource — REQUIRED within an entry (SPEC §5.1)")
                if e.get("id"):
                    if e["id"] in ids:
                        warnings.append(f"{r}: sources[{i}].id {json_string(e['id'])} duplicates an earlier entry — footnotes join on id (SPEC §5.1)")
                    ids.add(e["id"])
                if "last_modified" in e:
                    ts(f"sources[{i}].last_modified", e.get("last_modified"), "§5.1")
                if "usage_window" in e:
                    check_window(r, f"sources[{i}].usage_window", e.get("usage_window"), warnings)
                elif "usage_count" in e and not has_shared_window:
                    warnings.append(f"{r}: sources[{i}].usage_count has no usage_window to frame it (SPEC §5.1)")
    for label in sorted(set(FOOTNOTE_RE.findall(strip_code(body)))):
        if label not in ids:
            warnings.append(f"{r}: footnote [^{label}] has no matching sources[].id (SPEC §5.1)")

    # v0.1 leftovers (§13.1)
    if "timestamp" in fm:
        warnings.append(f"{r}: legacy v0.1 timestamp — the concept's own change time is generated.at; the date of the thing described belongs in sources[].last_modified (SPEC §13.1, §5.1)")
    if re.search(r"^#{1,6}\s*Citations\s*$", body, re.M):
        warnings.append(f"{r}: legacy v0.1 # Citations section — superseded by sources (SPEC §13.1)")

    # computation (§10)
    if isinstance(fm.get("type"), str) and fm["type"].strip() == ATTESTED_COMPUTATION:
        if not fm.get("runtime"):
            violations.append(f"{r}: runtime is REQUIRED for type {ATTESTED_COMPUTATION} (SPEC §10.2)")
        p = fm.get("parameters")
        if p is not None:
            if not isinstance(p, list):
                warnings.append(f"{r}: parameters should be a list of {{ name, type, required }} (SPEC §10.2)")
            else:
                for i, e in enumerate(p):
                    if not isinstance(e, dict) or not e.get("name") or not e.get("type"):
                        warnings.append(f"{r}: parameters[{i}] should carry name and type (SPEC §10.2)")
        if not fm.get("computation") and not re.search(r"^#{1,6}\s*Computation\s*$", body, re.M):
            warnings.append(f"{r}: no computation — neither a computation path nor a # Computation body section (SPEC §10.3)")
        for key in ("executor", "attester"):
            if key in fm:
                e = fm.get(key)
                if not isinstance(e, dict) or not e.get("resource"):
                    warnings.append(f"{r}: {key} should be a mapping with a resource (SPEC §10.2)")
                elif key == "executor" and not isinstance(e.get("receipt"), list):
                    warnings.append(f"{r}: executor.receipt should list the fields a run must return (SPEC §10.2)")


def check_window(r, label, w, warnings):
    if not isinstance(w, dict) or "from" not in w or "to" not in w:
        warnings.append(f"{r}: {label} should be a {{ from, to }} datetime range (SPEC §5.1)")
        return
    for k in ("from", "to"):
        if not is_timestamp(w.get(k)):
            warnings.append(f"{r}: {label}.{k} {json_string(w.get(k))} is not an ISO 8601 datetime with an explicit offset (SPEC §5.1)")


def validate(bundle):
    violations = []
    warnings = []
    root = os.path.realpath(bundle)
    for path in walk(root):
        r = rel(root, path)
        name = os.path.basename(path)
        try:
            doc = read_doc(path)
        except OkfError as exc:
            violations.append(f"{r}: {exc}")
            continue
        if name == "index.md":
            is_root = os.path.dirname(path) == root
            if doc["frontmatter"] is not None and not is_root:
                violations.append(f"{r}: index.md may only carry frontmatter at the bundle root (SPEC §8)")
            if is_root and isinstance(doc["frontmatter"], dict):
                declared = doc["frontmatter"].get("okf_version")
                if declared is not None and str(declared) != OKF_VERSION:
                    warnings.append(f"{r}: bundle declares okf_version {json_string(declared)} — this tool checks OKF v{OKF_VERSION} (SPEC §12)")
            continue
        if name == "log.md":
            for h in re.finditer(r"^## +(.+)$", doc["body"], re.M):
                value = h.group(1).strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                    violations.append(f"{r}: log date heading {json_string(value)} is not ISO YYYY-MM-DD (SPEC §9)")
            continue
        fm = doc["frontmatter"]
        if fm is None:
            violations.append(f"{r}: concept document has no frontmatter block (SPEC §11.1)")
            continue
        typ = fm.get("type")
        if not isinstance(typ, str) or typ.strip() == "":
            violations.append(f'{r}: frontmatter has no non-empty "type" field (SPEC §11.2)')
        if not fm.get("description"):
            warnings.append(f'{r}: no "description" — index entries and previews will be empty')
        check_families(r, fm, doc["body"], violations, warnings)
    return violations, warnings


# --- links and path-valued fields (SPEC §6) ---------------------------------


def resolve_path(root, from_path, target):
    """Resolve a bundle-relative (/x), relative (./x, ../x), or bare relative
    path. Bare relative paths try the concept's directory first, then the
    bundle root (the spec's own examples use root-relative bare paths)."""
    if target.startswith("/"):
        return [os.path.join(root, target.lstrip("/"))]
    here = os.path.realpath(os.path.join(os.path.dirname(from_path), target))
    if target.startswith("./") or target.startswith("../"):
        return [here]
    return [here, os.path.realpath(os.path.join(root, target))]


def exists_any(candidates):
    return any(os.path.exists(c) for c in candidates)


def path_fields(fm):
    """(label, value, unambiguous) for every path-valued field (§6.2).
    `resource` and `sources[].resource` may be a URI or scope descriptor, so
    only their explicit path forms are checked."""
    out = []
    if isinstance(fm.get("resource"), str):
        out.append(("resource", fm["resource"], False))
    for i, e in enumerate(sources_of(fm)):
        if isinstance(e.get("resource"), str):
            out.append((f"sources[{i}].resource", e["resource"], False))
    if isinstance(fm.get("computation"), str):
        out.append(("computation", fm["computation"], True))
    for key in ("executor", "attester"):
        e = fm.get(key)
        if isinstance(e, dict) and isinstance(e.get("resource"), str):
            out.append((f"{key}.resource", e["resource"], True))
    return out


def inside_root(root, candidate):
    real = os.path.realpath(candidate)
    return real == root or real.startswith(root + os.sep)


def check_links(bundle):
    """Three kinds of unresolved target, kept apart because they mean
    different things (SPEC §6.1 vs §6.2):

    - `links`: a body link to a concept that does not exist — tolerated,
      may be not-yet-written knowledge.
    - `fields`: a path-valued frontmatter field pointing inside the bundle
      at nothing — usually a mistake.
    - `external`: a path-valued field that escapes the bundle root and
      finds no file there — provenance breakage, never a placeholder.

    `dangling` maps each unresolved internal target to the files that
    reference it, for the parallel-authoring convergence report."""
    root = os.path.realpath(bundle)
    links, fields, external = [], [], []
    dangling = {}
    for path in walk(root):
        try:
            doc = read_doc(path)
        except OkfError:
            continue
        for m in LINK_RE.finditer(doc["body"]):
            target = m.group(1).split("#", 1)[0]
            if target == "" or URL_RE.match(target):
                continue
            candidate = resolve_path(root, path, target)[0]
            if not os.path.exists(candidate):
                links.append(f"{rel(root, path)} -> {m.group(1)}")
                key = rel(root, candidate) if inside_root(root, candidate) else target
                dangling.setdefault(key, []).append(rel(root, path))
        fm = doc["frontmatter"]
        if not isinstance(fm, dict):
            continue
        for label, value, unambiguous in path_fields(fm):
            v = value.strip()
            if v == "" or URL_RE.match(v):
                continue
            explicit = v.startswith("/") or v.startswith("./") or v.startswith("../")
            if not explicit and not unambiguous:
                continue
            candidates = resolve_path(root, path, v)
            if exists_any(candidates):
                continue
            line = f"{rel(root, path)} -> {label}: {value}"
            if any(inside_root(root, c) for c in candidates):
                fields.append(line)
            else:
                external.append(line)
    return {"links": links, "fields": fields, "external": external, "dangling": dangling}


# --- indexes (SPEC §8) ------------------------------------------------------


def build_index(dir_path, root):
    concepts = sorted(
        entry.name
        for entry in os.scandir(dir_path)
        if entry.is_file() and entry.name.endswith(".md") and entry.name not in RESERVED
    )
    dirs = [d for d in subdirs_of(dir_path) if len(walk(os.path.join(dir_path, d))) > 0]
    if not concepts and not dirs:
        return None
    lines = []
    if concepts:
        lines.extend(["# Contents", ""])
        for name in concepts:
            fm = None
            try:
                fm = read_doc(os.path.join(dir_path, name))["frontmatter"]
            except OkfError:
                pass
            desc = f" - {fm.get('description')}" if isinstance(fm, dict) and fm.get("description") else ""
            lines.append(f"* [{title_for(os.path.join(dir_path, name), fm)}]({name}){desc}")
        lines.append("")
    if dirs:
        lines.extend(["# Subdirectories", ""])
        for d in dirs:
            lines.append(f"* [{d}]({d}/)")
        lines.append("")
    index_path = os.path.join(dir_path, "index.md")
    prefix = ""
    if dir_path == root and os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            frontmatter, _ = split_frontmatter(raw)
            if frontmatter is not None:
                prefix = f"---\n{frontmatter}\n---\n\n"
        except OkfError:
            pass
    return prefix + "\n".join(lines).rstrip() + "\n"


def generate_indexes(bundle, write=False):
    root = os.path.realpath(bundle)
    dirs = {root}
    for path in walk(root):
        dirs.add(os.path.dirname(path))
    results = []
    for dir_path in sorted(dirs):
        content = build_index(dir_path, root)
        if content is None:
            continue
        index_path = os.path.join(dir_path, "index.md")
        existing = None
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as fh:
                existing = fh.read()
        changed = existing != content
        if write and changed:
            with open(index_path, "w", encoding="utf-8") as fh:
                fh.write(content)
        results.append({"path": rel(root, index_path) or "index.md", "changed": changed, "content": content})
    return results


# --- tag and type registries -------------------------------------------------


def parse_tag_registry(text):
    m = re.search(r"```[a-z]*\n# okf-tag-registry\n([\s\S]*?)```", text)
    if not m:
        return None
    facets = {}
    for line in re.sub(r",\s*\n\s+", ", ", m.group(1)).split("\n"):
        fm = re.match(r"^([a-z][a-z-]*):\s*\[([^\]]*)\]", line)
        if fm:
            facets[fm.group(1)] = [s.strip() for s in fm.group(2).split(",") if s.strip()]
    return facets if facets else None


def near_duplicate(a, b):
    stem = lambda t: re.sub(r"s$", "", t)
    if stem(a) == stem(b):
        return True
    sa, sb = a.split("-"), b.split("-")
    short, long = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    if len(short) == len(long):
        return False
    head = "-".join(long[: len(short)])
    tail = "-".join(long[-len(short) :])
    return "-".join(short) == head or "-".join(short) == tail


def tag_report(bundle, registry_path):
    root = os.path.realpath(bundle)
    uses = {}
    concepts = 0
    for path in walk(root):
        try:
            doc = read_doc(path)
        except OkfError:
            continue
        concepts += 1
        tags = doc["frontmatter"].get("tags") if isinstance(doc["frontmatter"], dict) else []
        if not isinstance(tags, list):
            tags = []
        for tag in tags:
            uses.setdefault(tag, []).append(rel(root, path))
    registry = None
    if registry_path and os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as fh:
            registry = parse_tag_registry(fh.read())
    registered = set(t for vals in registry.values() for t in vals) if registry else None
    tags = sorted(uses.keys())
    single_use = [t for t in tags if len(uses[t]) == 1]
    unknown = [t for t in tags if registered is not None and t not in registered]
    dupes = []
    for i, a in enumerate(tags):
        for b in tags[i + 1 :]:
            if near_duplicate(a, b):
                dupes.append((a, b))
    unused = sorted([t for t in registered if t not in uses]) if registered is not None else []
    return {
        "concepts": concepts,
        "uses": uses,
        "single_use": single_use,
        "unknown": unknown,
        "dupes": dupes,
        "unused": unused,
        "has_registry": registry is not None,
    }


def parse_type_registry(text):
    block = re.search(r"```[a-z]*\n# okf-type-registry\n([\s\S]*?)```", text)
    types = {}
    if block:
        for line in block.group(1).split("\n"):
            m = re.match(r"^([A-Za-z][A-Za-z ]*?):\s*(\S*)", line)
            if m:
                types[m.group(1).strip()] = re.sub(r"/$", "", m.group(2))
        return types if types else None
    for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+?)\/?`\s*\|", text, re.M):
        types[m.group(1)] = m.group(2)
    if types:
        return types
    for section in re.split(r"^### +", text, flags=re.M)[1:]:
        if not re.search(r"^\s*[-*]?\s*\**Criteria\**\s*[:*]", section, re.I | re.M):
            continue
        types[section.split("\n")[0].strip()] = ""
    return types if types else None


def type_report(bundle, taxonomy_path):
    root = os.path.realpath(bundle)
    registry = None
    if os.path.exists(taxonomy_path):
        with open(taxonomy_path, "r", encoding="utf-8") as fh:
            registry = parse_type_registry(fh.read())
    uses = {}
    concepts = 0
    for path in walk(root):
        if os.path.basename(path) in RESERVED:
            continue
        try:
            fm = read_doc(path)["frontmatter"]
        except OkfError:
            continue
        if not isinstance(fm, dict) or not isinstance(fm.get("type"), str) or fm.get("type").strip() == "":
            continue
        concepts += 1
        typ = fm["type"].strip()
        uses.setdefault(typ, []).append(rel(root, path))
    if registry is None:
        return {"concepts": concepts, "uses": uses, "registry": None}
    unknown = sorted([t for t in uses if t not in registry])
    misplaced = []
    for typ, files in uses.items():
        dir_name = registry.get(typ)
        if dir_name is None or dir_name == "":
            continue
        for f in files:
            if f.split("/")[0] != dir_name and not f.startswith(f"{dir_name}/"):
                misplaced.append((f, typ, dir_name))
    unused = sorted([t for t in registry if t not in uses])
    return {
        "concepts": concepts,
        "uses": uses,
        "registry": registry,
        "unknown": unknown,
        "misplaced": misplaced,
        "unused": unused,
    }


# --- CLI ---------------------------------------------------------------------


USAGE = {
    "validate": (
        "okf.py validate <bundle-dir>",
        "Spec conformance (SPEC §11 plus the §5/§7/§10 family rules). Prints\n"
        "warnings then VIOLATION lines. Exit 1 when any violation exists.",
        [],
    ),
    "links": (
        "okf.py links <bundle-dir> [--dangling]",
        "Unresolved targets in three groups: broken body links (tolerated, §6.1),\n"
        "path-valued fields pointing nowhere inside the bundle, and path-valued\n"
        "fields that escape the bundle root and find no file (provenance\n"
        "breakage). Exit 1 only for the external group.",
        [("--dangling", "group unresolved internal targets by directory with the files that reference them")],
    ),
    "index": (
        "okf.py index <bundle-dir> [--write]",
        "Report stale index.md files (SPEC §8); regenerate them with --write.",
        [("--write", "rewrite every stale index.md in place")],
    ),
    "tags": (
        "okf.py tags <bundle-dir> [--registry <file>]",
        "Tag inventory: single-use tags, near-duplicate candidates, and — when a\n"
        "registry exists — registered-but-unused and UNREGISTERED tags. Exit 1\n"
        "only for unregistered tags.",
        [("--registry <file>", "tag registry (default <bundle>/decisions/tag-vocabulary.md)")],
    ),
    "types": (
        "okf.py types <bundle-dir> [--taxonomy <file>]",
        "Type inventory; with a taxonomy, misplaced files are warnings and\n"
        "UNREGISTERED types exit 1.",
        [("--taxonomy <file>", "type taxonomy (default <bundle>/decisions/type-taxonomy.md)")],
    ),
}


def usage(cmd=None, stream=None):
    stream = stream or sys.stderr
    if cmd is None:
        stream.write("usage: okf.py <command> <bundle-dir> [options]\n\ncommands:\n")
        for name, (synopsis, _summary, _flags) in USAGE.items():
            stream.write(f"  {synopsis}\n")
        stream.write("\nrun `okf.py <command> --help` for that command's flags.\n")
        return
    synopsis, summary, flags = USAGE[cmd]
    stream.write(f"usage: {synopsis}\n\n{summary}\n")
    if flags:
        stream.write("\noptions:\n")
        for name, help_text in flags:
            stream.write(f"  {name:<20} {help_text}\n")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        usage(None, sys.stdout if argv else sys.stderr)
        return 0 if argv else 2
    cmd = argv[0]
    if cmd not in USAGE:
        sys.stderr.write(f"unknown command: {cmd}\n")
        usage()
        return 2
    if "-h" in argv[1:] or "--help" in argv[1:]:
        usage(cmd, sys.stdout)
        return 0
    if len(argv) < 2:
        usage(cmd)
        return 2
    bundle, rest = argv[1], argv[2:]
    if not os.path.isdir(bundle):
        sys.stderr.write(f"not a directory: {bundle}\n")
        return 2

    if cmd == "validate":
        violations, warnings = validate(bundle)
        for w in warnings:
            print(f"warning: {w}")
        for v in violations:
            print(f"VIOLATION: {v}")
        print(f"\n{len(violations)} violation(s), {len(warnings)} warning(s)")
        return 1 if violations else 0

    if cmd == "links":
        r = check_links(bundle)
        if "--dangling" in rest:
            by_dir = {}
            for target, referrers in r["dangling"].items():
                by_dir.setdefault(os.path.dirname(target) or ".", []).append((target, referrers))
            for d in sorted(by_dir):
                print(f"{d}/")
                for target, referrers in sorted(by_dir[d], key=lambda kv: (-len(kv[1]), kv[0])):
                    print(f"  {len(referrers):>3}  {target}")
                    for f in sorted(set(referrers)):
                        print(f"         <- {f}")
            print(f"\n{len(r['dangling'])} dangling target(s), {sum(len(v) for v in r['dangling'].values())} reference(s)")
            return 0
        for b in r["links"]:
            print(f"broken: {b}")
        for b in r["fields"]:
            print(f"missing: {b}")
        for b in r["external"]:
            print(f"EXTERNAL MISSING: {b}")
        print(f"\n{len(r['links'])} broken internal link(s) (tolerated per SPEC §6.1 — may be not-yet-written knowledge)")
        print(f"{len(r['fields'])} path-valued field(s) pointing nowhere inside the bundle (SPEC §6.2)")
        print(f"{len(r['external'])} path-valued field(s) escaping the bundle with no file there (provenance breakage)")
        return 1 if r["external"] else 0

    if cmd == "index":
        write = "--write" in rest
        results = generate_indexes(bundle, write)
        for r in results:
            status = "wrote" if write and r["changed"] else "stale" if r["changed"] else "ok   "
            print(f"{status}  {r['path']}")
        if not write and any(r["changed"] for r in results):
            print("\nrun with --write to apply")
        return 0

    if cmd == "tags":
        registry_path = flag(rest, "--registry", os.path.join(bundle, "decisions", "tag-vocabulary.md"))
        r = tag_report(bundle, registry_path)
        assignments = sum(len(fs) for fs in r["uses"].values())
        print(f"{r['concepts']} concept(s), {assignments} tag assignment(s), {len(r['uses'])} distinct tag(s), {len(r['single_use'])} single-use")
        if not r["has_registry"]:
            print(f"no registry found (looked for {registry_path}) — inventory only")
        if r["single_use"]:
            print("\nsingle use (inventory, not a defect):")
            for t in r["single_use"]:
                print(f"  {t}  ({r['uses'][t][0]})")
        if r["dupes"]:
            print("\nnear-duplicate candidates (review, not auto-merge):")
            for a, b in r["dupes"]:
                print(f"  {a} ({len(r['uses'][a])}) ~ {b} ({len(r['uses'][b])})")
        if r["unused"]:
            print(f"\nregistered but unused: {', '.join(r['unused'])}")
        for t in r["unknown"]:
            print(f"UNREGISTERED: {t}  ({', '.join(r['uses'][t])})")
        if r["has_registry"]:
            print(f"\n{len(r['unknown'])} unregistered tag(s)")
        return 1 if r["unknown"] else 0

    if cmd == "types":
        taxonomy_path = flag(rest, "--taxonomy", os.path.join(bundle, "decisions", "type-taxonomy.md"))
        r = type_report(bundle, taxonomy_path)
        print(f"{r['concepts']} typed concept(s), {len(r['uses'])} distinct type(s)")
        if r["registry"] is None:
            print(f"no type registry found (looked for {taxonomy_path}) — inventory only:")
            for typ, files in sorted(r["uses"].items(), key=lambda kv: -len(kv[1])):
                print(f"  {typ} ({len(files)})")
            return 0
        if r["unused"]:
            print(f"registered but unused: {', '.join(r['unused'])}")
        if r["misplaced"]:
            print("\nmisplaced (type's registered directory, warning only):")
            for f, typ, dir_name in r["misplaced"]:
                print(f"  {f}  ({typ} -> {dir_name}/)")
        for typ in r["unknown"]:
            print(f"UNREGISTERED TYPE: {typ}  ({', '.join(r['uses'][typ])})")
        print(f"\n{len(r['unknown'])} unregistered type(s)")
        return 1 if r["unknown"] else 0

    sys.stderr.write(f"unknown command: {cmd}\n")
    return 2


def flag(args, name, default):
    try:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    except ValueError:
        pass
    return default


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
