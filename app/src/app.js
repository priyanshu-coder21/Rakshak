// // --- CONFIGURATION ---
// const API_BASE_URL = 'http://localhost:8000'; // Ensure this matches your FastAPI server URL

// // --- UI / TAB SWITCHING ---
// function switchTab(tabId) {
//     document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
//     document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    
//     document.getElementById(tabId).classList.add('active');
//     event.target.classList.add('active');

//     if (tabId === 'dashboard-tab') {
//         loadDistressTickets();
//         loadRescueTeams();
//     }
// }

// // --- UTILITY: GET BROWSER GPS ---
// function getLocation(latId, lngId) {
//     if (navigator.geolocation) {
//         navigator.geolocation.getCurrentPosition(
//             (position) => {
//                 document.getElementById(latId).value = position.coords.latitude.toFixed(6);
//                 document.getElementById(lngId).value = position.coords.longitude.toFixed(6);
//             },
//             (error) => alert("Error getting location: " + error.message)
//         );
//     } else {
//         alert("Geolocation is not supported by this browser.");
//     }
// }

// // --- UTILITY: SHOW MESSAGES ---
// function showResponse(elementId, message, isError = false) {
//     const el = document.getElementById(elementId);
//     el.textContent = message;
//     el.classList.remove('hidden', 'error');
//     if (isError) el.classList.add('error');
//     setTimeout(() => el.classList.add('hidden'), 5000); // Auto-hide
// }

// // --- API 1: SUBMIT DISTRESS TICKET ---
// document.getElementById('distress-form').addEventListener('submit', async (e) => {
//     e.preventDefault();
//     const payload = {
//         raw_message: document.getElementById('raw_message').value,
//         latitude: parseFloat(document.getElementById('v_latitude').value),
//         longitude: parseFloat(document.getElementById('v_longitude').value)
//     };

//     try {
//         const res = await fetch(`${API_BASE_URL}/api/distress`, {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify(payload)
//         });
        
//         const data = await res.json();
//         if (res.ok) {
//             showResponse('distress-response', `Success! Token ID: ${data.token_id} | Status: ${data.status}`);
//             e.target.reset();
//         } else {
//             showResponse('distress-response', `Error: ${data.detail}`, true);
//         }
//     } catch (error) {
//         showResponse('distress-response', `Network Error: ${error.message}`, true);
//     }
// });

// // --- API 2: REGISTER RESCUE TEAM ---
// document.getElementById('rescue-form').addEventListener('submit', async (e) => {
//     e.preventDefault();
//     const payload = {
//         latitude: parseFloat(document.getElementById('r_latitude').value),
//         longitude: parseFloat(document.getElementById('r_longitude').value),
//         team_capacity: parseInt(document.getElementById('team_capacity').value)
//     };

//     try {
//         const res = await fetch(`${API_BASE_URL}/api/rescue`, {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify(payload)
//         });
        
//         const data = await res.json();
//         if (res.ok) {
//             showResponse('rescue-response', `Registered! Team ID: ${data.team_id}`);
//             e.target.reset();
//         } else {
//             showResponse('rescue-response', `Error: ${data.detail}`, true);
//         }
//     } catch (error) {
//         showResponse('rescue-response', `Network Error: ${error.message}`, true);
//     }
// });

// // --- API 3: FETCH DISTRESS DASHBOARD ---
// async function loadDistressTickets() {
//     try {
//         const res = await fetch(`${API_BASE_URL}/getDistress`);
//         if (!res.ok) throw new Error("Failed to fetch tickets");
//         const tickets = await res.json();
        
//         const tbody = document.querySelector('#distress-table tbody');
//         tbody.innerHTML = ''; 
        
//         tickets.forEach(t => {
//             tbody.innerHTML += `
//                 <tr>
//                     <td><strong>${t.token_id}</strong></td>
//                     <td>${t.vwps_score ? t.vwps_score.toFixed(2) : '0.00'}</td>
//                     <td><span style="color: ${t.status === 'Pending' ? '#d97706' : '#16a34a'}">${t.status}</span></td>
//                 </tr>
//             `;
//         });
//     } catch (error) {
//         console.error(error);
//     }
// }

// // --- API 4: FETCH TEAMS DASHBOARD ---
// async function loadRescueTeams() {
//     try {
//         const res = await fetch(`${API_BASE_URL}/getRescue`);
//         if (!res.ok) throw new Error("Failed to fetch teams");
//         const teams = await res.json();
        
//         const tbody = document.querySelector('#rescue-table tbody');
//         tbody.innerHTML = ''; 
        
//         teams.forEach(t => {
//             tbody.innerHTML += `
//                 <tr>
//                     <td><strong>${t.team_id}</strong></td>
//                     <td>${t.capacity}</td>
//                     <td>${t.status}</td>
//                 </tr>
//             `;
//         });
//     } catch (error) {
//         console.error(error);
//     }
// }

// // --- API 5: RUN DISPATCH SCHEDULER ---
// async function runDispatchAlgorithm() {
//     try {
//         const res = await fetch(`${API_BASE_URL}/api/dispatch/run`, {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' }
//         });
        
//         if (res.ok) {
//             showResponse('dispatch-response', "Dispatch run successful! Refreshing tables...");
//             loadDistressTickets();
//             loadRescueTeams();
//         } else {
//             const data = await res.json();
//             showResponse('dispatch-response', `Dispatch Error: ${data.detail}`, true);
//         }
//     } catch (error) {
//         showResponse('dispatch-response', `Network Error: ${error.message}`, true);
//     }
// }
















"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const state = { tickets: [], teams: [], logs: [] };

// ---------- helpers ----------
function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function toast(msg, isErr = false) {
  const t = document.createElement("div");
  t.className = "toast" + (isErr ? " err" : "");
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), isErr ? 6000 : 3500);
}
function errText(detail) {
  if (!detail) return "Something went wrong.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(d => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  return JSON.stringify(detail);
}
async function api(path, opts) {
  let res;
  try { res = await fetch(path, opts); }
  catch { throw new Error("Cannot reach the server. Check that the backend is running."); }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!res.ok) throw new Error(errText(data && data.detail) || res.statusText);
  return data;
}
const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// PostGIS returns geometry as hex EWKB; decode it to lat/lng.
function decodeLocation(loc) {
  try {
    if (loc && typeof loc === "object" && Array.isArray(loc.coordinates)) return { lng: loc.coordinates[0], lat: loc.coordinates[1] };
    if (typeof loc !== "string" || !/^[0-9a-fA-F]+$/.test(loc)) return null;
    const b = new Uint8Array(loc.match(/../g).map(h => parseInt(h, 16)));
    const dv = new DataView(b.buffer);
    const le = b[0] === 1;
    const type = dv.getUint32(1, le);
    let off = 5;
    if (type & 0x20000000) off += 4;
    return { lng: dv.getFloat64(off, le), lat: dv.getFloat64(off + 8, le) };
  } catch { return null; }
}
function fmtLoc(loc) {
  const p = decodeLocation(loc);
  return p ? `${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}` : "n/a";
}
function fmtTime(v) {
  if (!v) return "n/a";
  const d = new Date(v);
  return isNaN(d) ? esc(v) : d.toLocaleString();
}
const pill = s => `<span class="pill ${esc(s)}">${esc(String(s ?? "").replace("_", " "))}</span>`;
const sev = n => `<span class="sev sev${esc(n)}">${esc(n ?? "n/a")}</span>`;
const emptyRow = (cols, text) => `<tr><td class="empty" colspan="${cols}">${text}</td></tr>`;

// ---------- rendering ----------
function renderStats() {
  const t = state.tickets, r = state.teams;
  $("#stPending").textContent = t.filter(x => x.status === "Pending").length;
  $("#stDispatched").textContent = t.filter(x => x.status === "Dispatched").length;
  $("#stAvail").textContent = r.filter(x => x.status === "Available").length;
  $("#stTransit").textContent = r.filter(x => x.status === "In_Transit").length;
}
function renderTeams() {
  $("#teamBody").innerHTML = state.teams.length
    ? state.teams.map(x => `<tr><td><code>${esc(x.team_id)}</code></td><td>${pill(x.status)}</td><td>${esc(x.capacity)}</td><td>${fmtLoc(x.location)}</td></tr>`).join("")
    : emptyRow(4, "No teams yet. Register one above.");
}
function renderTickets() {
  const q = $("#tkSearch").value.trim().toLowerCase(), f = $("#tkFilter").value;
  const rows = state.tickets
    .filter(x => (!f || x.status === f) && (!q || `${x.token_id} ${x.raw_message}`.toLowerCase().includes(q)))
    .sort((a, b) => (b.vwps_score ?? 0) - (a.vwps_score ?? 0));
  $("#tkBody").innerHTML = rows.length
    ? rows.map(x => `<tr><td><code>${esc(x.token_id)}</code></td><td class="msg">${esc(x.raw_message)}</td><td>${sev(x.severity)}</td><td>${esc(x.vulnerability)}</td><td>${esc(x.vwps_score ?? "n/a")}</td><td>${pill(x.status)}</td><td>${fmtLoc(x.location)}</td></tr>`).join("")
    : emptyRow(7, "No requests match.");
}
function renderQueue() {
  const rows = state.tickets.filter(x => x.status === "Pending")
    .sort((a, b) => (b.vwps_score ?? 0) - (a.vwps_score ?? 0) || String(a.token_id).localeCompare(b.token_id)).slice(0, 5);
  $("#queueBody").innerHTML = rows.length
    ? rows.map(x => `<tr><td><code>${esc(x.token_id)}</code></td><td>${esc(x.vwps_score ?? "n/a")}</td><td>${sev(x.severity)}</td><td>${esc(x.vulnerability)}</td><td>${fmtTime(x.wait_time_start)}</td></tr>`).join("")
    : emptyRow(5, "The queue is empty.");
}
function renderLogs() {
  const rows = [...state.logs].reverse();
  $("#logBody").innerHTML = rows.length
    ? rows.map(x => `<tr><td>${esc(x.log_id)}</td><td><code>${esc(x.token_id)}</code></td><td><code>${esc(x.team_id)}</code></td><td>${fmtTime(x.dispatch_time)}</td><td>${x.sns_alert_sent ? "Yes" : "No"}</td></tr>`).join("")
    : emptyRow(5, "Nothing dispatched yet.");
}
const renderAll = () => { renderStats(); renderTeams(); renderTickets(); renderQueue(); renderLogs(); };

// ---------- loading ----------
const loaders = {
  tickets: async () => { state.tickets = await api("/getDistress"); },
  teams: async () => { state.teams = await api("/getRescue"); },
  logs: async () => { state.logs = await api("/getDispatchLogs"); },
};
async function load(kinds = Object.keys(loaders), quiet = false) {
  const results = await Promise.allSettled(kinds.map(k => loaders[k]()));
  results.forEach((r, i) => { if (r.status === "rejected" && !quiet) toast(`Could not load ${kinds[i]}: ${r.reason.message}`, true); });
  renderAll();
}

// ---------- tabs ----------
function showTab(name) {
  $$(".tab").forEach(b => { const on = b.dataset.tab === name; b.classList.toggle("active", on); b.setAttribute("aria-selected", on); });
  $$(".panel").forEach(p => p.classList.toggle("active", p.id === "tab-" + name));
  location.hash = name;
}
$$(".tab").forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));
$$("[data-refresh]").forEach(b => b.addEventListener("click", async () => { await load([b.dataset.refresh]); toast("Refreshed"); }));
$("#refreshAll").addEventListener("click", async () => { await load(); toast("Refreshed"); });
["tkSearch", "tkFilter"].forEach(id => $("#" + id).addEventListener("input", renderTickets));

// ---------- geolocation ----------
$$("[data-geo]").forEach(b => b.addEventListener("click", () => {
  const p = b.dataset.geo;
  if (!navigator.geolocation) return toast("This browser cannot share your location.", true);
  b.disabled = true;
  navigator.geolocation.getCurrentPosition(
    pos => { $(`#${p}Lat`).value = pos.coords.latitude.toFixed(6); $(`#${p}Lng`).value = pos.coords.longitude.toFixed(6); b.disabled = false; toast("Location filled in"); },
    err => { b.disabled = false; toast("Could not get location: " + err.message, true); },
    { enableHighAccuracy: true, timeout: 10000 });
}));

// ---------- distress form ----------
$("#dMsg").addEventListener("input", e => { $("#dCount").textContent = e.target.value.trim().split(/\s+/).filter(Boolean).length; });
$("#distressForm").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = $("#dSubmit"), out = $("#dResult");
  btn.disabled = true; btn.textContent = "Sending...";
  try {
    const d = await post("/api/distress", {
      raw_message: $("#dMsg").value.trim(),
      latitude: parseFloat($("#dLat").value),
      longitude: parseFloat($("#dLng").value),
    });
    out.className = "card result"; out.hidden = false;
    out.innerHTML = `<b>${esc(d.message)}</b>
      <div class="token"><span>Tracking token</span><code id="tokenVal">${esc(d.token_id)}</code><button type="button" class="ghost" id="copyTok">Copy token</button></div>
      <div>Status: ${pill(d.status)} &nbsp; Severity: ${sev(d.extracted_data?.severity)} &nbsp; Vulnerability: <b>${esc(d.extracted_data?.vulnerability ?? "n/a")}</b></div>`;
    $("#copyTok").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(d.token_id); toast("Token copied"); } catch { toast("Copy failed. Select the token and copy it manually.", true); }
    });
    $("#dMsg").value = ""; $("#dCount").textContent = "0";
    toast("Request sent");
    load(["tickets"], true);
  } catch (err) {
    out.className = "card result err"; out.hidden = false;
    out.textContent = "Request not sent: " + err.message;
    toast(err.message, true);
  } finally { btn.disabled = false; btn.textContent = "Send request"; }
});

// ---------- team form ----------
$("#teamForm").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = $("#tSubmit"); btn.disabled = true; btn.textContent = "Registering...";
  try {
    const d = await post("/api/rescue", {
      latitude: parseFloat($("#tLat").value),
      longitude: parseFloat($("#tLng").value),
      team_capacity: parseInt($("#tCap").value, 10),
    });
    toast(`Team ${d.team_id} registered`);
    await load(["teams"], true);
  } catch (err) { toast(err.message, true); }
  finally { btn.disabled = false; btn.textContent = "Register team"; }
});

// ---------- dispatch ----------
$("#runDispatch").addEventListener("click", async () => {
  const btn = $("#runDispatch"), out = $("#dispResult");
  btn.disabled = true; btn.textContent = "Dispatching...";
  const before = state.logs.length;
  try {
    await api("/api/dispatch/run", { method: "POST" });
    await load(undefined, true);
    const log = state.logs.length > before ? state.logs[state.logs.length - 1] : null;
    out.className = "result"; out.hidden = false;
    out.innerHTML = log
      ? `Team <code>${esc(log.team_id)}</code> is on the way to request <code>${esc(log.token_id)}</code>.`
      : "Dispatch finished.";
    toast("Dispatched");
  } catch (err) {
    await load(undefined, true);
    out.className = "result err"; out.hidden = false;
    out.textContent = "Nothing dispatched: " + err.message;
    toast(err.message, true);
  } finally { btn.disabled = false; btn.textContent = "Run dispatch"; }
});

// ---------- auto refresh + clock ----------
setInterval(() => { $("#clock").textContent = new Date().toLocaleString(); }, 1000);
$("#clock").textContent = new Date().toLocaleString();
setInterval(() => { if ($("#autoRefresh").checked && !document.hidden) load(undefined, true); }, 10000);

const startTab = location.hash.slice(1);
if ($(`.tab[data-tab="${startTab}"]`)) showTab(startTab);
load();