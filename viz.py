#!/usr/bin/env python3
"""viz.py - zero-dependency OKF bundle visualizer."""

import json
import os
import re
import sys

from okf import LINK_RE, read_doc, walk


PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
           "#edc949", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def build_graph(bundle):
    root = os.path.realpath(bundle)
    nodes = []
    by_id = {}
    for path in walk(root):
        if os.path.basename(path) == "index.md":
            continue
        node_id = re.sub(r"\.md$", "", rel(root, path))
        try:
            doc = read_doc(path)
        except Exception:
            with open(path, "r", encoding="utf-8") as fh:
                doc = {"frontmatter": None, "body": fh.read()}
        fm = doc["frontmatter"] if isinstance(doc.get("frontmatter"), dict) else {}
        node = {
            "id": node_id,
            "type": fm["type"] if isinstance(fm.get("type"), str) and fm.get("type") else ("Log" if os.path.basename(path) == "log.md" else "Untyped"),
            "title": fm.get("title") or os.path.splitext(os.path.basename(path))[0],
            "description": fm.get("description") or "",
            "tags": fm.get("tags") if isinstance(fm.get("tags"), list) else [],
            "resource": fm.get("resource") if isinstance(fm.get("resource"), str) else "",
            "timestamp": fm.get("timestamp") or "",
            "body": doc["body"],
        }
        nodes.append(node)
        by_id[node_id] = node

    edges = []
    seen = set()
    for node in nodes:
        dir_path = os.path.join(root, os.path.dirname(node["id"]))
        for match in LINK_RE.finditer(node["body"]):
            target = match.group(1).split("#", 1)[0]
            if target == "" or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            abs_path = os.path.join(root, target.lstrip("/")) if target.startswith("/") else os.path.realpath(os.path.join(dir_path, target))
            if not os.path.exists(abs_path) or not abs_path.endswith(".md"):
                continue
            target_id = re.sub(r"\.md$", "", rel(root, abs_path))
            if target_id not in by_id or target_id == node["id"]:
                continue
            key = f"{node['id']} -> {target_id}"
            if key in seen:
                continue
            seen.add(key)
            edges.append({"source": node["id"], "target": target_id})
    return {"nodes": nodes, "edges": edges}


def escape_html(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(name, graph):
    types = sorted(set(n["type"] for n in graph["nodes"]))
    colors = {t: PALETTE[i % len(PALETTE)] for i, t in enumerate(types)}
    data = {"name": name, "types": types, "colors": colors, **graph}
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return TEMPLATE.replace("__TITLE__", escape_html(name)).replace("__DATA__", encoded)


TEMPLATE = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>__TITLE__ — OKF bundle</title>\n<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js"></script>\n<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>\n<style>\n  * { box-sizing: border-box; }\n  body { margin: 0; font: 14px/1.45 -apple-system, "Segoe UI", Roboto, sans-serif; color: #1a1a2e; display: flex; height: 100vh; }\n  #side { width: 230px; min-width: 230px; border-right: 1px solid #ddd; padding: 12px; overflow-y: auto; background: #fafafa; }\n  #side h1 { font-size: 15px; margin: 0 0 4px; }\n  #side .meta { color: #777; font-size: 12px; margin-bottom: 10px; }\n  #search { width: 100%; padding: 6px 8px; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 10px; }\n  .typerow { display: flex; align-items: center; gap: 6px; margin: 3px 0; font-size: 13px; cursor: pointer; }\n  .swatch { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }\n  #fit { margin-top: 10px; padding: 5px 10px; border: 1px solid #ccc; border-radius: 5px; background: #fff; cursor: pointer; }\n  #cy { flex: 1; min-width: 0; }\n  #detail { width: 420px; min-width: 320px; border-left: 1px solid #ddd; padding: 16px; overflow-y: auto; }\n  #detail .placeholder { color: #999; margin-top: 40%; text-align: center; }\n  #detail h2 { margin: 0 0 2px; font-size: 18px; }\n  .chip { display: inline-block; font-size: 11px; padding: 1px 8px; border-radius: 9px; color: #fff; margin-right: 6px; }\n  .tag { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 9px; background: #eee; color: #555; margin: 0 4px 4px 0; }\n  .cid { color: #999; font-size: 12px; font-family: monospace; margin-bottom: 6px; }\n  .desc { color: #444; font-style: italic; margin: 6px 0 10px; }\n  .res a { font-size: 12px; word-break: break-all; }\n  #body { border-top: 1px solid #eee; margin-top: 12px; padding-top: 10px; }\n  #body table { border-collapse: collapse; font-size: 12px; }\n  #body th, #body td { border: 1px solid #ddd; padding: 3px 7px; text-align: left; }\n  #body pre { background: #f5f5f5; padding: 8px; border-radius: 5px; overflow-x: auto; font-size: 12px; }\n  #body code { background: #f5f5f5; font-size: 12px; }\n  #body a { color: #2a6fb0; }\n  #backlinks { border-top: 1px solid #eee; margin-top: 12px; padding-top: 10px; }\n  #backlinks h3 { font-size: 13px; margin: 0 0 6px; color: #666; }\n  #backlinks a { display: block; font-size: 13px; margin: 2px 0; color: #2a6fb0; cursor: pointer; }\n</style>\n</head>\n<body>\n<div id="side">\n  <h1 id="bname"></h1>\n  <div class="meta" id="bmeta"></div>\n  <input id="search" placeholder="search title / id / tags…">\n  <div id="types"></div>\n  <button id="fit">Fit graph</button>\n</div>\n<div id="cy"></div>\n<div id="detail"><div class="placeholder">Select a concept</div></div>\n<script>\nvar DATA = __DATA__;\ndocument.getElementById(\'bname\').textContent = DATA.name;\ndocument.getElementById(\'bmeta\').textContent = DATA.nodes.length + \' concepts · \' + DATA.edges.length + \' links\';\n\nvar nodeById = {};\nDATA.nodes.forEach(function (n) { nodeById[n.id] = n; });\nvar inbound = {};\nDATA.edges.forEach(function (e) { (inbound[e.target] = inbound[e.target] || []).push(e.source); });\n\nvar cy = cytoscape({\n  container: document.getElementById(\'cy\'),\n  elements: DATA.nodes.map(function (n) {\n    return { data: { id: n.id, label: n.title, type: n.type } };\n  }).concat(DATA.edges.map(function (e) {\n    return { data: { id: e.source + \'->\' + e.target, source: e.source, target: e.target } };\n  })),\n  style: [\n    { selector: \'node\', style: {\n        \'label\': \'data(label)\', \'font-size\': 8, \'width\': 16, \'height\': 16,\n        \'text-wrap\': \'wrap\', \'text-max-width\': 90, \'text-valign\': \'bottom\', \'text-margin-y\': 3,\n        \'color\': \'#333\', \'background-color\': \'#999\' } },\n    { selector: \'edge\', style: {\n        \'width\': 1, \'line-color\': \'#ccc\', \'target-arrow-color\': \'#ccc\',\n        \'target-arrow-shape\': \'triangle\', \'arrow-scale\': 0.7, \'curve-style\': \'bezier\' } },\n    { selector: \'node:selected\', style: { \'border-width\': 3, \'border-color\': \'#1a1a2e\' } },\n    { selector: \'.dim\', style: { \'opacity\': 0.12 } },\n    { selector: \'.hide\', style: { \'display\': \'none\' } }\n  ].concat(DATA.types.map(function (t) {\n    return { selector: \'node[type="\' + t.replace(/"/g, \'\\\\\\\\"\') + \'"]\',\n             style: { \'background-color\': DATA.colors[t] } };\n  })),\n  layout: { name: \'cose\', animate: false, nodeRepulsion: 9000, idealEdgeLength: 60 }\n});\n\n// type filter\nvar typesEl = document.getElementById(\'types\');\nDATA.types.forEach(function (t) {\n  var row = document.createElement(\'label\');\n  row.className = \'typerow\';\n  var cb = document.createElement(\'input\');\n  cb.type = \'checkbox\'; cb.checked = true;\n  cb.addEventListener(\'change\', applyFilters);\n  var sw = document.createElement(\'span\');\n  sw.className = \'swatch\'; sw.style.background = DATA.colors[t];\n  var count = DATA.nodes.filter(function (n) { return n.type === t; }).length;\n  row.appendChild(cb); row.appendChild(sw);\n  row.appendChild(document.createTextNode(t + \' (\' + count + \')\'));\n  row.dataset.type = t;\n  typesEl.appendChild(row);\n});\n\nfunction applyFilters() {\n  var enabled = {};\n  Array.prototype.forEach.call(typesEl.children, function (row) {\n    enabled[row.dataset.type] = row.querySelector(\'input\').checked;\n  });\n  var q = document.getElementById(\'search\').value.trim().toLowerCase();\n  cy.nodes().forEach(function (el) {\n    var n = nodeById[el.id()];\n    el.toggleClass(\'hide\', !enabled[n.type]);\n    var match = !q || n.id.toLowerCase().indexOf(q) >= 0 ||\n      n.title.toLowerCase().indexOf(q) >= 0 ||\n      n.description.toLowerCase().indexOf(q) >= 0 ||\n      n.tags.join(\' \').toLowerCase().indexOf(q) >= 0;\n    el.toggleClass(\'dim\', !match);\n  });\n}\ndocument.getElementById(\'search\').addEventListener(\'input\', applyFilters);\ndocument.getElementById(\'fit\').addEventListener(\'click\', function () { cy.fit(undefined, 30); });\n\nfunction esc(s) {\n  return String(s).replace(/&/g, \'&amp;\').replace(/</g, \'&lt;\').replace(/>/g, \'&gt;\');\n}\n\nfunction targetIdOf(href, fromId) {\n  if (!href || /^[a-z][a-z0-9+.-]*:/i.test(href) || href.charAt(0) === \'#\') return null;\n  var path = href.split(\'#\')[0].replace(/\\\\.md$/, \'\');\n  if (path.charAt(0) === \'/\') path = path.slice(1);\n  else {\n    var base = fromId.indexOf(\'/\') >= 0 ? fromId.slice(0, fromId.lastIndexOf(\'/\')).split(\'/\') : [];\n    var parts = path.split(\'/\');\n    for (var i = 0; i < parts.length; i++) {\n      if (parts[i] === \'..\') base.pop();\n      else if (parts[i] !== \'.\') base.push(parts[i]);\n    }\n    path = base.join(\'/\');\n  }\n  return nodeById[path] ? path : null;\n}\n\nfunction show(id) {\n  var n = nodeById[id];\n  var d = document.getElementById(\'detail\');\n  var html = \'<h2>\' + esc(n.title) + \'</h2><div class="cid">\' + esc(n.id) + \'</div>\' +\n    \'<span class="chip" style="background:\' + DATA.colors[n.type] + \'">\' + esc(n.type) + \'</span>\' +\n    (n.timestamp ? \'<span style="font-size:11px;color:#999">\' + esc(n.timestamp) + \'</span>\' : \'\') +\n    (n.description ? \'<div class="desc">\' + esc(n.description) + \'</div>\' : \'\') +\n    (n.tags.length ? \'<div>\' + n.tags.map(function (t) { return \'<span class="tag">\' + esc(t) + \'</span>\'; }).join(\'\') + \'</div>\' : \'\') +\n    (n.resource ? \'<div class="res">resource: <a href="\' + esc(n.resource) + \'" target="_blank" rel="noopener">\' + esc(n.resource) + \'</a></div>\' : \'\') +\n    \'<div id="body"></div><div id="backlinks"></div>\';\n  d.innerHTML = html;\n  var bodyEl = d.querySelector(\'#body\');\n  if (window.marked) bodyEl.innerHTML = marked.parse(n.body);\n  else bodyEl.innerHTML = \'<pre>\' + esc(n.body) + \'</pre>\';\n  // rewire internal links to in-viewer navigation\n  Array.prototype.forEach.call(bodyEl.querySelectorAll(\'a\'), function (a) {\n    var tid = targetIdOf(a.getAttribute(\'href\'), n.id);\n    if (tid) {\n      a.addEventListener(\'click\', function (ev) { ev.preventDefault(); select(tid); });\n      a.removeAttribute(\'target\');\n    } else if (/^[a-z][a-z0-9+.-]*:/i.test(a.getAttribute(\'href\') || \'\')) {\n      a.setAttribute(\'target\', \'_blank\');\n      a.setAttribute(\'rel\', \'noopener\');\n    } else {\n      a.replaceWith.apply(a, a.childNodes); // unresolvable local link → plain text\n    }\n  });\n  var back = inbound[id] || [];\n  var bl = d.querySelector(\'#backlinks\');\n  bl.innerHTML = \'<h3>Linked from (\' + back.length + \')</h3>\';\n  back.sort().forEach(function (src) {\n    var a = document.createElement(\'a\');\n    a.textContent = nodeById[src].title + \' — \' + src;\n    a.addEventListener(\'click\', function () { select(src); });\n    bl.appendChild(a);\n  });\n}\n\nfunction select(id) {\n  cy.elements().unselect();\n  var el = cy.getElementById(id);\n  el.select();\n  cy.animate({ center: { eles: el }, duration: 200 });\n  show(id);\n}\n\ncy.on(\'tap\', \'node\', function (ev) { show(ev.target.id()); });\n</script>\n</body>\n</html>\n'
TEMPLATE = TEMPLATE.replace("\\\\\\\\\"", "\\\\\"").replace("/\\\\.md$", "/\\.md$")


def opt(args, flag, default):
    try:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    except ValueError:
        pass
    return default


def main(argv):
    bundle = argv[0] if argv else None
    if not bundle or not os.path.isdir(bundle):
        sys.stderr.write("usage: viz.py <bundle-dir> [--out <path>] [--name <display name>]\n")
        return 2
    name = opt(argv, "--name", os.path.basename(os.path.realpath(bundle)))
    out = opt(argv, "--out", os.path.join(bundle, "viz.html"))
    graph = build_graph(bundle)
    html = render(name, graph)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {out} — {len(graph['nodes'])} concepts, {len(graph['edges'])} edges, {len(html)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
