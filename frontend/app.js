// ---------------- Helpers ----------------
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };

async function api(path, opts) {
  const r = await fetch(path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}
function fmtDate(iso, opts = { day: "2-digit", month: "short" }) {
  return new Date(iso + "T00:00:00").toLocaleDateString("fr-FR", opts);
}
function hms(min) { return min >= 60 ? `${Math.floor(min / 60)}h${String(min % 60).padStart(2, "0")}` : `${min} min`; }
const SPORT_LABEL = { run: "Course", bike: "Vélo", swim: "Natation", strength: "Renfo / Burn", brick: "Brick", rest: "Repos", mobility: "Mobilité" };
const SPORT_COLOR = { run: "#34d399", bike: "#fbbf24", swim: "#38bdf8", strength: "#c084fc", brick: "#fb7185", rest: "#5d6878", mobility: "#8b97a8" };

// ---------------- State cache ----------------
const cache = {};
async function getOverview() { return cache.overview ??= await api("/api/overview"); }
async function getCoaching() { return cache.coaching ??= await api("/api/coaching"); }
async function getGamification() { return cache.gam ??= await api("/api/gamification"); }
let currentMonday = null;

// ---------------- Progress ring ----------------
function ring(pct, label, sub, color = "#22d3ee") {
  const R = 50, C = 2 * Math.PI * R, off = C * (1 - pct / 100);
  return `<div class="ring"><svg viewBox="0 0 116 116" width="116" height="116">
    <circle cx="58" cy="58" r="${R}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="9"/>
    <circle cx="58" cy="58" r="${R}" fill="none" stroke="${color}" stroke-width="9" stroke-linecap="round"
      stroke-dasharray="${C}" stroke-dashoffset="${off}"/>
  </svg><div class="ring-label"><b>${label}</b><span>${sub}</span></div></div>`;
}

// ---------------- Topbar ----------------
async function topbar(route) {
  const titles = {
    overview: ["Vue d'ensemble", "Ta progression vers le 20km et le 70.3"],
    plan: ["Mon plan", "Périodisation sur 12 mois, phase par phase"],
    week: ["Cette semaine", "Tes séances, à cocher au fil de l'eau"],
    load: ["Charge d'entraînement", "Ce que tu as réellement fait (Garmin)"],
    defis: ["Défis", "Ton niveau, ta série et tes badges"],
    coaching: ["Conseils", "Méthode et stratégie de course"],
  };
  const [t, s] = titles[route] || titles.overview;
  $("#page-title").textContent = t;
  $("#page-sub").textContent = s;
  const o = await getOverview();
  const g = o.goals;
  $("#topbar-chips").innerHTML = `
    <div class="chip">🏃 20km <b>J-${g.race_20km.days_left}</b></div>
    <div class="chip">🏊🚴🏃 70.3 <b>J-${g.race_703.days_left}</b></div>`;
}

// ---------------- Garmin mini (sidebar) ----------------
async function renderGarminMini() {
  const o = await getOverview();
  const gm = o.garmin;
  const node = $("#garmin-mini");
  node.innerHTML = `
    <div class="gm-row"><span><span class="dot ${gm.configured ? "on" : "off"}"></span>Garmin</span>
      <span class="muted">${gm.last_sync ? "à jour" : "non lié"}</span></div>
    <button class="btn full" id="sync-btn">Synchroniser</button>
    <div class="small muted" id="sync-msg" style="margin-top:8px"></div>`;
  $("#sync-btn").onclick = doSync;
}
async function doSync() {
  const btn = $("#sync-btn"), msg = $("#sync-msg");
  btn.disabled = true; msg.textContent = "Connexion à Garmin…";
  try {
    const r = await api("/api/sync", { method: "POST" });
    msg.textContent = `✅ ${r.imported} activités importées.`;
    delete cache.overview; delete cache.gam; await renderGarminMini();
    if (location.hash.includes("load") || location.hash === "" || location.hash.includes("overview")) render();
  } catch (e) { msg.textContent = "⚠️ " + e.message; }
  finally { const b = $("#sync-btn"); if (b) b.disabled = false; }
}

// ---------------- Views ----------------
async function viewOverview() {
  const o = await getOverview();
  const g = o.goals, p = o.paces, pp = o.plan_progress;
  const v = $("#view");

  const card20 = `<div class="card glow"><div class="goal-hero">
    ${ring(100 - Math.round(g.race_20km.days_left / 3.65), "J-" + g.race_20km.days_left, "avant la course", "#34d399")}
    <div class="info">
      <div class="label">🏃 20km de Bruxelles</div>
      <h3>${fmtDate(g.race_20km.date, { day: "2-digit", month: "long", year: "numeric" })}</h3>
      <div class="kv"><span>PR actuel <span class="badge">Garmin</span></span><b>${hms(g.race_20km.current_min)}</b></div>
      <div class="kv"><span>🎯 Objectif <span class="badge cyan">on y va</span></span><b>${hms(g.race_20km.goal_realistic_min)}</b></div>
      <div class="kv"><span>Stretch <span class="badge amber">si ça claque</span></span><b>${hms(g.race_20km.goal_stretch_min)}</b></div>
    </div></div></div>`;

  const card70 = `<div class="card glow"><div class="goal-hero">
    ${ring(100 - Math.round(g.race_703.days_left / 3.71), "J-" + g.race_703.days_left, "avant la course", "#22d3ee")}
    <div class="info">
      <div class="label">🏊🚴🏃 Half-Ironman 70.3</div>
      <h3>${fmtDate(g.race_703.date, { day: "2-digit", month: "long", year: "numeric" })}</h3>
      <div class="kv"><span>Actuel</span><b>${hms(g.race_703.current_min)}</b></div>
      <div class="kv"><span>Objectif <span class="badge green">réaliste</span></span><b>sub-${Math.floor(g.race_703.goal_min / 60)}h</b></div>
      <div class="kv"><span>Gain clé</span><b>Vélo + transitions</b></div>
    </div></div></div>`;

  const z = p.zones;
  const paces = `<div class="card"><h2 class="with-eyebrow">Allures d'entraînement 🎯</h2>
    <div class="eyebrow">Aujourd'hui → objectif · montée progressive (avancement ${p.progress_pct}%)</div>
    <div class="paces">
      ${pchip("Récup / Easy", z.easy)}${pchip("Sortie longue", z.long)}
      ${pchip("Tempo / allure 20km", z.tempo, true)}${pchip("Seuil", z.threshold)}
      ${pchip("VO2max (~5km)", z.vo2)}
    </div>
    <p class="small muted" style="margin:14px 0 0">${p.from_garmin ? `Ancrées sur tes <b>vraies allures Garmin</b> (Z2 réelle ${p.measured_easy})` : "Basées sur ton niveau actuel"} et montant <b>crescendo</b> vers tes allures objectif <b>1h05</b>. Le grand chiffre = ce que tu vises <b>maintenant</b>, la petite ligne = la cible 1h05.</p></div>`;

  const progress = `<div class="card"><h2 class="with-eyebrow">Avancement du plan</h2>
    <div class="eyebrow">${fmtDate(pp.start)} → ${fmtDate(pp.end)}</div>
    <div class="progress-track"><div class="progress-fill" style="width:${pp.pct}%"></div></div>
    <div style="display:flex;justify-content:space-between" class="small muted">
      <span>Semaine ${pp.elapsed_weeks} / ${pp.total_weeks}</span><span>${pp.pct}%</span></div></div>`;

  const gam = await getGamification();
  const gamStrip = `<div class="card glow gamebar">
    <div class="lvl"><div class="lvl-badge">Niv.<b>${gam.level}</b></div></div>
    <div class="gb-main">
      <div class="gb-top"><span><b>${gam.xp.toLocaleString("fr-FR")}</b> XP</span>
        <span class="muted small">${gam.xp_into_level}/${gam.xp_for_next} vers niv. ${gam.level + 1}</span></div>
      <div class="progress-track" style="margin:8px 0 0"><div class="progress-fill" style="width:${gam.level_progress_pct}%"></div></div>
    </div>
    <div class="gb-stat"><div class="gb-flame">🔥 ${gam.streak_weeks}</div><span class="muted small">sem. d'affilée</span></div>
    <div class="gb-stat"><div class="gb-flame">🏆 ${gam.badges_earned}/${gam.badges_total}</div><span class="muted small">badges</span></div>
  </div>`;

  v.innerHTML = `
    ${gamStrip}
    <div style="height:16px"></div>
    <div class="grid cols-2">${card20}${card70}</div>
    <div style="height:16px"></div>${progress}
    <div style="height:16px"></div>${paces}`;
}

async function viewDefis() {
  const gam = await getGamification();
  const grid = gam.badges.map((b) => `
    <div class="card badge-card ${b.earned ? "earned" : "locked"}">
      <div class="b-ico">${b.icon}</div>
      <div class="b-info"><h3>${b.title}</h3><p class="muted small">${b.desc}</p>
        ${b.earned ? '<span class="badge green">obtenu ✓</span>'
          : `<div class="progress-track" style="margin-top:8px"><div class="progress-fill" style="width:${b.progress * 100}%"></div></div>
             <span class="faint small">${Math.round(b.progress * 100)}%</span>`}
      </div></div>`).join("");

  $("#view").innerHTML = `
    <div class="card glow gamebar">
      <div class="lvl"><div class="lvl-badge">Niv.<b>${gam.level}</b></div></div>
      <div class="gb-main"><div class="gb-top"><span><b>${gam.xp.toLocaleString("fr-FR")}</b> XP</span>
        <span class="muted small">plus que ${gam.xp_for_next - gam.xp_into_level} XP pour le niveau ${gam.level + 1}</span></div>
        <div class="progress-track" style="margin:8px 0 0"><div class="progress-fill" style="width:${gam.level_progress_pct}%"></div></div></div>
      <div class="gb-stat"><div class="gb-flame">🔥 ${gam.streak_weeks}</div><span class="muted small">semaines</span></div>
    </div>
    <div class="section-title">Badges — ${gam.badges_earned}/${gam.badges_total} obtenus</div>
    <div class="grid cols-3">${grid}</div>
    <p class="small muted" style="margin-top:14px">Tu gagnes de l'XP à chaque sortie (durée + distance + dénivelé). Reste régulier pour faire grimper ta série 🔥 et débloquer les badges.</p>`;
}
function pchip(k, z, hl) { return `<div class="pace-chip ${hl ? "hl" : ""}"><span class="k">${k}</span><span class="v">${z.now}</span><span class="pgoal">→ ${z.goal}</span></div>`; }

async function viewPlan() {
  const c = await getCoaching();
  const o = await getOverview();
  const phases = ["base", "build", "specific", "peak"];
  const meta = {
    base: { name: "Base aérobie", color: "#22d3ee" }, build: { name: "Force & hiver", color: "#c084fc" },
    specific: { name: "Spécifique", color: "#fb7185" }, peak: { name: "Affûtage", color: "#fbbf24" },
  };
  // phase courante approximée par avancement
  const pct = o.plan_progress.pct;
  const activeIdx = pct < 34 ? 0 : pct < 64 ? 1 : pct < 90 ? 2 : 3;

  const timeline = `<div class="timeline">${phases.map((k, i) => `
    <div class="tl-seg ${i === activeIdx ? "active" : ""}"><div class="bar" style="background:${meta[k].color}"></div>
      <div class="ph">${meta[k].name}</div><div class="pd">${c.phase_guides[k].subtitle.split("—")[1]?.trim() || ""}</div></div>`).join("")}</div>`;

  const guides = phases.map((k) => {
    const gp = c.phase_guides[k];
    return `<div class="card guide" style="border-left:4px solid ${meta[k].color}">
      <h3>${gp.subtitle.split("—")[0].trim()}</h3>
      <div class="sub" style="color:${meta[k].color}">${gp.subtitle.split("—")[1]?.trim() || ""}</div>
      <p>${gp.summary}</p>
      <div class="block-title">Objectifs</div><ul>${gp.objectives.map((x) => `<li>${x}</li>`).join("")}</ul>
      <div class="block-title">Séances clés</div><div class="tag-row">${gp.key_sessions.map((x) => `<span class="tag">${x}</span>`).join("")}</div>
      <div class="block-title">Points de vigilance</div><ul class="watch">${gp.watch_outs.map((x) => `<li>${x}</li>`).join("")}</ul>
      <div class="block-title">À suivre</div><div class="tag-row">${gp.metrics.map((x) => `<span class="tag">📊 ${x}</span>`).join("")}</div>
    </div>`;
  }).join("");

  $("#view").innerHTML = `<div class="card">${timeline}</div>
    <div class="section-title">Les 4 phases en détail</div>
    <div class="grid cols-2">${guides}</div>`;
}

async function viewWeek(dateIso) {
  const q = dateIso ? `?d=${dateIso}` : "";
  const wk = await api("/api/week" + q);
  currentMonday = wk.monday;
  weekData = wk;
  const today = new Date().toISOString().slice(0, 10);

  const ph = wk.phase;
  const days = wk.days.map((day) => {
    const sess = day.sessions.filter((s) => s.sport !== "rest" && s.sport !== "mobility").length
      ? day.sessions.map((s, i) => sessCard(day.date, i, s)).join("")
      : day.sessions.map((s, i) => sessCard(day.date, i, s)).join("") || `<div class="rest">Repos</div>`;
    return `<div class="day ${day.date === today ? "today" : ""}">
      <div class="dh"><span class="wd">${day.weekday}</span><span class="dt">${fmtDate(day.date)}</span></div>
      ${sess}</div>`;
  }).join("");

  $("#view").innerHTML = `
    <div class="week-head">
      <div class="week-nav">
        <button class="iconbtn" id="prev-week">◀</button>
        <span id="week-label">Sem. du ${fmtDate(wk.monday)}</span>
        <button class="iconbtn" id="next-week">▶</button>
      </div>
      <div class="chip">Volume planifié <b>${wk.total_hours}h</b></div>
    </div>
    <div class="phase-banner" style="border-left-color:${ph.color}">
      <div class="pb-top"><b style="color:${ph.color}">${ph.phase_label || ph.name}</b>
        ${wk.deload ? '<span class="deload">· semaine d\'allègement</span>' : ""}</div>
      <p class="small muted" style="margin:6px 0 0">${ph.focus}</p>
    </div>
    <div class="week-grid">${days}</div>`;

  $("#prev-week").onclick = () => shiftWeek(-7);
  $("#next-week").onclick = () => shiftWeek(7);
  $$(".sess").forEach((s) => s.onclick = () => openDrawer(s.dataset.date, +s.dataset.idx));
}
let weekData = null;

function sessCard(planDate, idx, s) {
  if (s.sport === "rest") return `<div class="rest">😴 ${s.title}</div>`;
  const icon = { planned: "", done: "✅", skipped: "⛔️" }[s.status] || "";
  return `<div class="sess ${s.sport} ${s.status}" data-date="${planDate}" data-idx="${idx}">
    <div class="top"><span class="st">${s.emoji} ${s.title}</span><span class="stat">${icon}</span></div>
    <div class="sm">${s.duration_min ? s.duration_min + " min · " : ""}${s.zone}</div></div>`;
}

// ---------------- Drawer ----------------
function openDrawer(planDate, idx) {
  const day = weekData.days.find((d) => d.date === planDate);
  const s = day.sessions[idx];
  const color = SPORT_COLOR[s.sport] || "#8b97a8";
  const d = $("#drawer");
  d.innerHTML = `
    <button class="dr-close" id="dr-close">✕</button>
    <span class="dr-sport" style="background:${color}22;color:${color}">${s.emoji} ${SPORT_LABEL[s.sport] || s.sport}</span>
    <h2>${s.title}</h2>
    <div class="muted small">${day.weekday} ${fmtDate(planDate)}</div>
    <div class="dr-meta">
      ${s.duration_min ? `<div class="m"><div class="k">Durée</div><div class="v">${s.duration_min} min</div></div>` : ""}
      <div class="m"><div class="k">Intensité</div><div class="v">${s.zone}</div></div>
    </div>
    <div class="block-title" style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);font-weight:800;margin-bottom:8px">Consigne</div>
    <div class="dr-desc">${s.description}</div>
    <div class="dr-actions">
      <button class="btn ok ${s.status === "done" ? "sel" : "ghost"}" data-st="done">✅ Fait</button>
      <button class="btn bad ${s.status === "skipped" ? "sel" : "ghost"}" data-st="skipped">⛔️ Sauté</button>
      <button class="btn ghost ${s.status === "planned" ? "sel" : ""}" data-st="planned">↩︎ À faire</button>
    </div>`;
  $("#dr-close").onclick = closeDrawer;
  $$(".dr-actions .btn", d).forEach((b) => b.onclick = async () => {
    await api("/api/session-status", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_date: planDate, slug: s.slug, status: b.dataset.st }),
    });
    closeDrawer(); await viewWeek(currentMonday);
  });
  d.classList.add("open"); $("#drawer-backdrop").classList.add("open");
}
function closeDrawer() { $("#drawer").classList.remove("open"); $("#drawer-backdrop").classList.remove("open"); }
$("#drawer-backdrop").onclick = closeDrawer;

function shiftWeek(delta) {
  const d = new Date(currentMonday + "T00:00:00"); d.setDate(d.getDate() + delta);
  viewWeek(d.toISOString().slice(0, 10));
}

async function viewLoad() {
  const o = await getOverview();
  const be = o.best_efforts;
  const hasEfforts = Object.keys(be).length > 0;
  const effortCards = ["run", "bike", "swim"].map((sp) => {
    const e = be[sp]; const ico = { run: "🏃", bike: "🚴", swim: "🏊" }[sp];
    return `<div class="card effort"><div class="sport-ico">${ico}</div>
      <div class="muted small">${SPORT_LABEL[sp]}</div>
      <div class="v" style="color:${SPORT_COLOR[sp]}">${e ? e.pace : "—"}</div>
      <div class="small muted">${e ? `${e.distance_km} km · ${fmtDate(e.date)}` : "pas encore de donnée"}</div></div>`;
  }).join("");

  $("#view").innerHTML = `
    <div class="card"><h2>Charge des 12 dernières semaines</h2>
      <canvas id="loadChart" height="120"></canvas>
      <p class="small muted" style="margin:14px 0 0">Minutes par sport. Synchronise Garmin pour remplir ce graphe.</p></div>
    <div class="section-title">Meilleures allures récentes</div>
    <div class="grid cols-3">${effortCards}</div>
    ${hasEfforts ? "" : '<p class="empty">Connecte Garmin et synchronise pour voir tes meilleures allures et ta charge réelle.</p>'}`;

  const { weekly } = await api("/api/load?weeks=12");
  const sports = ["run", "bike", "swim", "strength"];
  const datasets = sports.map((sp) => ({
    label: SPORT_LABEL[sp], backgroundColor: SPORT_COLOR[sp], borderRadius: 4,
    data: weekly.map((w) => w.by_sport_min[sp] || 0),
  }));
  new Chart($("#loadChart"), {
    type: "bar",
    data: { labels: weekly.map((w) => w.label), datasets },
    options: {
      responsive: true,
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color: "#8b97a8" } },
        y: { stacked: true, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#8b97a8" } },
      },
      plugins: { legend: { labels: { color: "#eef2f7", usePointStyle: true, pointStyle: "rectRounded" } } },
    },
  });
}

async function viewCoaching() {
  const c = await getCoaching();
  const ICONS = {
    polarized: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    progressive: '<path d="M3 17 9 11l4 4 8-8"/><path d="M21 7v6h-6"/>',
    specificity: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="0.5" fill="currentColor"/>',
    recovery: '<path d="M12 21a9 9 0 1 1 9-9"/><path d="M12 7v5l3 2"/>',
    consistency: '<path d="M20 6 9 17l-5-5"/>',
    strength: '<path d="M6 7v10M18 7v10M3 9v6M21 9v6M6 12h12"/>',
  };
  const principles = c.principles.map((p) => `<div class="card principle">
    <div class="pic"><svg viewBox="0 0 24 24">${ICONS[p.icon] || ICONS.consistency}</svg></div>
    <div><h3>${p.title}</h3><p>${p.body}</p></div></div>`).join("");

  const strat = (s) => `<div class="card strat">
    <h2 class="with-eyebrow">${s.title}</h2><div class="goal-line">${s.goal_line}</div>
    <div class="block-title">Gestion de l'allure</div><ol>${s.pacing.map((x) => `<li>${x}</li>`).join("")}</ol>
    <div class="block-title">Avant la course</div><ul class="plain">${s.pre_race.map((x) => `<li>${x}</li>`).join("")}</ul>
    <div class="block-title">Mental</div><div class="mental">${s.mental}</div></div>`;

  $("#view").innerHTML = `
    <div class="section-title" style="margin-top:8px">Principes d'entraînement</div>
    <div class="grid cols-2">${principles}</div>
    <div class="section-title">Stratégies de course</div>
    <div class="grid cols-2">${strat(c.race_strategies["20km"])}${strat(c.race_strategies["703"])}</div>`;
}

// ---------------- Router ----------------
const ROUTES = { overview: viewOverview, plan: viewPlan, week: () => viewWeek(currentMonday), load: viewLoad, defis: viewDefis, coaching: viewCoaching };
async function render() {
  closeDrawer();
  const route = (location.hash.replace("#/", "") || "overview");
  const fn = ROUTES[route] || viewOverview;
  $$("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.route === route));
  $("#view").innerHTML = '<div class="loading">Chargement…</div>';
  try { await topbar(route); await fn(); }
  catch (e) { $("#view").innerHTML = `<div class="errbar">⚠️ ${e.message}</div>`; }
}
window.addEventListener("hashchange", render);

(async () => {
  await renderGarminMini().catch(() => {});
  await render();
})();
