/* Price Analyst — Persian web UI (no build step, no external dependencies).
 *
 * Talks only to same-origin relative URLs (/api/v1/...), which serve.py proxies
 * to the FastAPI backend. All marketplace-provided text is HTML-escaped and only
 * http(s) URLs are rendered as links/images. Currencies are never converted.
 */
"use strict";

const API = "/api/v1";

// ------------------------------------------------------------------ labels
const L = {
  currency: { IRR: "ریال", IRT: "تومان", UNKNOWN: "واحد نامشخص" },
  source: { torob: "ترب", basalam: "باسلام", digikala: "دیجی‌کالا", divar: "دیوار", instagram: "اینستاگرام", other: "سایر" },
  sourceState: {
    ready: ["آماده", "ok"], not_configured: ["پیکربندی نشده", ""], unavailable: ["در دسترس نیست", "bad"],
    rate_limited: ["محدودیت نرخ", "warn"], stale: ["داده قدیمی", "warn"],
  },
  collection: {
    complete: ["جمع‌آوری کامل انجام شد.", "ok"],
    partial: ["نتیجهٔ ناقص: برخی منابع پاسخ ندادند؛ داده‌های موجود نمایش داده می‌شود.", "warn"],
    no_sources_configured: ["هیچ منبعی فعال نیست. این نتیجه به معنی نبود کالا در بازار نیست؛ برای دریافت داده، منابع را در فایل .env فعال کنید.", "info"],
    failed: ["جمع‌آوری ناموفق بود؛ هیچ منبعی داده‌ای برنگرداند.", "error"],
  },
  availability: { in_stock: ["موجود", "ok"], out_of_stock: ["ناموجود", "bad"], unknown: ["موجودی نامشخص", ""] },
  condition: { new: "نو", used: "کارکرده", refurbished: "بازسازی‌شده", unknown: "وضعیت نامشخص" },
  classification: {
    below_market: ["زیر قیمت بازار", "ok", "#1a9d5b"], typical: ["قیمت معمول", "info", "#3b6cf6"],
    above_market: ["بالای قیمت بازار", "warn", "#d48806"], low_outlier: ["ارزان غیرعادی", "bad", "#13a8a8"],
    high_outlier: ["گران غیرعادی", "bad", "#d4380d"], unknown: ["نامشخص", "", "#9aa3b5"],
  },
  ai: {
    not_requested: ["تحلیل هوش مصنوعی درخواست نشده است. از دکمهٔ «جستجو + تحلیل هوش مصنوعی» استفاده کنید.", "info"],
    disabled: ["تحلیل هوش مصنوعی غیرفعال است (کلید Gemini در سرور تنظیم نشده). داده‌های قطعی محلی کامل هستند.", "info"],
    cached: ["نتیجهٔ ذخیره‌شدهٔ قبلی هوش مصنوعی استفاده شد.", "ok"],
    completed: ["تحلیل هوش مصنوعی با موفقیت انجام شد.", "ok"],
    invalid_response: ["پاسخ هوش مصنوعی معتبر نبود و کنار گذاشته شد. داده‌های محلی دست‌نخورده‌اند.", "warn"],
    failed: ["تحلیل هوش مصنوعی ناموفق بود. داده‌های محلی دست‌نخورده‌اند.", "warn"],
  },
  errorCode: {
    adapter_not_configured: "این منبع فعال نشده است.",
    detail_fetch_failed: "دریافت جزئیات برخی صفحات ناموفق بود.",
    timeout: "مهلت پاسخ‌گویی منبع به پایان رسید.",
    collection_error: "خطا در جمع‌آوری داده از این منبع.",
    gemini_disabled: "کلید Gemini در سرور تنظیم نشده است.",
    gemini_unavailable: "سرویس Gemini در دسترس نبود.",
    gemini_analysis_failed: "تحلیل Gemini ناموفق بود.",
    invalid_gemini_response: "پاسخ Gemini با قالب مورد انتظار مطابقت نداشت.",
  },
  field: { brand: "برند", model: "مدل", capacity: "ظرفیت", color: "رنگ", title: "عنوان" },
};
const label = (map, key, fallback) => (map[key] !== undefined ? map[key] : (fallback ?? key ?? "—"));
// Known codes get Persian text; unknown codes fall back to the server message (not a stable code).
const errorText = (code, message) => {
  if (code && L.errorCode[code]) return L.errorCode[code];
  if (code && /^http_\d{3}$/.test(code)) return `منبع با کد HTTP ${code.slice(5)} پاسخ داد.`;
  return message || code || "";
};
const pair = (map, key) => map[key] || [String(key ?? "نامشخص"), ""];

// ------------------------------------------------------------------ helpers
const $ = (sel) => document.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => { try { const p = new URL(u); return p.protocol === "https:" || p.protocol === "http:" ? p.href : null; } catch { return null; } };
const nf = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 2 });
const num = (v) => (v === null || v === undefined || Number.isNaN(v) ? "—" : nf.format(v));
const pct = (v) => (v === null || v === undefined ? "—" : `${nf2.format(v * 100)}٪`);
const dt = (v) => { if (!v) return "—"; const d = new Date(v); return Number.isNaN(d.getTime()) ? esc(v) : d.toLocaleString("fa-IR"); };
const unit = (c) => esc(label(L.currency, c, c || "واحد نامشخص"));
const money = (m) => (m ? `${num(m.amount)} <span class="unit">${unit(m.currency)}</span>` : "—");
const amount = (v, c) => (v === null || v === undefined ? "—" : `${num(v)} <span class="unit">${unit(c)}</span>`);
const chip = (text, cls = "") => `<span class="chip ${cls}">${esc(text)}</span>`;
const show = (el, on = true) => el.classList.toggle("hidden", !on);

async function api(path, body) {
  const opts = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(body),
  };
  let res;
  try { res = await fetch(API + path, opts); } catch { throw new Error("ارتباط با سرور برقرار نشد."); }
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON */ }
  if (!res.ok) {
    if (data && data.detail === "backend_unreachable") throw new Error("سرویس پشتیبان (backend) در دسترس نیست. آیا اجرا شده است؟");
    if (res.status === 422) throw new Error("درخواست نامعتبر است: " + describeDetail(data && data.detail));
    throw new Error(`خطای سرور (${res.status}): ${describeDetail(data && data.detail)}`);
  }
  return data;
}
function describeDetail(d) {
  if (!d) return "بدون توضیح";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("؛ ");
  return JSON.stringify(d);
}

// ------------------------------------------------------------------ tabs
document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === b));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${b.dataset.tab}`));
}));
function selectSub(name) {
  document.querySelectorAll(".subtab").forEach((x) => x.classList.toggle("active", x.dataset.sub === name));
  document.querySelectorAll(".subpanel").forEach((p) => p.classList.toggle("active", p.id === `sub-${name}`));
}
document.querySelectorAll(".subtab").forEach((b) => b.addEventListener("click", () => selectSub(b.dataset.sub)));

// ------------------------------------------------------------------ health
async function checkHealth() {
  const box = $("#health"), text = $("#health-text"), info = $("#service-info");
  box.classList.remove("ok", "bad");
  try {
    const h = await api("/health");
    let ready = "نامشخص";
    try { const r = await api("/ready"); ready = r.status === "ready" ? "آماده" : r.status; } catch (e) { ready = "آماده نیست"; }
    box.classList.add("ok");
    text.textContent = `سرویس فعال — نسخه ${h.version}`;
    info.innerHTML = `
      <dt>وضعیت</dt><dd>${esc(h.status === "ok" ? "فعال" : h.status)}</dd>
      <dt>آمادگی</dt><dd>${esc(ready)}</dd>
      <dt>سرویس</dt><dd>${esc(h.service)}</dd>
      <dt>نسخه</dt><dd class="ltr">${esc(h.version)}</dd>
      <dt>محیط</dt><dd class="ltr">${esc(h.environment)}</dd>
      <dt>کلید Gemini</dt><dd>${h.gemini_configured ? chip("تنظیم شده", "ok") : chip("تنظیم نشده", "")}</dd>`;
  } catch (e) {
    box.classList.add("bad");
    text.textContent = "سرویس در دسترس نیست";
    info.innerHTML = `<dt>خطا</dt><dd>${esc(e.message)}</dd>`;
  }
}
$("#recheck").addEventListener("click", checkHealth);

// ------------------------------------------------------------------ retail
let snapshot = null;

async function runRetail(withAI) {
  const query = $("#retail-query").value.trim();
  if (!query) { $("#retail-query").focus(); return; }
  const buttons = document.querySelectorAll("#retail-form button");
  buttons.forEach((b) => (b.disabled = true));
  show($("#retail-error"), false);
  show($("#retail-loading"));
  try {
    snapshot = await api(withAI ? "/searches/analysis" : "/searches", { query, refresh: $("#retail-refresh").checked });
    renderRetail();
    show($("#retail-result"));
    if (withAI) selectSub("ai");
  } catch (e) {
    $("#retail-error").textContent = e.message;
    show($("#retail-error"));
  } finally {
    show($("#retail-loading"), false);
    buttons.forEach((b) => (b.disabled = false));
  }
}
$("#retail-form").addEventListener("submit", (e) => { e.preventDefault(); runRetail(false); });
$("#retail-ai").addEventListener("click", () => runRetail(true));
$("#only-matches").addEventListener("change", () => snapshot && renderOffers());
$("#offer-sort").addEventListener("change", () => snapshot && renderOffers());

function banner(status, stale, collectedAt) {
  const [msg, cls] = pair(L.collection, status);
  let html = `<div class="alert ${cls || "info"}">${esc(msg)} <span class="muted">— زمان: ${dt(collectedAt)}</span></div>`;
  if (stale) html += `<div class="alert warn">بخشی از داده‌ها از حافظهٔ موقت قدیمی (stale) هستند.</div>`;
  return html;
}

function renderRetail() {
  const s = snapshot;
  $("#retail-banner").innerHTML = banner(s.collection_status, s.stale, s.collected_at);
  const q = s.query || {};
  const attrs = Object.entries(q.attributes || {}).map(([k, v]) => chip(`${k}: ${v}`)).join("");
  $("#query-info").innerHTML = `
    <dt>متن اصلی</dt><dd>${esc(q.original)}</dd>
    <dt>متن نرمال‌شده</dt><dd>${esc(q.normalized_text)}</dd>
    <dt>برند</dt><dd>${esc(q.brand ?? "—")}</dd>
    <dt>مدل</dt><dd>${esc(q.model ?? "—")}</dd>
    <dt>ظرفیت</dt><dd>${esc(q.capacity ?? "—")}</dd>
    <dt>رنگ</dt><dd>${esc(q.color ?? "—")}</dd>
    ${attrs ? `<dt>ویژگی‌ها</dt><dd>${attrs}</dd>` : ""}
    ${(q.variants || []).length ? `<dt>گونه‌ها</dt><dd>${q.variants.map((v) => chip(v)).join("")}</dd>` : ""}`;
  $("#source-statuses").innerHTML = renderSourceStatuses(s.source_statuses || [], "offer_count");
  $("#count-offers").textContent = nf.format((s.offers || []).length);
  $("#count-opps").textContent = nf.format((s.local_analysis?.opportunities || []).length);
  renderOffers();
  renderStats();
  renderOpportunities();
  renderAI();
}

function renderSourceStatuses(list, countField) {
  if (!list.length) return `<div class="muted">اطلاعاتی از منابع وجود ندارد.</div>`;
  return `<div class="sources">${list.map((st) => {
    const [txt, cls] = pair(L.sourceState, st.state);
    const extras = [];
    extras.push(chip(`${nf.format(st[countField] ?? 0)} مورد`));
    if (st.average_response_time_ms != null) extras.push(chip(`${num(st.average_response_time_ms)} میلی‌ثانیه`));
    if (st.failure_count) extras.push(chip(`${nf.format(st.failure_count)} خطا`, "bad"));
    if (st.temporary_disabled_until) extras.push(chip(`توقف موقت تا ${dt(st.temporary_disabled_until)}`, "warn"));
    if (st.stale_data_available) extras.push(chip("دادهٔ قدیمی موجود", "warn"));
    const err = errorText(st.error_code, st.error_message);
    return `<div class="source-row">
      <b>${esc(label(L.source, st.source, st.source))}</b>
      <span>${chip(txt, cls)} ${extras.join("")}</span>
      ${err && st.state !== "not_configured" ? `<div class="err">${esc(err)}</div>` : ""}
    </div>`;
  }).join("")}</div>`;
}

function renderOffers() {
  const s = snapshot;
  const la = s.local_analysis || {};
  const matches = Object.fromEntries((la.matches || []).map((m) => [m.offer_id, m]));
  const classes = Object.fromEntries((la.classifications || []).map((c) => [c.offer_id, c]));
  let offers = [...(s.offers || [])];
  if ($("#only-matches").checked) offers = offers.filter((o) => matches[o.offer_id]?.is_match);
  const sort = $("#offer-sort").value;
  const p = (o) => (o.price ? o.price.amount : null);
  offers.sort((a, b) => {
    if (sort === "match") return (matches[b.offer_id]?.score ?? -1) - (matches[a.offer_id]?.score ?? -1);
    if (sort === "source") return String(a.source).localeCompare(String(b.source));
    // Price sorting groups by currency first so IRR/IRT values are never compared.
    const ca = a.price?.currency ?? "~", cb = b.price?.currency ?? "~";
    if (ca !== cb) return ca.localeCompare(cb);
    if (p(a) === null) return 1;
    if (p(b) === null) return -1;
    return sort === "price-desc" ? p(b) - p(a) : p(a) - p(b);
  });
  if (!offers.length) {
    $("#offers").innerHTML = `<div class="card empty">${s.offers?.length ? "هیچ مورد منطبقی یافت نشد." : "پیشنهادی وجود ندارد."}</div>`;
    return;
  }
  $("#offers").innerHTML = `<div class="grid cards">${offers.map((o) => {
    const m = matches[o.offer_id], c = classes[o.offer_id];
    const url = safeUrl(o.product_url), img = safeUrl(o.image_url);
    const [avTxt, avCls] = pair(L.availability, o.availability);
    const chips = [
      chip(label(L.source, o.source, o.source), "info"), chip(avTxt, avCls), chip(label(L.condition, o.condition, o.condition)),
    ];
    if (c) { const [t, cl] = pair(L.classification, c.classification); chips.push(chip(t, cl)); }
    if (m) chips.push(chip(`انطباق ${pct(m.score)}`, m.is_match ? "ok" : ""));
    const rel = c && c.relative_to_median != null ? `<div class="meta">نسبت به میانه: ${pct(c.relative_to_median)}</div>` : "";
    const strike = o.original_price && (!o.price || o.original_price.amount !== o.price.amount)
      ? `<span class="strike">${money(o.original_price)}</span>` : "";
    return `<div class="card offer">
      ${img ? `<img src="${esc(img)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ""}
      <div class="body">
        <h3>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(o.title)}</a>` : esc(o.title)}</h3>
        <div class="price">${o.price ? money(o.price) : '<span class="muted">قیمت نامشخص</span>'}${strike}</div>
        ${rel}
        <div>${chips.join("")}</div>
        <div class="meta">
          ${o.seller ? `فروشنده: ${esc(o.seller)} · ` : ""}
          ${o.shipping ? `ارسال: ${money(o.shipping)} · ` : ""}
          ${o.shipping_information ? `${esc(o.shipping_information)} · ` : ""}
          مشاهده: ${dt(o.observed_at)}
        </div>
        ${m && (m.mismatched_fields.length || m.missing_fields.length) ? `<div class="meta">
          ${m.mismatched_fields.length ? `ناهمخوان: ${m.mismatched_fields.map((f) => esc(label(L.field, f, f))).join("، ")} ` : ""}
          ${m.missing_fields.length ? `نامعلوم: ${m.missing_fields.map((f) => esc(label(L.field, f, f))).join("، ")}` : ""}
        </div>` : ""}
      </div>
    </div>`;
  }).join("")}</div>`;
}

function renderStats() {
  const la = snapshot.local_analysis || {};
  const stats = la.statistics_by_currency || [];
  const charts = la.price_charts || [];
  if (!stats.length && !charts.length) {
    $("#stats").innerHTML = `<div class="card empty">آماری برای نمایش وجود ندارد (قیمت قابل‌مقایسه‌ای یافت نشد).</div>`;
    return;
  }
  const rows = [
    ["count", "تعداد", false], ["minimum", "کمینه"], ["p10", "صدک ۱۰"], ["p25", "چارک اول"], ["median", "میانه"],
    ["mean", "میانگین"], ["p75", "چارک سوم"], ["p90", "صدک ۹۰"], ["maximum", "بیشینه"],
    ["price_range", "دامنه"], ["standard_deviation", "انحراف معیار"],
  ];
  const groups = (la.deduplication_groups || []).length;
  $("#stats").innerHTML = stats.map((st) => {
    const chart = charts.find((c) => c.currency === st.currency);
    return `<div class="card">
      <h2>آمار قیمت — ${unit(st.currency)}</h2>
      <div class="stat-grid">
        ${rows.map(([k, t, isMoney = true]) => `<div class="stat"><div class="label">${t}</div>
          <div class="value">${isMoney ? amount(st[k], st.currency) : num(st[k])}</div></div>`).join("")}
        <div class="stat"><div class="label">ضریب تغییرات</div><div class="value">${pct(st.coefficient_of_variation)}</div></div>
        <div class="stat"><div class="label">گروه‌های کالای یکسان</div><div class="value">${nf.format(groups)}</div></div>
      </div>
      ${chart ? `<div class="chart">${renderChart(chart)}</div>` : ""}
    </div>`;
  }).join("") + charts.filter((c) => !stats.some((s) => s.currency === c.currency))
    .map((c) => `<div class="card"><h2>نمودار — ${unit(c.currency)}</h2><div class="chart">${renderChart(c)}</div></div>`).join("");
}

function renderChart(chart) {
  const pts = [...(chart.points || [])].sort((a, b) => a.amount - b.amount);
  if (!pts.length) return `<div class="muted">نقطه‌ای برای نمودار وجود ندارد.</div>`;
  const W = 900, H = 300, padL = 20, padR = 110, padT = 15, padB = 30;
  const max = Math.max(...pts.map((p) => p.amount), chart.p75 || 0) * 1.08 || 1;
  const bw = (W - padL - padR) / pts.length;
  const y = (v) => padT + (H - padT - padB) * (1 - v / max);
  const bars = pts.map((p, i) => {
    const color = pair(L.classification, p.classification)[2] || "#9aa3b5";
    const x = padL + i * bw + bw * 0.12;
    const tip = `${label(L.source, p.source, p.source)} — ${p.label}: ${nf.format(p.amount)} ${label(L.currency, p.currency)}`;
    return `<rect x="${x.toFixed(1)}" y="${y(p.amount).toFixed(1)}" width="${Math.max(bw * 0.76, 1).toFixed(1)}"
      height="${(H - padB - y(p.amount)).toFixed(1)}" rx="3" fill="${color}"><title>${esc(tip)}</title></rect>`;
  }).join("");
  const line = (v, name, color) => (v == null ? "" : `
    <line x1="${padL}" x2="${W - padR}" y1="${y(v)}" y2="${y(v)}" stroke="${color}" stroke-dasharray="6 4" stroke-width="1.5"/>
    <text x="${W - padR + 6}" y="${y(v) + 4}" font-size="12" fill="${color}" text-anchor="start" direction="rtl">${name}: ${nf.format(v)}</text>`);
  const used = [...new Set(pts.map((p) => p.classification))];
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="نمودار قیمت">
      <line x1="${padL}" x2="${W - padR}" y1="${H - padB}" y2="${H - padB}" stroke="#ccd2de"/>
      ${bars}
      ${line(chart.p25, "چارک اول", "#13a8a8")}${line(chart.median, "میانه", "#1d2433")}${line(chart.p75, "چارک سوم", "#d48806")}
      <text x="${padL}" y="${H - 8}" font-size="12" fill="#6b7385">${nf.format(pts.length)} قیمت (از ارزان به گران)</text>
    </svg>
    <div class="legend">${used.map((c) => { const [t, , col] = pair(L.classification, c); return `<span><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" rx="3" fill="${col || "#9aa3b5"}"/></svg> ${esc(t)}</span>`; }).join("")}</div>`;
}

function renderOpportunities() {
  const opps = snapshot.local_analysis?.opportunities || [];
  const offers = Object.fromEntries((snapshot.offers || []).map((o) => [o.offer_id, o]));
  if (!opps.length) { $("#opportunities").innerHTML = `<div class="card empty">فرصتی شناسایی نشد.</div>`; return; }
  $("#opportunities").innerHTML = `<div class="card table-wrap"><table>
    <thead><tr><th>کالا</th><th>قیمت خرید</th><th>قیمت فروش مورد انتظار</th><th>هزینهٔ کل</th><th>سود</th><th>حاشیهٔ سود</th><th>بازده (ROI)</th><th>طبقه</th></tr></thead>
    <tbody>${opps.map((o) => {
      const offer = offers[o.offer_id];
      const url = offer && safeUrl(offer.product_url);
      const title = offer ? esc(offer.title) : esc(o.offer_id ?? "—");
      const [ct, cc] = pair(L.classification, o.classification);
      return `<tr>
        <td>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${title}</a>` : title}
          ${offer ? `<div class="meta">${esc(label(L.source, offer.source, offer.source))}</div>` : ""}</td>
        <td>${money(o.assumptions?.purchase_price)}</td>
        <td>${money(o.assumptions?.expected_resale_price)}</td>
        <td>${amount(o.total_cost, o.currency)}</td>
        <td>${amount(o.profit, o.currency)}</td>
        <td>${pct(o.profit_margin)}</td>
        <td>${pct(o.roi)}</td>
        <td>${chip(ct, cc)}</td></tr>`;
    }).join("")}</tbody></table></div>`;
}

function renderAI() {
  const env = snapshot.ai_analysis || { status: "not_requested" };
  const [msg, cls] = pair(L.ai, env.status);
  let html = `<div class="alert ${cls || "info"}">${esc(msg)}</div>`;
  if ((env.error_code || env.error_message) && env.status !== "disabled") {
    html += `<div class="alert warn">${esc(errorText(env.error_code, env.error_message))}</div>`;
  }
  const r = env.result;
  if (r) {
    const list = (title, items) => (items && items.length
      ? `<h3>${title}</h3><ul class="ai-list">${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "");
    html += `<div class="card">
      ${r.summary ? `<h3>خلاصه</h3><p>${esc(r.summary)}</p>` : ""}
      ${r.market_assessment ? `<h3>ارزیابی بازار</h3><p>${esc(r.market_assessment)}</p>` : ""}
      <h3>اطمینان</h3><meter class="confidence" min="0" max="1" value="${Number(r.confidence) || 0}"></meter>
      <div class="muted">${pct(r.confidence)}</div>
    </div>
    <div class="grid two">
      <div class="card">${list("واقعیت‌ها (از داده‌ها)", r.facts)}${list("پیشنهادهای ارزان", r.cheap_offers)}${list("پیشنهادهای گران", r.expensive_offers)}${list("فرصت‌های احتمالی", r.potential_opportunities)}</div>
      <div class="card">${list("استنباط‌ها", r.inferences)}${list("عدم قطعیت‌ها", r.uncertainties)}${list("ریسک‌ها", r.risks)}${list("اطلاعات ناموجود", r.missing_information)}</div>
    </div>`;
  }
  if (env.model || env.dataset_hash) {
    html += `<div class="muted">مدل: <span class="ltr">${esc(env.model ?? "—")}</span> · نسخهٔ پرامپت: <span class="ltr">${esc(env.prompt_version ?? "—")}</span></div>`;
  }
  html += `<p class="muted">تفسیر هوش مصنوعی جایگزین داده‌های قطعی محلی نیست و فقط بر اساس خلاصه‌ای محدود از داده‌ها تولید می‌شود.</p>`;
  $("#ai").innerHTML = html;
}

// ------------------------------------------------------------------ wholesale
$("#wholesale-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = $("#wholesale-query").value.trim();
  if (!query) return;
  const btn = $("#wholesale-form button");
  btn.disabled = true;
  show($("#wholesale-error"), false);
  show($("#wholesale-loading"));
  try {
    const w = await api("/wholesale/searches", { query, refresh: $("#wholesale-refresh").checked });
    $("#wholesale-banner").innerHTML = banner(w.collection_status, w.stale, w.collected_at);
    $("#wholesale-statuses").innerHTML = renderSourceStatuses(w.source_statuses || [], "listing_count");
    const ls = w.listings || [];
    $("#wholesale-listings").innerHTML = ls.length ? `<div class="card table-wrap"><table>
      <thead><tr><th>عنوان</th><th>تأمین‌کننده</th><th>قیمت واحد</th><th>حداقل سفارش</th><th>موقعیت</th><th>وضعیت</th><th>ارسال</th><th>تماس عمومی</th></tr></thead>
      <tbody>${ls.map((l) => {
        const url = safeUrl(l.product_url);
        const [avTxt, avCls] = pair(L.availability, l.availability);
        return `<tr>
          <td>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(l.title)}</a>` : esc(l.title)}<div class="meta">${esc(l.source)}</div></td>
          <td>${esc(l.supplier_name ?? "—")}</td>
          <td>${money(l.unit_price)}</td>
          <td>${num(l.minimum_order_quantity)}</td>
          <td>${esc(l.location ?? "—")}</td>
          <td>${chip(avTxt, avCls)} ${chip(label(L.condition, l.condition, l.condition))}</td>
          <td>${esc(l.shipping_information ?? "—")}</td>
          <td>${esc(l.public_contact ?? "—")}</td></tr>`;
      }).join("")}</tbody></table></div>` : `<div class="card empty">موردی یافت نشد.</div>`;
    show($("#wholesale-result"));
  } catch (err) {
    $("#wholesale-error").textContent = err.message;
    show($("#wholesale-error"));
  } finally {
    show($("#wholesale-loading"), false);
    btn.disabled = false;
  }
});

checkHealth();
