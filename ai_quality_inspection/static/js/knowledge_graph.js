/* ========== 缺陷知识图谱 力导向图可视化 ========== */

let kgNodes = [];
let kgEdges = [];
let kgSimulation = null;
let kgSvgEl = null;
let kgWidth = 0;
let kgHeight = 0;

// 节点颜色映射
const kgTypeColors = {
    defect: "#E53935",
    cause: "#FF9800",
    process: "#2196F3",
    disposition: "#9C27B0",
    prevention: "#4CAF50",
    method: "#00BCD4",
};

const kgTypeLabels = {
    defect: "缺陷类型",
    cause: "成因",
    process: "工序",
    disposition: "处置方案",
    prevention: "预防措施",
    method: "检测方法",
};

function initKG() {
    // 在页面加载时预取数据
    fetch(API.knowledgeGraph)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                kgNodes = data.nodes || [];
                kgEdges = data.edges || [];
            }
        });
}

function renderKG() {
    if (kgNodes.length === 0) {
        fetch(API.knowledgeGraph)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    kgNodes = data.nodes || [];
                    kgEdges = data.edges || [];
                    drawKG();
                }
            });
    } else {
        drawKG();
    }
}

function drawKG() {
    kgSvgEl = document.getElementById("kgSvg");
    const wrapper = kgSvgEl.parentElement;
    kgWidth = wrapper.clientWidth;
    kgHeight = wrapper.clientHeight;

    kgSvgEl.setAttribute("viewBox", `0 0 ${kgWidth} ${kgHeight}`);
    kgSvgEl.innerHTML = "";

    // 清空旧数据，复制一份避免修改原始数据
    const nodes = kgNodes.map(n => ({ ...n }));
    const edges = kgEdges.map(e => ({ ...e }));

    // 初始化节点位置
    nodes.forEach((n, i) => {
        const angle = (i / nodes.length) * Math.PI * 2;
        const radius = Math.min(kgWidth, kgHeight) * 0.35;
        n.x = kgWidth / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 50;
        n.y = kgHeight / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 50;
        n.vx = 0;
        n.vy = 0;
    });

    // 构建邻接表
    const adj = {};
    nodes.forEach(n => { adj[n.id] = []; });
    edges.forEach(e => {
        if (adj[e.source]) adj[e.source].push(e.target);
        if (adj[e.target]) adj[e.target].push(e.source);
    });

    // 创建SVG元素
    const svgNS = "http://www.w3.org/2000/svg";

    // 定义箭头
    const defs = document.createElementNS(svgNS, "defs");
    defs.innerHTML = `
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#999" />
        </marker>
    `;
    kgSvgEl.appendChild(defs);

    // 边组
    const edgeGroup = document.createElementNS(svgNS, "g");
    edgeGroup.setAttribute("id", "kg-edges");
    kgSvgEl.appendChild(edgeGroup);

    // 节点组
    const nodeGroup = document.createElementNS(svgNS, "g");
    nodeGroup.setAttribute("id", "kg-nodes");
    kgSvgEl.appendChild(nodeGroup);

    // 绘制边
    const edgeElements = [];
    edges.forEach(e => {
        const line = document.createElementNS(svgNS, "line");
        line.setAttribute("stroke", "#ddd");
        line.setAttribute("stroke-width", "1");
        edgeGroup.appendChild(line);
        edgeElements.push({ el: line, source: e.source, target: e.target, relation: e.relation });
    });

    // 绘制节点
    const nodeElements = [];
    nodes.forEach(n => {
        const g = document.createElementNS(svgNS, "g");
        g.style.cursor = "pointer";
        g.setAttribute("data-id", n.id);

        const radius = n.type === "defect" ? 20 : 14;
        const color = n.color || kgTypeColors[n.type] || "#999";

        const circle = document.createElementNS(svgNS, "circle");
        circle.setAttribute("r", radius);
        circle.setAttribute("fill", color);
        circle.setAttribute("opacity", "0.85");
        circle.setAttribute("stroke", "#fff");
        circle.setAttribute("stroke-width", "2");
        g.appendChild(circle);

        const text = document.createElementNS(svgNS, "text");
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("dy", radius + 14);
        text.setAttribute("font-size", "11px");
        text.setAttribute("fill", "#333");
        text.textContent = n.name;
        g.appendChild(text);

        // 点击事件
        g.addEventListener("click", () => showKGNodeDetail(n.id));

        // 拖拽
        g.addEventListener("mousedown", (event) => {
            event.preventDefault();
            const startX = event.clientX;
            const startY = event.clientY;
            const origX = n.x;
            const origY = n.y;

            const onMove = (ev) => {
                const dx = ev.clientX - startX;
                const dy = ev.clientY - startY;
                n.x = origX + dx;
                n.y = origY + dy;
                n.vx = 0;
                n.vy = 0;
                updatePositions();
            };
            const onUp = () => {
                document.removeEventListener("mousemove", onMove);
                document.removeEventListener("mouseup", onUp);
            };
            document.addEventListener("mousemove", onMove);
            document.addEventListener("mouseup", onUp);
        });

        nodeGroup.appendChild(g);
        nodeElements.push({ el: g, node: n, circle, text });
    });

    // 力导向模拟
    function tick() {
        // 斥力
        nodes.forEach(a => {
            nodes.forEach(b => {
                if (a.id === b.id) return;
                const dx = a.x - b.x;
                const dy = a.y - b.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const minDist = 60;
                if (dist < 120) {
                    const force = (120 - dist) / dist * 0.5;
                    a.vx += dx * force * 0.1;
                    a.vy += dy * force * 0.1;
                }
            });
        });

        // 引力 (边)
        edges.forEach(e => {
            const s = nodes.find(n => n.id === e.source);
            const t = nodes.find(n => n.id === e.target);
            if (!s || !t) return;
            const dx = t.x - s.x;
            const dy = t.y - s.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const ideal = 100;
            const force = (dist - ideal) * 0.01;
            s.vx += dx / dist * force;
            s.vy += dy / dist * force;
            t.vx -= dx / dist * force;
            t.vy -= dy / dist * force;
        });

        // 中心引力
        nodes.forEach(n => {
            n.vx += (kgWidth / 2 - n.x) * 0.001;
            n.vy += (kgHeight / 2 - n.y) * 0.001;
        });

        // 更新位置
        nodes.forEach(n => {
            n.vx *= 0.85;
            n.vy *= 0.85;
            n.x += n.vx;
            n.y += n.vy;

            // 边界约束
            n.x = Math.max(30, Math.min(kgWidth - 30, n.x));
            n.y = Math.max(30, Math.min(kgHeight - 30, n.y));
        });

        updatePositions();
    }

    function updatePositions() {
        // 更新节点位置
        nodeElements.forEach(({ el, node }) => {
            el.setAttribute("transform", `translate(${node.x},${node.y})`);
        });
        // 更新边
        edgeElements.forEach(({ el, source, target }) => {
            const s = nodes.find(n => n.id === source);
            const t = nodes.find(n => n.id === target);
            if (s && t) {
                el.setAttribute("x1", s.x);
                el.setAttribute("y1", s.y);
                el.setAttribute("x2", t.x);
                el.setAttribute("y2", t.y);
            }
        });
    }

    // 运行模拟
    let tickCount = 0;
    const maxTicks = 300;
    function runSimulation() {
        tick();
        tickCount++;
        if (tickCount < maxTicks) {
            requestAnimationFrame(runSimulation);
        }
    }
    runSimulation();

    // 图例
    const legend = document.createElementNS(svgNS, "g");
    legend.setAttribute("transform", "translate(10, 10)");
    let ly = 0;
    Object.entries(kgTypeLabels).forEach(([type, label]) => {
        const color = kgTypeColors[type];
        const lc = document.createElementNS(svgNS, "rect");
        lc.setAttribute("x", 0);
        lc.setAttribute("y", ly);
        lc.setAttribute("width", 12);
        lc.setAttribute("height", 12);
        lc.setAttribute("fill", color);
        lc.setAttribute("rx", 2);
        legend.appendChild(lc);

        const lt = document.createElementNS(svgNS, "text");
        lt.setAttribute("x", 18);
        lt.setAttribute("y", ly + 10);
        lt.setAttribute("font-size", "11px");
        lt.setAttribute("fill", "#666");
        lt.textContent = label;
        legend.appendChild(lt);

        ly += 20;
    });
    kgSvgEl.appendChild(legend);
}

function showKGNodeDetail(nodeId) {
    fetch(`${API.knowledgeGraph}/node/${nodeId}`)
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const node = data.node;
            const related = data.related || [];

            const detailEl = document.getElementById("kgDetail");
            const typeLabel = kgTypeLabels[node.type] || node.type;
            const color = node.color || kgTypeColors[node.type] || "#999";

            let html = `<div style="margin-bottom:16px;">
                <span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:${color};margin-right:6px;"></span>
                <strong style="font-size:16px;">${node.name}</strong>
                <span style="margin-left:8px;color:#999;font-size:12px;">${typeLabel}</span>
            </div>`;

            if (node.description) {
                html += `<p style="margin-bottom:12px;color:#666;">${node.description}</p>`;
            }

            // 节点属性
            const props = { ...node };
            delete props.id; delete props.type; delete props.name; delete props.description;
            delete props.color; delete props.severity;
            if (Object.keys(props).length) {
                html += "<div style='margin-bottom:12px;'><strong>属性:</strong><br>";
                for (const [k, v] of Object.entries(props)) {
                    html += `<span style="color:#666;">${k}: ${v}</span><br>`;
                }
                html += "</div>";
            }

            // 关联节点
            if (related.length) {
                html += `<div style="margin-top:12px;"><strong>关联节点 (${related.length}):</strong></div>`;
                related.forEach(r => {
                    const relType = kgTypeLabels[r.node.type] || r.node.type;
                    const relColor = r.node.color || kgTypeColors[r.node.type] || "#999";
                    const direction = r.direction === "outgoing" ? "→" : "←";
                    html += `<div class="kg-related-item" style="cursor:pointer;" onclick="showKGNodeDetail('${r.node.id}')">
                        <span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${relColor};margin-right:4px;"></span>
                        <span class="rel-name">${r.node.name}</span>
                        <span class="rel-type" style="margin-left:4px;">(${relType}) ${direction} ${r.relation}</span>
                    </div>`;
                });
            }

            detailEl.innerHTML = html;
        });
}

function searchKG(keyword) {
    if (!keyword) {
        // 重置高亮
        document.querySelectorAll("#kg-nodes circle").forEach(c => {
            c.setAttribute("opacity", "0.85");
        });
        return;
    }
    // 高亮匹配的节点
    kgNodes.forEach((n, i) => {
        const g = document.querySelector(`#kg-nodes g[data-id="${n.id}"]`);
        if (!g) return;
        const circle = g.querySelector("circle");
        if (n.name.includes(keyword) || (n.code && n.code.includes(keyword))) {
            circle.setAttribute("opacity", "1");
            circle.setAttribute("stroke", "#FFD700");
            circle.setAttribute("stroke-width", "3");
        } else {
            circle.setAttribute("opacity", "0.3");
            circle.setAttribute("stroke", "#fff");
            circle.setAttribute("stroke-width", "1");
        }
    });
}

function resetKGView() {
    drawKG();
    document.getElementById("kgSearch").value = "";
    document.getElementById("kgDetail").innerHTML = "<h3>节点详情</h3><p class='hint'>点击图谱中的节点查看详情</p>";
}
