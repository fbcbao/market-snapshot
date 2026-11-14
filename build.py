"""Turn raw catalog pages into a normalized dataset + an offline HTML browser."""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")


def load_pages():
    pages = []
    for p in sorted(glob.glob(os.path.join(RAW, "page-*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                pages.append(json.load(f))
        except Exception as e:  # noqa: BLE001
            print(f"skip {os.path.basename(p)}: {e}", file=sys.stderr)
    return pages


def is_npm_target(install):
    if not isinstance(install, str):
        return False
    parts = install.split()
    if len(parts) < 5 or parts[:3] != ["dsh", "plugin", "--profile"]:
        return False
    target = parts[-1]
    if target.startswith(("github:", "git+", "http:", "https:", "file:", "link:")):
        return False
    return "@" not in target or not target.startswith("@")


def normalize(pages):
    meta = pages[0] if pages else {}
    seen = {}
    for page in pages:
        for it in page.get("plugins") or []:
            key = it.get("id") or f"{it.get('owner')}/{it.get('name')}"
            desc = it.get("description") or {}
            if isinstance(desc, str):
                desc = {"en": desc, "zh": desc}
            row = {
                "id": key,
                "name": it.get("name") or "",
                "owner": it.get("owner") or "",
                "url": it.get("url") or "",
                "category": it.get("category") or "",
                "zh": (desc.get("zh") or "").strip(),
                "en": (desc.get("en") or "").strip(),
                "install": it.get("install") or "",
                "stars": it.get("stars") or 0,
                "installs": it.get("installCount") or 0,
                "installs7d": it.get("installs7d") or 0,
                "pushed": (it.get("pushedAt") or "")[:10],
                "added": it.get("added") or "",
                "npm": is_npm_target(it.get("install")),
            }
            prev = seen.get(key)
            if prev is None or row["installs"] > prev["installs"]:
                seen[key] = row
    return meta, sorted(seen.values(), key=lambda r: (-r["installs"], -r["stars"]))


def main():
    pages = load_pages()
    if not pages:
        print("no raw pages", file=sys.stderr)
        return 1
    meta, rows = normalize(pages)
    cats = meta.get("categories") or []
    payload = {
        "generatedAt": meta.get("generatedAt"),
        "source": "https://deepseek1024.com/api/v2/plugins",
        "total": len(rows),
        "pagesFetched": len(pages),
        "pagesTotal": meta.get("totalPages"),
        "upstreamTotal": meta.get("total"),
        "categories": cats,
        "plugins": rows,
    }
    with open(os.path.join(HERE, "plugins.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    js = "window.DSH_MARKET=" + json.dumps(payload, ensure_ascii=False).replace("</", "<\\/") + ";"
    with open(os.path.join(HERE, "data.js"), "w", encoding="utf-8") as f:
        f.write(js)
    page = HTML.replace('<script src="data.js"></script>', "<script>" + js + "</script>")
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    npm = sum(1 for r in rows if r["npm"])
    print(f"plugins={len(rows)} npm_installable={npm} categories={len(cats)}")
    return 0


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSH 社区插件目录 · 本地快照</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--fg:#1b1f24;--muted:#5b6672;--line:#e3e6ea;--accent:#3b6ef6;--chip:#eef2ff}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1c2027;--fg:#e8ebef;--muted:#98a2ae;--line:#2b313a;--accent:#7aa2ff;--chip:#232a36}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 20px;z-index:5}
h1{margin:0 0 4px;font-size:17px}
.sub{color:var(--muted);font-size:12px}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:center}
input[type=search],select{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:7px 10px;font:inherit}
input[type=search]{flex:1 1 260px;min-width:200px}
label.toggle{display:flex;gap:6px;align-items:center;color:var(--muted);font-size:13px;user-select:none}
main{padding:14px 20px 60px;max-width:1180px;margin:0 auto}
.row{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px}
.row h3{margin:0 0 2px;font-size:15px;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.owner{color:var(--muted);font-weight:400;font-size:12px}
.desc{margin:6px 0 8px;color:var(--fg);opacity:.9}
.meta{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:12px;align-items:center}
.chip{background:var(--chip);color:var(--accent);border-radius:999px;padding:1px 9px;font-size:11px}
.chip.gray{background:transparent;border:1px solid var(--line);color:var(--muted)}
.actions{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
button{background:var(--card);border:1px solid var(--line);color:var(--fg);border-radius:8px;padding:5px 11px;font:inherit;cursor:pointer}
button:hover{border-color:var(--accent);color:var(--accent)}
code{background:var(--chip);border-radius:6px;padding:2px 6px;font-size:12px;word-break:break-all}
.pager{display:flex;gap:8px;align-items:center;justify-content:center;margin:18px 0;color:var(--muted)}
.empty{text-align:center;color:var(--muted);padding:40px 0}
a{color:var(--accent);text-decoration:none}
</style>
</head>
<body>
<noscript><div style="padding:18px;font-family:sans-serif">这个页面需要 JavaScript 才能渲染。<br>
如果你在 DSH 右侧预览区看到空白，请双击 index.html 用浏览器打开。</div></noscript>
<header>
  <h1>DSH 社区插件目录 · 本地快照</h1>
  <div class="sub" id="sub"></div>
  <div class="controls">
    <input type="search" id="q" placeholder="搜索名字 / 作者 / 描述…">
    <select id="cat"><option value="">全部分类</option></select>
    <select id="sort">
      <option value="installs">按安装数</option>
      <option value="stars">按 Star</option>
      <option value="pushed">按最近更新</option>
      <option value="name">按名称</option>
    </select>
    <label class="toggle"><input type="checkbox" id="npmOnly"> 只看可直接安装</label>
  </div>
</header>
<main>
  <div id="list"></div>
  <div class="pager" id="pager"></div>
</main>
<script src="data.js"></script>
<script>
const D = window.DSH_MARKET;
const PAGE = 50;
let state = {q:"", cat:"", sort:"installs", npmOnly:false, page:1};
const $ = s => document.querySelector(s);

const catName = {};
for (const c of D.categories) catName[c.id] = c.zh || c.en || c.id;

const sub = document.getElementById("sub");
sub.textContent = `本地快照 ${D.total.toLocaleString()} 条（已抓 ${D.pagesFetched}/${D.pagesTotal} 页，上游共 ${Number(D.upstreamTotal).toLocaleString()} 条）· 抓取于 ${new Date().toLocaleString()}`;

const catSel = document.getElementById("cat");
for (const c of D.categories) {
  const o = document.createElement("option");
  o.value = c.id; o.textContent = `${c.zh || c.en} (${c.count})`;
  catSel.appendChild(o);
}

function filtered() {
  const q = state.q.trim().toLowerCase();
  let rows = D.plugins;
  if (state.npmOnly) rows = rows.filter(r => r.npm);
  if (state.cat) rows = rows.filter(r => r.category === state.cat);
  if (q) rows = rows.filter(r =>
    r.name.toLowerCase().includes(q) || r.owner.toLowerCase().includes(q) ||
    r.zh.toLowerCase().includes(q) || r.en.toLowerCase().includes(q));
  const s = state.sort;
  rows = [...rows].sort((a, b) =>
    s === "name" ? a.name.localeCompare(b.name)
    : s === "stars" ? b.stars - a.stars
    : s === "pushed" ? (b.pushed || "").localeCompare(a.pushed || "")
    : b.installs - a.installs);
  return rows;
}

function esc(s){return s.replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}

function render() {
  const rows = filtered();
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  state.page = Math.min(state.page, pages);
  const slice = rows.slice((state.page - 1) * PAGE, state.page * PAGE);
  const list = document.getElementById("list");
  if (!slice.length) { list.innerHTML = '<div class="empty">没有匹配的插件</div>'; }
  else {
    list.innerHTML = slice.map(r => `
      <div class="row">
        <h3>${esc(r.name)} <span class="owner">${esc(r.owner)}</span>
          <span class="chip">${esc(catName[r.category] || r.category || "未分类")}</span>
          ${r.npm ? '<span class="chip">npm 可直接装</span>' : '<span class="chip gray">github 源</span>'}
        </h3>
        <div class="desc">${esc(r.zh || r.en || "")}</div>
        <div class="meta">
          <span>★ ${r.stars.toLocaleString()}</span>
          <span>安装 ${r.installs.toLocaleString()}</span>
          <span>近 7 天 ${r.installs7d.toLocaleString()}</span>
          <span>最近推送 ${esc(r.pushed || "-")}</span>
        </div>
        <div class="actions">
          <button data-copy="${esc(r.install)}">复制安装命令</button>
          ${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noreferrer"><button>打开仓库</button></a>` : ""}
        </div>
        ${r.install ? `<div class="meta" style="margin-top:8px"><code>${esc(r.install)}</code></div>` : ""}
      </div>`).join("");
  }
  document.getElementById("pager").innerHTML = rows.length
    ? `<button ${state.page<=1?"disabled":""} id="prev">上一页</button>
       <span>${state.page} / ${pages}　共 ${rows.length.toLocaleString()} 条</span>
       <button ${state.page>=pages?"disabled":""} id="next">下一页</button>` : "";
  const prev = document.getElementById("prev"), next = document.getElementById("next");
  if (prev) prev.onclick = () => { state.page--; render(); scrollTo({top:0}); };
  if (next) next.onclick = () => { state.page++; render(); scrollTo({top:0}); };
}

document.addEventListener("click", async e => {
  const btn = e.target.closest("[data-copy]");
  if (!btn) return;
  try { await navigator.clipboard.writeText(btn.dataset.copy); btn.textContent = "已复制"; }
  catch { btn.textContent = "复制失败"; }
  setTimeout(() => btn.textContent = "复制安装命令", 1200);
});

document.getElementById("q").addEventListener("input", e => { state.q = e.target.value; state.page = 1; render(); });
catSel.addEventListener("change", e => { state.cat = e.target.value; state.page = 1; render(); });
document.getElementById("sort").addEventListener("change", e => { state.sort = e.target.value; state.page = 1; render(); });
document.getElementById("npmOnly").addEventListener("change", e => { state.npmOnly = e.target.checked; state.page = 1; render(); });

render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
