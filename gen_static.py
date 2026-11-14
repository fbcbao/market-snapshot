"""Render a script-free static HTML list (fallback + preview diagnostic)."""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "plugins.json"), encoding="utf-8") as f:
    d = json.load(f)

rows = sorted(d["plugins"], key=lambda r: (-r["installs"], -r["stars"]))
cats = {c["id"]: (c.get("zh") or c.get("en") or c["id"]) for c in d["categories"]}

items = []
for r in rows:
    desc = html.escape(r["zh"] or r["en"] or "")
    items.append(
        "<li>"
        f'<b>{html.escape(r["name"])}</b> '
        f'<span class="o">{html.escape(r["owner"])}</span> '
        f'<span class="c">{html.escape(cats.get(r["category"], r["category"]))}</span><br>'
        f'<span class="d">{desc}</span><br>'
        f'<span class="m">★ {r["stars"]:,} · 安装 {r["installs"]:,} · 更新 {html.escape(r["pushed"] or "-")}</span><br>'
        f'<code>{html.escape(r["install"])}</code>'
        "</li>"
    )

page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>DSH 插件目录 · 静态版</title>
<style>
body{{margin:0;padding:20px;background:#fff;color:#111;font:14px/1.6 "Microsoft YaHei",sans-serif}}
h1{{font-size:18px;margin:0 0 4px}}
p.sub{{color:#666;margin:0 0 16px;font-size:12px}}
ul{{list-style:none;padding:0;margin:0}}
li{{border-bottom:1px solid #e5e7eb;padding:10px 0}}
.o{{color:#666;font-size:12px;margin-left:6px}}
.c{{background:#eef2ff;color:#3b6ef6;border-radius:9px;padding:0 8px;font-size:11px;margin-left:6px}}
.d{{color:#333}}
.m{{color:#777;font-size:12px}}
code{{background:#f3f4f6;border-radius:5px;padding:1px 5px;font-size:12px;word-break:break-all}}
</style></head>
<body style="background:#fff;color:#111">
<h1>DSH 插件目录 · 静态版（不依赖 JavaScript）</h1>
<p class="sub">共 {len(rows)} 条 · 快照 {d['pagesFetched']}/{d['pagesTotal']} 页 · 按安装数排序</p>
<ul>
{''.join(items)}
</ul>
</body></html>
"""

out = os.path.join(HERE, "index-static.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(page)
print("static rows:", len(rows), "size:", os.path.getsize(out) // 1024, "KB")
