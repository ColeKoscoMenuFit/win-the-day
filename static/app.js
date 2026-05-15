const state = { emails: null, openThread: null };

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function escapeHTML(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function toast(msg, type = "ok") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = `toast show ${type}`;
  setTimeout(() => el.classList.remove("show"), 2500);
}

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function renderCard(email) {
  const badges = [];
  if (email.has_attachments) badges.push('<span class="badge">attach</span>');
  if (email.is_calendar) badges.push('<span class="badge">cal</span>');
  return `
    <div class="card" data-thread="${escapeHTML(email.thread_id)}">
      <div class="card-from">${escapeHTML(email.from)}</div>
      <div class="card-subject">${escapeHTML(email.subject)}${badges.length ? `<span class="card-badges">${badges.join("")}</span>` : ""}</div>
      <div class="card-snippet">${escapeHTML(email.snippet)}</div>
    </div>
  `;
}

function renderBoard(emails) {
  state.emails = emails;
  for (const col of $$(".column")) {
    const key = col.dataset.key;
    const items = emails[key] || [];
    col.querySelector("[data-count]").textContent = items.length ? `(${items.length})` : "";
    const cards = col.querySelector("[data-cards]");
    if (items.length === 0) {
      cards.innerHTML = '<div class="empty">Nothing here.</div>';
    } else {
      cards.innerHTML = items.map(renderCard).join("");
    }
  }
}

async function loadBoard() {
  try {
    const data = await fetchJSON("/api/emails");
    renderBoard(data);
  } catch (e) {
    toast(`Load failed: ${e.message}`, "err");
  }
}

async function refresh() {
  const btn = $("#refresh-btn");
  btn.disabled = true;
  btn.textContent = "Refreshing...";
  try {
    const data = await fetchJSON("/api/refresh", { method: "POST" });
    renderBoard(data);
    toast("Refreshed");
  } catch (e) {
    toast(`Refresh failed: ${e.message}`, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "Refresh";
  }
}

async function expand(card, threadId) {
  if (state.openThread && state.openThread !== threadId) {
    collapseAll();
  }
  if (card.classList.contains("expanded")) return;
  state.openThread = threadId;
  card.classList.add("expanded");

  card.insertAdjacentHTML("beforeend", `
    <div class="detail">
      <div class="body-box" data-body><span class="spinner"></span>Loading message...</div>
      <div class="draft-label">Draft reply</div>
      <textarea class="draft" data-draft placeholder="Generating draft..."></textarea>
      <div class="actions">
        <button class="btn btn-primary" data-action="send">Send</button>
        <button class="btn" data-action="regen">Regenerate draft</button>
        <button class="btn btn-ghost" data-action="discard">Discard</button>
      </div>
    </div>
  `);

  try {
    const thread = await fetchJSON(`/api/thread/${threadId}`);
    card.querySelector("[data-body]").textContent = thread.body || "(empty message)";
  } catch (e) {
    card.querySelector("[data-body]").textContent = `Failed to load message: ${e.message}`;
  }

  const ta = card.querySelector("[data-draft]");
  ta.value = "";
  ta.placeholder = "Generating draft...";
  try {
    const d = await fetchJSON(`/api/draft/${threadId}`);
    ta.value = d.draft || "";
    ta.placeholder = "Write your reply...";
  } catch (e) {
    ta.placeholder = `Draft failed: ${e.message}`;
  }
}

function collapseAll() {
  for (const card of $$(".card.expanded")) {
    card.classList.remove("expanded");
    const detail = card.querySelector(".detail");
    if (detail) detail.remove();
  }
  state.openThread = null;
}

async function send(card, threadId) {
  const ta = card.querySelector("[data-draft]");
  const body = ta.value.trim();
  if (!body) { toast("Draft is empty", "err"); return; }
  card.classList.add("sending");
  try {
    await fetchJSON("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId, body }),
    });
    card.remove();
    toast("Sent");
    state.openThread = null;
  } catch (e) {
    card.classList.remove("sending");
    toast(`Send failed: ${e.message}`, "err");
  }
}

async function regen(card, threadId) {
  const ta = card.querySelector("[data-draft]");
  const btns = card.querySelectorAll("button");
  btns.forEach(b => b.disabled = true);
  const oldPlaceholder = ta.placeholder;
  ta.placeholder = "Regenerating...";
  try {
    const d = await fetchJSON(`/api/draft/${threadId}/regenerate`, { method: "POST" });
    ta.value = d.draft || "";
  } catch (e) {
    toast(`Regenerate failed: ${e.message}`, "err");
  } finally {
    btns.forEach(b => b.disabled = false);
    ta.placeholder = oldPlaceholder;
  }
}

document.addEventListener("click", (e) => {
  const action = e.target.dataset?.action;
  const card = e.target.closest(".card");
  if (action && card) {
    const threadId = card.dataset.thread;
    if (action === "send") return send(card, threadId);
    if (action === "regen") return regen(card, threadId);
    if (action === "discard") {
      collapseAll();
      return;
    }
  }
  if (card && !card.classList.contains("expanded")) {
    expand(card, card.dataset.thread);
  }
});

$("#refresh-btn").addEventListener("click", refresh);

loadBoard();
