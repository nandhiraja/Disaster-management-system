/* Shared API client – all pages import this */
const API ="https://disaster-management-system-yy3e.onrender.com/api"; // Replace with your Render URL
//  api = "http://localhost:8000/api";

async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(API + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return await res.json();
  } catch (e) {
    throw e;
  }
}

/* Toast notification helper */
function showToast(msg, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = "0"; toast.style.transition = "opacity 0.4s"; }, 3000);
  setTimeout(() => toast.remove(), 3500);
}

/* Status badge colour mapper */
function statusBadge(status) {
  const map = {
    pending:         "badge-red",
    assigned:        "badge-blue",
    in_progress:     "badge-amber",
    rescued:         "badge-green",
    closed:          "badge-gray",
    available:       "badge-green",
    busy:            "badge-amber",
    offline:         "badge-gray",
    created:         "badge-gray",
    en_route:        "badge-blue",
    on_site:         "badge-purple",
    rescue_in_progress: "badge-amber",
    completed:       "badge-green",
    cancelled:       "badge-red",
    medical:         "badge-red",
    flood:           "badge-blue",
    trapped:         "badge-amber",
    elderly:         "badge-purple",
    unknown:         "badge-gray",
    boat:            "badge-blue",
    ambulance:       "badge-red",
    volunteer:       "badge-green",
    helicopter:      "badge-purple",
    logistics:       "badge-orange",
  };
  const cls = map[status] || "badge-gray";
  return `<span class="badge ${cls}">${status?.replace(/_/g, " ")}</span>`;
}

/* Format ISO timestamp nicely */
function fmtTime(ts) {
  if (!ts) return "–";
  try {
    const d = new Date(ts + "Z");
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) + " " +
           d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
  } catch { return ts; }
}

/* Emergency type icon */
function emIcon(type) {
  return { medical: "🏥", flood: "🌊", trapped: "⛑️", elderly: "👴", unknown: "❓" }[type] || "🆘";
}

/* Sidebar active link highlighter */
function setSidebarActive(page) {
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.dataset.page === page);
  });
}
