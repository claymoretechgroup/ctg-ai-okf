#!/usr/bin/env python3
"""okf.py - zero-dependency tooling for OKF v0.1 bundles."""

import os
import re
import sys


RESERVED = {"index.md", "log.md"}
SKIP_DIRS = {".git", "node_modules"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


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


def parse_scalar(raw):
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if inner == "" else [parse_scalar(part) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def parse_yaml_lite(src):
    out = {}
    pending_key = None
    last_scalar_key = None
    for line in src.split("\n"):
        t = line.strip()
        if t == "" or t.startswith("#"):
            continue
        indented = bool(re.match(r"\s", line))
        is_list_item = t.startswith("- ") or t == "-"
        if is_list_item and pending_key is not None:
            if not isinstance(out.get(pending_key), list):
                out[pending_key] = []
            out[pending_key].append(parse_scalar(t[1:]))
            continue
        if indented:
            if pending_key is not None:
                m = re.match(r"^([^:\s][^:]*):(.*)$", t)
                if m:
                    if not isinstance(out.get(pending_key), dict):
                        out[pending_key] = {}
                    out[pending_key][m.group(1).strip()] = parse_scalar(m.group(2))
                    continue
            if last_scalar_key is not None and isinstance(out.get(last_scalar_key), str):
                out[last_scalar_key] = f"{out[last_scalar_key]} {t}".strip()
                continue
            raise OkfError(f"unparseable frontmatter line: {json_string(line)}")
        m = re.match(r"^([^:\s][^:]*):(.*)$", line)
        if not m:
            raise OkfError(f"unparseable frontmatter line: {json_string(line)}")
        key = m.group(1).strip()
        rest = m.group(2).strip()
        if rest == "":
            pending_key = key
            last_scalar_key = None
            out[key] = None
        elif re.match(r"^[>|][+-]?$", rest):
            pending_key = None
            last_scalar_key = key
            out[key] = ""
        else:
            pending_key = None
            out[key] = parse_scalar(rest)
            last_scalar_key = key if isinstance(out[key], str) else None
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
                violations.append(f"{r}: index.md may only carry frontmatter at the bundle root (SPEC §11)")
            continue
        if name == "log.md":
            for h in re.finditer(r"^## +(.+)$", doc["body"], re.M):
                value = h.group(1).strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                    violations.append(f"{r}: log date heading {json_string(value)} is not ISO YYYY-MM-DD (SPEC §7)")
            continue
        fm = doc["frontmatter"]
        if fm is None:
            violations.append(f"{r}: concept document has no frontmatter block (SPEC §9.1)")
            continue
        typ = fm.get("type")
        if not isinstance(typ, str) or typ.strip() == "":
            violations.append(f'{r}: frontmatter has no non-empty "type" field (SPEC §9.2)')
        if not fm.get("description"):
            warnings.append(f'{r}: no "description" — index entries and previews will be empty')
    return violations, warnings


def check_links(bundle):
    root = os.path.realpath(bundle)
    broken = []
    for path in walk(root):
        try:
            body = read_doc(path)["body"]
        except OkfError:
            continue
        for m in LINK_RE.finditer(body):
            target = m.group(1).split("#", 1)[0]
            if target == "" or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            abs_path = os.path.join(root, target.lstrip("/")) if target.startswith("/") else os.path.realpath(os.path.join(os.path.dirname(path), target))
            if not os.path.exists(abs_path):
                broken.append(f"{rel(root, path)} -> {m.group(1)}")
    return broken


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
    orphans = [t for t in tags if len(uses[t]) == 1]
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
        "orphans": orphans,
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


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: okf.py <validate|links|index|tags|types> <bundle-dir> [--write] [--registry <file>] [--taxonomy <file>]\n")
        return 2
    cmd, bundle, rest = argv[0], argv[1], argv[2:]
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
        broken = check_links(bundle)
        for b in broken:
            print(f"broken: {b}")
        print(f"\n{len(broken)} broken internal link(s) (tolerated per SPEC §5.3 — may be not-yet-written knowledge)")
        return 0

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
        print(f"{r['concepts']} concept(s), {assignments} tag assignment(s), {len(r['uses'])} distinct tag(s), {len(r['orphans'])} orphan(s)")
        if not r["has_registry"]:
            print(f"no registry found (looked for {registry_path}) — inventory only")
        if r["orphans"]:
            print("\norphans (single use):")
            for t in r["orphans"]:
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
