/* 湖企智库 - 前端逻辑 */
(function () {
  let currentUser = null;
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);
  const TABS = {
    dashboard: "工作台", kb: "知识库管理", chat: "智能问答", retrieve: "检索测试",
    graph: "知识图谱", audit: "审计日志", users: "用户管理", system: "系统设置"
  };

  async function api(url, opts = {}) {
    const res = await fetch(url, {
      method: opts.method || "GET",
      headers: opts.body ? { "Content-Type": "application/json" } : {},
      credentials: "same-origin",
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (res.status === 401) { location.reload(); throw new Error("未登录"); }
    const data = await res.json();
    if (!data.success && !opts.raw) throw new Error(data.error || "请求失败");
    return data;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  function showMsg(el, text, ok) {
    el.className = "msg " + (ok ? "ok" : "err");
    el.textContent = text;
  }

  const badge = (level) => {
    const m = { "公开": "gray", "内部": "blue", "机密": "red" };
    return `<span class="badge ${m[level] || "gray"}">${esc(level)}</span>`;
  };
  const statusBadge = (s) => {
    const m = { "ready": "green", "pending": "amber", "error": "red" };
    const t = { "ready": "已入库", "pending": "解析中", "error": "失败" };
    return `<span class="badge ${m[s] || "gray"}">${t[s] || s}</span>`;
  };

  /* ---------- 登录 ---------- */
  async function initSession() {
    try {
      const d = await api("/api/me");
      if (d.logged_in) {
        currentUser = d.user;
        enterApp();
      } else {
        showLogin();
      }
    } catch (e) { showLogin(); }
  }

  function showLogin() {
    $("#loginPage").style.display = "flex";
    $("#mainApp").style.display = "none";
  }
  function enterApp() {
    $("#loginPage").style.display = "none";
    $("#mainApp").style.display = "flex";
    $("#navUser").textContent = currentUser.username;
    $("#navRole").textContent = currentUser.role === "admin" ? "管理员" : "普通用户";
    $("#navRole").className = "role-tag " + currentUser.role;
    $("#topUser").textContent = currentUser.dept + " · " + currentUser.username;
    $$(".admin-only").forEach((el) => { el.style.display = currentUser.role === "admin" ? "" : "none"; });
    switchTab("dashboard");
    loadSystemMeta();
  }

  /* ---------- Tab 切换 ---------- */
  function switchTab(page) {
    $$(".nav-item").forEach((el) => el.classList.toggle("active", el.dataset.page === page));
    $$(".page").forEach((el) => el.classList.remove("active"));
    $("#page-" + page).classList.add("active");
    $("#pageTitle").textContent = TABS[page];
    loaders[page] && loaders[page]();
  }
  const loaders = {
    dashboard: loadDashboard,
    kb: loadKb,
    chat: loadChatInit,
    retrieve: () => {},
    graph: loadGraph,
    audit: loadAudit,
    users: loadUsers,
    system: loadSystem,
  };

  function loadGraph() {
    if (window.KGraph) { window.KGraph.load(); window.KGraph.start(); }
  }

  /* ---------- 工作台 ---------- */
  async function loadDashboard() {
    const d = await api("/api/stats");
    $("#stDocs").textContent = d.doc_ready + "/" + d.doc_total;
    $("#stChunks").textContent = d.chunk_total;
    $("#stQa").textContent = d.qa_total;
    $("#stSat").textContent = d.satisfaction == null ? "--" : d.satisfaction + "%";
    const cb = $("#catBars");
    cb.innerHTML = d.categories.length ? d.categories.map((c) => {
      const pct = Math.round(c.value / Math.max(1, d.doc_ready) * 100);
      return `<div class="cat-row"><span class="cat-name">${esc(c.name)}</span>
        <div class="cat-bar-bg"><div class="cat-bar" style="width:${Math.max(8, pct)}%"></div></div>
        <span class="cat-val">${c.value}</span></div>`;
    }).join("") : '<div class="muted">暂无知识文档，请先上传或导入</div>';
    const ss = $("#sysState");
    const sys = await api("/api/system");
    const dot = (ok) => `<span class="dot ${ok ? "green" : "red"}"></span>`;
    ss.innerHTML = `
      <div>${dot(sys.ollama_ready)}Ollama 服务：${sys.ollama_ready ? "在线" : "离线（演示可忽略）"}</div>
      <div>${dot(sys.llm_ready)}DeepSeek 模型：${sys.llm_ready ? "已就绪" : "未加载"}</div>
      <div><span class="dot green"></span>推理模式：${sys.mode === "local" ? "本地推理（数据不出域）" : "模拟模式（开箱即用）"}</div>
      <div>${dot(true)}敏感数据处理：全程内网</div>`;
    const rq = $("#recentQa");
    rq.innerHTML = d.recent_qa.length ? d.recent_qa.map((q) => `
      <div class="qa-line">
        <div class="qa-q">${esc(q.question)}</div>
        <div class="qa-a">${esc(q.answer).slice(0, 120)}</div>
        <div class="qa-meta">${esc(q.mode)} · ${q.duration_ms}ms · ${esc(q.created_at)}</div>
      </div>`).join("") : '<div class="muted">暂无问答记录，去「智能问答」提问试试</div>';
  }

  /* ---------- 知识库 ---------- */
  async function loadKb() {
    const d = await api("/api/documents");
    const tb = $("#kbTable tbody");
    tb.innerHTML = d.documents.map((doc) => `
      <tr>
        <td><b>${esc(doc.title)}</b><br><span class="muted">${esc(doc.filename || "")}${doc.source === "seed" ? " · 预置" : ""}</span></td>
        <td>${esc(doc.category)}</td>
        <td>${badge(doc.level)}</td>
        <td>${doc.chunk_count}</td>
        <td>${statusBadge(doc.status)}${doc.error ? `<br><span class="muted">${esc(doc.error)}</span>` : ""}</td>
        <td>${esc(doc.updated_at || "")}</td>
        <td>
          ${doc.status !== "ready" ? `<button class="link-btn" onclick="KB.reindex(${doc.id})">重新解析</button>` : ""}
          <button class="link-btn danger" onclick="KB.del(${doc.id})">删除</button>
        </td>
      </tr>`).join("");
  }

  window.KB = {
    async del(id) {
      if (!confirm("确认删除该文档及其全部知识片段？")) return;
      try { await api("/api/documents/" + id, { method: "DELETE" }); loadKb(); }
      catch (e) { alert(e.message); }
    },
    async reindex(id) {
      try { await api(`/api/documents/${id}/reindex`, { method: "POST" }); loadKb(); }
      catch (e) { alert(e.message); }
    }
  };

  async function uploadKb() {
    const f = $("#kbFile").files[0];
    if (!f) { showMsg($("#kbMsg"), "请先选择文件", false); return; }
    const fd = new FormData();
    fd.append("file", f);
    fd.append("title", $("#kbTitle").value);
    fd.append("category", $("#kbCat").value);
    fd.append("level", $("#kbLevel").value);
    $("#kbMsg").className = "msg";
    $("#kbMsg").textContent = "正在上传并解析，请稍候……";
    try {
      const res = await fetch("/api/documents", { method: "POST", body: fd, credentials: "same-origin" });
      const d = await res.json();
      if (!d.success) throw new Error(d.error);
      showMsg($("#kbMsg"), d.message + "（密级：" + $("#kbLevel").value + "）", true);
      $("#kbFile").value = ""; $("#kbTitle").value = "";
      loadKb();
    } catch (e) { showMsg($("#kbMsg"), e.message, false); }
  }

  /* ---------- 智能问答 ---------- */
  let chatHistory = [];
  function loadChatInit() {
    if (!chatHistory.length) {
      $("#chatBox").innerHTML = `
        <div class="chat-item"><div class="bubble a">您好，我是<b>湖企智库</b>智能助手。<br><br>
        我已接入企业本地知识库（DeepSeek 本地推理，数据不出域）。您可以问我：<br>
        · 出差住宿标准是多少？<br>
        · 客户投诉如何处理？<br>
        · SMT 回流焊峰值温度要求？<br>
        · 机密数据可以发给外部供应商吗？</div></div>`;
    } else {
      renderChat();
    }
  }
  function renderChat() {
    const box = $("#chatBox");
    box.innerHTML = chatHistory.map((m) => m.html).join("");
    box.scrollTop = box.scrollHeight;
  }
  function pushBubble(html) {
    chatHistory.push({ html });
    renderChat();
  }
  async function sendChat() {
    const q = $("#chatInput").value.trim();
    if (!q) return;
    const cat = $("#chatCat").value;
    pushBubble(`<div class="chat-item user"><div class="bubble q">${esc(q)}</div></div>`);
    $("#chatInput").value = "";
    const typingId = chatHistory.length;
    pushBubble(`<div class="chat-item" id="typing${typingId}"><div class="bubble a typing"><span></span><span></span><span></span></div></div>`);
    try {
      const d = await api("/api/chat", { method: "POST", body: { question: q, category: cat || null } });
      const srcHtml = d.sources.map((s, i) => `
        <div class="source-card">
          <div class="source-head">📄 引用[${i + 1}] ${esc(s.doc_title)} <span class="source-score">${Math.round(s.score * 100)}%</span>
            <span class="badge ${s.level === "机密" ? "red" : "gray"}">${esc(s.level)}</span></div>
          <div class="source-body">${esc(s.content)}</div>
        </div>`).join("");
      const qaId = d.qa_id || "";
      const html = `<div class="chat-item">
        <div class="bubble a">${esc(d.answer)}</div>
        <div class="answer-meta">模式：${esc(d.mode)} · 检索 ${d.hit_count} 个片段 · 耗时 ${d.duration_ms}ms</div>
        ${srcHtml}
        ${qaId ? `<div class="fb-row">
          <button class="fb-btn" title="回答有帮助" onclick="FB(${qaId}, 5)">👍</button>
          <button class="fb-btn" title="回答不准确" onclick="FB(${qaId}, 1)">👎</button>
        </div>` : ""}
      </div>`;
      const el = document.getElementById("typing" + typingId);
      if (el) el.outerHTML = html; else pushBubble(html);
      chatHistory[chatHistory.length - 1] = { html };
      $("#chatBox").scrollTop = $("#chatBox").scrollHeight;
    } catch (e) {
      const el = document.getElementById("typing" + typingId);
      if (el) el.innerHTML = `<div class="bubble a">出错了：${esc(e.message)}</div>`;
    }
  }

  window.FB = async function (qid, rating) {
    try { await api("/api/qa/" + qid + "/feedback", { method: "POST", body: { rating } }); loadDashboard(); }
    catch (e) {}
  };

  /* ---------- 检索测试 ---------- */
  async function doRetrieve() {
    const q = $("#rtInput").value.trim();
    if (!q) return;
    const d = await api("/api/retrieve", { method: "POST", body: { question: q, category: $("#rtCat").value || null, top_k: 5 } });
    $("#rtResult").innerHTML = d.hits.length ? d.hits.map((h) => `
      <div class="rt-card">
        <div class="rt-head"><span class="rt-doc">${esc(h.doc_title)}</span>
          <span>相似度 <span class="rt-score">${Math.round(h.score * 100)}%</span> · ${badge(h.level)}</span></div>
        <div class="rt-body">${esc(h.content)}</div>
      </div>`).join("") : '<div class="panel">未检索到相关内容，换个关键词试试</div>';
  }

  /* ---------- 审计 ---------- */
  async function loadAudit() {
    const d = await api("/api/audit");
    $("#auditTable tbody").innerHTML = d.logs.map((l) => `
      <tr><td>${esc(l.created_at)}</td><td><b>${esc(l.username)}</b></td>
      <td>${esc(l.action)}</td><td>${esc(l.target)}</td><td class="muted">${esc(l.detail)}</td><td>${esc(l.ip)}</td></tr>`).join("");
  }

  /* ---------- 用户管理 ---------- */
  async function loadUsers() {
    const d = await api("/api/users");
    $("#userTable tbody").innerHTML = d.users.map((u) => `
      <tr>
        <td>${u.id}</td><td><b>${esc(u.username)}</b></td>
        <td>${u.role === "admin" ? `<span class="badge amber">管理员</span>` : `<span class="badge gray">普通用户</span>`}</td>
        <td>${esc(u.dept)}</td>
        <td>${["公开", "内部", "机密"][u.max_level]}</td>
        <td>${esc(u.created_at)}</td>
        <td><button class="link-btn danger" onclick="USERS.del(${u.id}, '${esc(u.username)}')">删除</button></td>
      </tr>`).join("");
  }
  window.USERS = {
    async del(id, name) {
      if (!confirm("确认删除用户 " + name + "？")) return;
      try { await api("/api/users/" + id, { method: "DELETE" }); loadUsers(); }
      catch (e) { alert(e.message); }
    }
  };
  async function addUser() {
    const u = $("#nuUser").value.trim(), p = $("#nuPass").value.trim();
    if (!u || !p) { showMsg($("#nuMsg"), "用户名和密码必填", false); return; }
    try {
      await api("/api/users", { method: "POST", body: { username: u, password: p, role: $("#nuRole").value, dept: $("#nuDept").value.trim() } });
      showMsg($("#nuMsg"), "用户创建成功", true);
      $("#nuUser").value = ""; $("#nuPass").value = ""; $("#nuDept").value = "";
      loadUsers();
    } catch (e) { showMsg($("#nuMsg"), e.message, false); }
  }

  /* ---------- 系统设置 ---------- */
  async function loadSystemMeta() {
    try {
      const sys = await api("/api/system");
      $("#modeChip").textContent = sys.mode === "local" ? "本地推理模式" : "模拟模式";
    } catch (e) {}
  }
  async function loadSystem() {
    const sys = await api("/api/system");
    const dot = (ok) => `<span class="dot ${ok ? "green" : "red"}"></span>`;
    $("#sysDetail").innerHTML = `
      <div>${dot(sys.ollama_ready)} Ollama 服务（${esc(sys.ollama_host)}）：${sys.ollama_ready ? "在线" : "离线"}</div>
      <div>${dot(sys.llm_ready)} 本地大模型（${esc(sys.llm_model)}）：${sys.llm_ready ? "已就绪" : "未检测到"}</div>
      <div>${dot(sys.mode === "local")} Embedding 模型（${esc(sys.embed_model)}）：${sys.mode === "local" ? "本地" : "模拟（内置哈希向量）"}</div>
      <div>${dot(true)} 推理链路：全本地化 · 数据不出域</div>`;
  }
  async function switchMode(mode) {
    try {
      await api("/api/system/mode", { method: "POST", body: { mode } });
      $("#modeChip").textContent = mode === "local" ? "本地推理模式" : "模拟模式";
      loadSystem(); loadDashboard();
    } catch (e) { alert(e.message); }
  }
  async function llmTest() {
    $("#llmTestOut").className = "msg";
    $("#llmTestOut").textContent = "正在请求本地 DeepSeek……";
    try {
      const d = await api("/api/system/llm-test", { method: "POST" });
      $("#llmTestOut").className = "msg ok";
      $("#llmTestOut").textContent = "✅ " + d.reply + "（耗时 " + d.duration_ms + "ms）";
    } catch (e) { $("#llmTestOut").className = "msg err"; $("#llmTestOut").textContent = "❌ " + e.message; }
  }

  /* ---------- 事件绑定 ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    initSession();
    $("#loginBtn").addEventListener("click", async () => {
      const u = $("#loginUser").value.trim(), p = $("#loginPass").value;
      if (!u || !p) { $("#loginMsg").textContent = "请输入账号和密码"; return; }
      try {
        const d = await api("/api/login", { method: "POST", body: { username: u, password: p } });
        currentUser = d.user;
        enterApp();
      } catch (e) { $("#loginMsg").textContent = e.message; }
    });
    $("#loginPass").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#loginBtn").click(); });
    $("#logoutBtn").addEventListener("click", async () => {
      await api("/api/logout", { method: "POST" }).catch(() => {});
      location.reload();
    });
    $$(".nav-item").forEach((el) => el.addEventListener("click", () => switchTab(el.dataset.page)));

    $("#kbUploadBtn").addEventListener("click", uploadKb);
    $("#chatSend").addEventListener("click", sendChat);
    $("#chatInput").addEventListener("keydown", (e) => { if (e.key === "Enter") sendChat(); });
    $("#rtBtn").addEventListener("click", doRetrieve);
    $("#rtInput").addEventListener("keydown", (e) => { if (e.key === "Enter") doRetrieve(); });
    $("#nuBtn").addEventListener("click", addUser);
    $("#llmTestBtn").addEventListener("click", llmTest);
    $$(".sys-row .btn[data-mode]").forEach((b) => b.addEventListener("click", () => switchMode(b.dataset.mode)));
  });
})();
