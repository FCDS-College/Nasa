// Builds one self-contained HTML file per front-end screen for import into Figma (HTML-to-design plugins).
// Usage:  node docs/design/figma-html/build.mjs        -> writes dist/NN-name.html
// Each screen = shared shell (sidebar + top bar) + content/NN-name.html (a fragment written by hand).
// Icons: write [[icon:Name]], [[icon:Name:16]] or [[icon:Name:16:#3B82F6]] in a fragment (size px, colour optional).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const ICONS = JSON.parse(fs.readFileSync(path.join(here, "icons.json"), "utf8"));

// nav: index of the active sidebar item (-1 = none). history: sidebar shows the sample chat history.
export const SCREENS = [
  { file: "01-dashboard", title: "Fire Safety Dashboard", topbar: "Fire Safety Dashboard", nav: 0 },
  { file: "02-explorer", title: "Flame Outcome Explorer", topbar: "Flame Outcome Explorer", nav: 1 },
  { file: "03-flight-tests", title: "Flight Test Browser", topbar: "Flight Test Browser", nav: 2 },
  { file: "04-chat", title: "Ask the NASA Corpus", topbar: "How does oxygen fraction affect flam...", nav: 3, history: true },
  { file: "05-search", title: "Search Evidence", topbar: "Search Evidence", nav: 4 },
  { file: "06-analysis", title: "Image & Video Analysis", topbar: "Image & Video Analysis", nav: 5 },
  { file: "07-history", title: "Analysis History", topbar: "Analysis History", nav: 6 },
  { file: "08-status", title: "System Status", topbar: "System Status", nav: 7 },
  { file: "09-investigation", title: "Investigation", topbar: "Investigation", nav: -1 },
  { file: "10-evidence", title: "Evidence", topbar: "Evidence", nav: -1 },
  { file: "11-knowledge", title: "Knowledge", topbar: "Knowledge", nav: -1 },
];

const NAV = [
  ["Fire Safety Dashboard", "ShieldCheck"], ["Flame Outcome Explorer", "FlaskConical"], ["Flight Test Browser", "Sparkles"],
  ["Ask the NASA Corpus", "MessageSquare"], ["Search Evidence", "FileSearch"], ["Image & Video Analysis", "Microscope"],
  ["Analysis History", "History"], ["System Status", "Activity"],
];

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const icon = (name, size = 16, color = "currentColor") => {
  const body = ICONS[name];
  if (!body) throw new Error(`Unknown icon: ${name}`);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex:none">${body.replace(/'/g, '"')}</svg>`;
};
const expandIcons = (html) => html.replace(/\[\[icon:(\w+)(?::(\d+))?(?::([^\]]+))?\]\]/g, (_, n, s, c) => icon(n, s ? Number(s) : 16, c || "currentColor"));

const CSS = `
:root{--bg-primary:#0F1115;--bg-card:#171A21;--bg-elevated:#1F232B;--accent-flame:#3B82F6;--accent-ember:#60A5FA;--accent-success:#22C55E;--accent-warning:#F59E0B;--accent-danger:#EF4444;--accent-cyan:#06B6D4;--accent-violet:#A78BFA;
--text-primary:#F3F4F6;--text-secondary:#9CA3AF;--text-muted:#6B7280;--text-dim:#4B5563;--border-subtle:rgba(39,43,51,.5);--border-default:#272B33;
--shadow-card:0 4px 12px rgba(0,0,0,.3);--font-sans:'Inter','Inter Variable',-apple-system,'Segoe UI',sans-serif;--font-mono:'JetBrains Mono','JetBrains Mono Variable',monospace}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{width:1440px;background:var(--bg-primary);color:var(--text-primary);font-family:var(--font-sans);-webkit-font-smoothing:antialiased;font-size:16px;line-height:1.5}
h1,h2,h3,h4,p,ul{margin:0;padding:0}ul{list-style:none}
.app{display:flex;width:1440px;min-height:1024px;background:var(--bg-primary)}
.sidebar{width:300px;flex:none;background:var(--bg-card);border-right:1px solid var(--border-subtle);display:flex;flex-direction:column;min-height:1024px}
.sb-head{height:64px;flex:none;display:flex;align-items:center;padding:0 20px;border-bottom:1px solid var(--border-subtle)}
.sb-logo{display:flex;align-items:center;gap:12px}
.sb-mark{width:36px;height:36px;border-radius:12px;background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.25);display:flex;align-items:center;justify-content:center;color:var(--accent-flame)}
.sb-brand{font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;line-height:1.35}
.sb-tag{font-family:var(--font-mono);font-size:10px;font-weight:500;color:var(--accent-flame);opacity:.8;letter-spacing:.025em}
.sb-nav{padding:12px 12px 0;display:flex;flex-direction:column;gap:2px}
.nav-item{display:flex;align-items:center;gap:10px;border-radius:8px;padding:8px 12px;font-size:12px;font-weight:500;color:var(--text-secondary);border:1px solid transparent}
.nav-item svg{color:var(--text-dim)}
.nav-item.active{background:rgba(59,130,246,.12);border-color:rgba(59,130,246,.25);color:var(--text-primary)}
.nav-item.active svg{color:var(--accent-flame)}
.sb-div{margin:12px 16px 0;border-top:1px solid var(--border-subtle)}
.sb-new{padding:16px 16px 8px}
.btn-new{width:100%;display:flex;align-items:center;justify-content:center;gap:10px;padding:12px 16px;border-radius:12px;font-size:14px;font-weight:600;background:rgba(59,130,246,.16);border:1px solid rgba(59,130,246,.3);color:var(--text-primary);box-shadow:0 0 15px rgba(59,130,246,.1);font-family:inherit}
.btn-new svg{color:var(--accent-flame)}
.sb-search{margin:4px 16px;display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:8px;background:var(--border-subtle);border:1px solid var(--border-subtle);font-size:12px;color:var(--text-muted)}
.sb-hist-h{display:flex;align-items:center;justify-content:space-between;padding:16px 20px 8px}
.sb-hist-l{display:flex;align-items:center;gap:6px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.15em;color:var(--text-muted)}
.sb-count{font-family:var(--font-mono);font-size:9px;background:var(--border-subtle);color:var(--text-secondary);border-radius:999px;padding:2px 6px;margin-left:6px;letter-spacing:0}
.sb-clear{font-size:10px;font-weight:500;color:var(--text-dim)}
.sb-list{flex:1;padding:8px 12px;display:flex;flex-direction:column;gap:2px}
.sb-empty{display:flex;flex-direction:column;align-items:center;text-align:center;padding:64px 16px}
.sb-empty .box{width:56px;height:56px;border-radius:16px;background:rgba(59,130,246,.08);border:1px solid var(--border-subtle);display:flex;align-items:center;justify-content:center;margin-bottom:16px;color:var(--text-dim)}
.sb-empty .t{font-size:12px;font-weight:500;color:var(--text-muted)}.sb-empty .s{font-size:11px;color:var(--text-dim);margin-top:4px}
.sess{display:flex;align-items:center;gap:10px;border-radius:12px;padding:10px 12px;border:1px solid transparent;color:var(--text-secondary)}
.sess svg{color:var(--text-dim)}
.sess.active{background:rgba(59,130,246,.08);border-color:rgba(59,130,246,.2);color:var(--text-primary)}
.sess.active svg{color:var(--accent-flame)}
.sess .st{font-size:12px;font-weight:500;line-height:1.35}.sess .tm{font-family:var(--font-mono);font-size:10px;color:var(--text-dim);margin-top:2px}
.sb-foot{padding:16px;border-top:1px solid var(--border-subtle);background:rgba(0,0,0,.05)}
.sb-foot .card{border-radius:12px;padding:12px;background:var(--border-subtle);border:1px solid var(--border-subtle);font-size:11px}
.sb-foot .r{display:flex;justify-content:space-between;align-items:center}
.sb-foot b{color:var(--text-secondary);font-weight:600}
.sb-foot .yr{font-family:var(--font-mono);font-size:9px;font-weight:600;color:var(--accent-flame);background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.15);border-radius:6px;padding:2px 8px}
.sb-foot p{font-size:10px;color:var(--text-dim);margin-top:6px}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.topbar{height:60px;flex:none;display:flex;align-items:center;justify-content:space-between;padding:0 24px;border-bottom:1px solid var(--border-subtle);background:var(--bg-primary)}
.tb-l{display:flex;align-items:center;gap:12px}
.tb-toggle{width:36px;height:36px;border-radius:8px;background:var(--border-subtle);border:1px solid var(--border-subtle);display:flex;align-items:center;justify-content:center;color:var(--accent-flame)}
.tb-title{font-size:14px;font-weight:600;line-height:1.3}.tb-build{font-family:var(--font-mono);font-size:10px;color:var(--text-dim)}
.tb-r{display:flex;align-items:center;gap:16px}
.pill{display:flex;align-items:center;gap:8px;border-radius:999px;padding:6px 12px;background:var(--border-subtle);border:1px solid var(--border-subtle);font-size:12px;font-weight:600;color:var(--text-secondary)}
.dot{width:8px;height:8px;border-radius:50%;background:rgba(16,185,129,.8);box-shadow:0 0 8px rgba(16,185,129,.8)}
.ver{font-family:var(--font-mono);font-size:11px;color:var(--text-secondary);background:var(--border-subtle);border:1px solid var(--border-subtle);border-radius:999px;padding:4px 10px}
.content{flex:1;display:flex;flex-direction:column}
/* ---- shared building blocks for the page fragments ---- */
.card{background:var(--bg-card);border:1px solid var(--border-default);border-radius:16px;padding:20px;box-shadow:var(--shadow-card)}
.elev{background:var(--bg-elevated);border:1px solid var(--border-default);border-radius:12px;padding:16px}
.badge{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:4px 10px;font-size:11px;font-weight:600;letter-spacing:.025em;background:var(--border-subtle);color:var(--text-secondary);border:1px solid rgba(255,255,255,.1)}
.badge.success{background:rgba(34,197,94,.1);color:var(--accent-success);border-color:rgba(34,197,94,.25)}
.badge.warning{background:rgba(245,158,11,.1);color:var(--accent-warning);border-color:rgba(245,158,11,.25)}
.badge.danger{background:rgba(239,68,68,.1);color:var(--accent-danger);border-color:rgba(239,68,68,.25)}
.badge.flame{background:rgba(59,130,246,.12);color:var(--accent-flame);border-color:rgba(59,130,246,.25)}
.badge.ember{background:rgba(96,165,250,.1);color:var(--accent-ember);border-color:rgba(96,165,250,.25)}
.kind{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:2px 8px;font-size:11px;font-weight:600}
.kind.measured{color:#22C55E;background:rgba(34,197,94,.1);border:1px solid #22C55E33}
.kind.model{color:#60A5FA;background:rgba(96,165,250,.1);border:1px solid #60A5FA33}
.kind.gap{color:#F59E0B;background:rgba(245,158,11,.1);border:1px solid #F59E0B33}
.btn{display:inline-flex;align-items:center;gap:6px;border-radius:8px;padding:6px 12px;font-size:12px;font-weight:600;font-family:inherit;background:var(--accent-flame);color:#fff;border:0}
.btn.secondary{background:var(--bg-elevated);color:var(--text-primary);border:1px solid var(--border-default)}
.chip{display:inline-flex;align-items:center;gap:4px;border-radius:6px;padding:2px 6px;font-family:var(--font-mono);font-size:11px;background:var(--bg-elevated);border:1px solid var(--border-default);color:var(--accent-ember)}
.metric{background:var(--bg-card);border:1px solid var(--border-default);border-radius:12px;padding:20px;box-shadow:var(--shadow-card)}
.metric .l{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.12em;color:var(--text-muted)}
.metric .v{font-size:30px;font-weight:700;line-height:1.2;margin-top:8px;color:var(--accent-flame)}
.metric .d{font-size:12px;color:var(--text-dim);margin-top:6px}
.state{border-radius:12px;padding:20px;background:var(--border-subtle);border:1px solid var(--border-default)}
.state h3{font-size:14px;font-weight:600}.state p{font-size:14px;color:var(--text-muted);margin-top:8px;line-height:1.6}
.state.success{background:rgba(34,197,94,.04);border-color:rgba(34,197,94,.15)}
.state.warning{background:rgba(245,158,11,.04);border-color:rgba(245,158,11,.15)}
.state.error{background:rgba(239,68,68,.04);border-color:rgba(239,68,68,.15)}
.eyebrow{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.12em;color:var(--text-muted)}
.mono{font-family:var(--font-mono)}
.row{display:flex;align-items:center}.col{display:flex;flex-direction:column}.wrap{flex-wrap:wrap}.between{justify-content:space-between}.grow{flex:1;min-width:0}
.input{background:var(--bg-elevated);border:1px solid var(--border-default);border-radius:8px;padding:6px 8px;color:var(--text-primary);font-size:12px;font-family:inherit}
`;

const sidebar = (s) => {
  const nav = NAV.map(([label, ic], i) => `<li><div class="nav-item${i === s.nav ? " active" : ""}">${icon(ic, 16)}${esc(label)}</div></li>`).join("");
  const sessions = [["How does oxygen fraction affect flam...", "2m ago", true], ["Summarize NASA FLEX droplet findings", "1h ago", false], ["What is the SoFIE flight test rig?", "Yesterday", false]];
  const list = s.history
    ? sessions.map(([t, tm, a]) => `<div class="sess${a ? " active" : ""}">${icon("MessageSquare", 16)}<div><div class="st">${esc(t)}</div><div class="tm">${tm}</div></div></div>`).join("")
    : `<div class="sb-empty"><div class="box">${icon("Sparkles", 28)}</div><div class="t">No conversations yet</div><div class="s">Start a new research chat</div></div>`;
  return `<aside class="sidebar">
<div class="sb-head"><div class="sb-logo"><div class="sb-mark">${icon("Flame", 20)}</div><div><div class="sb-brand">Flame in Freefall</div><div class="sb-tag">Fire-Safety Insights</div></div></div></div>
<nav class="sb-nav"><ul style="display:flex;flex-direction:column;gap:2px">${nav}</ul></nav><div class="sb-div"></div>
<div class="sb-new"><div class="btn-new">${icon("Plus", 16)}<span>New Research Chat</span></div></div>
${s.history ? `<div class="sb-search">${icon("Search", 14)}Search history...</div>` : ""}
<div class="sb-hist-h"><div class="sb-hist-l">${icon("Clock", 14)}<span>Chat History</span><span class="sb-count">${s.history ? 3 : 0}</span></div>${s.history ? '<span class="sb-clear">Clear all</span>' : ""}</div>
<div class="sb-list">${list}</div>
<div class="sb-foot"><div class="card"><div class="r"><b>NASA Space Apps</b><span class="yr">2026</span></div><p>NASA PSI flight data · NTRS reports</p></div></div>
</aside>`;
};
const topbar = (s) => `<header class="topbar"><div class="tb-l"><div class="tb-toggle">${icon("PanelLeft", 16)}</div><div><div class="tb-title">${esc(s.topbar)}</div><div class="tb-build">Build: build-7f8a9b</div></div></div>
<div class="tb-r"><div class="pill"><span class="dot"></span>${icon("Activity", 14, "#22C55E")}OK</div><div class="ver">v1.0.0-MVP</div></div></header>`;

export function build() {
  fs.mkdirSync(path.join(here, "dist"), { recursive: true });
  const out = [];
  for (const s of SCREENS) {
    const src = path.join(here, "content", `${s.file}.html`);
    if (!fs.existsSync(src)) { out.push(`MISSING ${s.file}`); continue; }
    const frag = expandIcons(fs.readFileSync(src, "utf8"));
    const html = `<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>${esc(s.title)} — Flame in Freefall</title><meta name="viewport" content="width=1440"><style>${CSS}</style></head>\n<body><div class="app">${sidebar(s)}<div class="main">${topbar(s)}<main class="content">\n${frag}\n</main></div></div></body></html>\n`;
    fs.writeFileSync(path.join(here, "dist", `${s.file}.html`), html);
    out.push(`built ${s.file}`);
  }
  // One index page linking to (and previewing) every screen. Open docs/design/figma-html/index.html
  const cards = SCREENS.filter((s) => fs.existsSync(path.join(here, "dist", `${s.file}.html`))).map((s) => {
    const n = s.file.slice(0, 2);
    return `<a class="c" href="dist/${s.file}.html" target="_blank"><div class="t"><iframe src="dist/${s.file}.html" tabindex="-1" loading="lazy"></iframe></div><div class="m"><span class="n">${n}</span><span>${esc(s.title)}</span></div></a>`;
  }).join("");
  const index = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Flame in Freefall — all screens</title><style>
body{margin:0;background:#0F1115;color:#F3F4F6;font-family:Inter,'Segoe UI',sans-serif}header{padding:32px 40px 8px}h1{margin:0;font-size:24px}p{margin:6px 0 0;color:#9CA3AF;font-size:14px}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:24px;padding:24px 40px 48px}
.c{display:block;text-decoration:none;color:inherit;background:#171A21;border:1px solid #272B33;border-radius:16px;overflow:hidden}.c:hover{border-color:rgba(59,130,246,.55)}
.t{height:300px;overflow:hidden;position:relative;background:#0F1115}.t iframe{width:1440px;height:1070px;border:0;transform:scale(.29);transform-origin:0 0;pointer-events:none}
.m{display:flex;gap:12px;align-items:center;padding:14px 16px;border-top:1px solid #272B33;font-weight:600;font-size:14px}.n{font-family:'JetBrains Mono',monospace;font-size:11px;color:#3B82F6;background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.25);border-radius:6px;padding:2px 8px}
</style></head><body><header><h1>Flame in Freefall — all screens (${SCREENS.length})</h1><p>Click a screen to open it full size (1440px). Each file in dist/ can be imported into Figma with an HTML-to-design plugin.</p></header><div class="g">${cards}</div></body></html>\n`;
  fs.writeFileSync(path.join(here, "index.html"), index);
  out.push("built index.html");
  return out;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) console.log(build().join("\n"));
