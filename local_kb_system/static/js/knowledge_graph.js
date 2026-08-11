/* 湖企智库 - 知识图谱力导向图（零依赖实现，离线可用） */
(function () {
  let data = { nodes: [], edges: [] };
  const svgNS = "http://www.w3.org/2000/svg";
  let svg, W = 900, H = 520, running = false, dragNode = null;

  const RADIUS = { document: 17, topic: 13, entity: 9 };
  const COLOR = { document: "#0A1330", topic: "#2563EB", entity: "#D9A441" };

  function $(id) { return document.getElementById(id); }

  async function load() {
    if (running) return;
    running = true;
    try {
      const res = await fetch("/api/graph", { credentials: "same-origin" });
      const d = await res.json();
      if (!d.success) throw new Error(d.error || "加载失败");
      if (!d.nodes.length) {
        $("graphSvg").innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#9AA1B5" font-size="14">暂无知识数据，请先上传文档</text>';
        return;
      }
      data = d;
      initPhysics();
      render();
    } catch (e) {
      $("graphSvg").innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#C0392B" font-size="14">图谱加载失败：' + e.message + "</text>";
    } finally { running = false; }
  }

  function initPhysics() {
    const n = data.nodes;
    const cx = W / 2, cy = H / 2;
    n.forEach((node, i) => {
      if (node.x == null) {
        const ang = (i / Math.max(1, n.length)) * Math.PI * 2;
        const r = 60 + (i % 5) * 38;
        node.x = cx + Math.cos(ang) * r;
        node.y = cy + Math.sin(ang) * r;
      }
      node.vx = 0; node.vy = 0;
    });
    // 预计算邻接（加速）
    const adj = {};
    data.edges.forEach((e) => {
      (adj[e.source] = adj[e.source] || []).push(e.target);
      (adj[e.target] = adj[e.target] || []).push(e.source);
    });
    data._adj = adj;
  }

  function tick() {
    const n = data.nodes, adj = data._adj;
    const EPS = 0.001;
    for (let i = 0; i < n.length; i++) {
      for (let j = i + 1; j < n.length; j++) {
        let dx = n[j].x - n[i].x, dy = n[j].y - n[i].y;
        let d2 = dx * dx + dy * dy + EPS;
        let d = Math.sqrt(d2);
        let f = 2600 / d2; // 斥力
        dx /= d; dy /= d;
        n[i].vx -= dx * f; n[i].vy -= dy * f;
        n[j].vx += dx * f; n[j].vy += dy * f;
      }
    }
    // 引力
    data.edges.forEach((e) => {
      const a = nodeById(e.source), b = nodeById(e.target);
      if (!a || !b) return;
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy + EPS);
      const f = (d - 70) * 0.02 * (e.weight || 1);
      a.vx += (dx / d) * f; a.vy += (dy / d) * f;
      b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
    });
    // 向心力 + 积分
    n.forEach((node) => {
      node.vx += (W / 2 - node.x) * 0.008;
      node.vy += (H / 2 - node.y) * 0.008;
      node.x += node.vx; node.y += node.vy;
      node.vx *= 0.85; node.vy *= 0.85;
      node.x = Math.max(30, Math.min(W - 30, node.x));
      node.y = Math.max(25, Math.min(H - 25, node.y));
    });
  }

  function nodeById(id) {
    return data._map ? data._map[id] : (data._map = {}, data.nodes.forEach((x) => data._map[x.id] = x), data._map[id]);
  }

  function render() {
    svg = $("graphSvg");
    svg.innerHTML = "";
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    data._map = null;
    data._map = {};
    data.nodes.forEach((x) => data._map[x.id] = x);

    data.edges.forEach((e) => {
      const a = data._map[e.source], b = data._map[e.target];
      if (!a || !b) return;
      const line = document.createElementNS(svgNS, "line");
      line.setAttribute("x1", a.x); line.setAttribute("y1", a.y);
      line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
      line.setAttribute("stroke", "#CBD2E4");
      line.setAttribute("stroke-width", (e.weight > 1 ? 1.8 : 1));
      svg.appendChild(line);
    });

    data.nodes.forEach((node) => {
      const g = document.createElementNS(svgNS, "g");
      const circle = document.createElementNS(svgNS, "circle");
      circle.setAttribute("cx", node.x); circle.setAttribute("cy", node.y);
      circle.setAttribute("r", RADIUS[node.type] || 10);
      circle.setAttribute("fill", COLOR[node.type] || "#888");
      circle.setAttribute("stroke", "#fff");
      circle.setAttribute("stroke-width", "2");
      const label = document.createElementNS(svgNS, "text");
      label.setAttribute("x", node.x); label.setAttribute("y", node.y - (RADIUS[node.type] || 10) - 5);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("font-size", "11");
      label.setAttribute("fill", "#4B5563");
      label.textContent = node.label.length > 9 ? node.label.slice(0, 9) + "…" : node.label;
      g.appendChild(circle); g.appendChild(label);
      g.style.cursor = "grab";
      g.addEventListener("mousedown", (ev) => startDrag(ev, node));
      svg.appendChild(g);
    });
  }

  function startDrag(ev, node) {
    ev.preventDefault();
    dragNode = node;
    svg.style.cursor = "grabbing";
  }
  function moveDrag(ev) {
    if (!dragNode) return;
    const rect = svg.getBoundingClientRect();
    const scale = W / rect.width;
    dragNode.x = Math.max(30, Math.min(W - 30, (ev.clientX - rect.left) * scale));
    dragNode.y = Math.max(25, Math.min(H - 25, (ev.clientY - rect.top) * scale));
    dragNode.vx = 0; dragNode.vy = 0;
    render();
  }
  function endDrag() { dragNode = null; svg.style.cursor = ""; }

  function animate() {
    if (!document.getElementById("page-graph").classList.contains("active")) return;
    for (let i = 0; i < 12; i++) tick();
    render();
    requestAnimationFrame(animate);
  }

  let animStarted = false;
  window.KGraph = {
    load,
    start() {
      if (!animStarted) {
        animStarted = true;
        requestAnimationFrame(animate);
      }
    }
  };
  document.addEventListener("DOMContentLoaded", () => {
    svg = $("graphSvg");
    svg.addEventListener("mousemove", moveDrag);
    window.addEventListener("mouseup", endDrag);
  });
})();
