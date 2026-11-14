"""Render the catalog as Markdown (the sidebar's native preview path)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LIMIT = 800

with open(os.path.join(HERE, "plugins.json"), encoding="utf-8") as f:
    d = json.load(f)

cats = {c["id"]: (c.get("zh") or c.get("en") or c["id"]) for c in d["categories"]}
rows = sorted(d["plugins"], key=lambda r: (-r["installs"], -r["stars"]))[:LIMIT]

out = []
out.append("# DSH 插件目录（本地快照）\n")
out.append(
    f"> 共 {d['total']} 条，这里按安装数取前 {LIMIT} 条；"
    f"上游共 {d['upstreamTotal']:,} 条（已抓 {d['pagesFetched']}/{d['pagesTotal']} 页）。\n"
)
out.append(
    "> 完整数据见 `plugins.json`；可交互版本是 `index.html`，"
    "**用系统浏览器双击打开**（侧栏预览当前打不开 HTML）。\n"
)
out.append("> 安装时把命令里的 `--profile web` 改成 `--profile desktop`。\n")
out.append("\n---\n")

current = None
for r in rows:
    cat = cats.get(r["category"], r["category"] or "未分类")
    if cat != current:
        current = cat
        out.append(f"\n## {cat}\n")
    desc = (r["zh"] or r["en"] or "").replace("\n", " ").strip()
    if len(desc) > 110:
        desc = desc[:110] + "…"
    line = f"- **{r['name']}** <sub>{r['owner']}</sub>"
    if desc:
        line += f" —— {desc}"
    line += f"\n  <sub>★ {r['stars']:,} · 安装 {r['installs']:,} · 更新 {r['pushed'] or '-'}</sub>"
    link = f"\n  [`{r['install']}`](<{r['url']}>)" if r["url"] else f"\n  `{r['install']}`"
    out.append(line + link + "\n")

path = os.path.join(HERE, "catalog.md")
with open(path, "w", encoding="utf-8") as f:
    f.write("".join(out))
print("markdown entries:", len(rows), "size:", os.path.getsize(path) // 1024, "KB")
