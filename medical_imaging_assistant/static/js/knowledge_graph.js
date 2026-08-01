/* ==================== 知识图谱可视化 ==================== */
const KG = {
    nodes: [],
    edges: [],
    canvas: null,
    ctx: null,
    simNodes: [],
    simEdges: [],
    hoveredNode: null,
    selectedNode: null,
    dragging: null,
    offsetX: 0,
    offsetY: 0,
    isPanning: false,
    zoom: 1,
    centerX: 0,
    centerY: 0,
    animationId: null,
};

const KG_NODE_STYLES = {
    disease:    { color: '#ef4444', radius: 22, icon: 'D' },
    symptom:    { color: '#f59e0b', radius: 16, icon: 'S' },
    exam:       { color: '#3b82f6', radius: 18, icon: 'E' },
    feature:    { color: '#8b5cf6', radius: 16, icon: 'F' },
    treatment:  { color: '#10b981', radius: 18, icon: 'T' },
    risk_factor:{ color: '#ec4899', radius: 15, icon: 'R' },
};

const KG_NODE_LABELS = {
    disease: '疾病',
    symptom: '症状',
    exam: '检查方法',
    feature: '影像特征',
    treatment: '治疗方法',
    risk_factor: '风险因素',
};

function initKnowledgeGraph() {
    if (KG.canvas) return; // 已初始化

    const container = document.getElementById('kgGraph');
    const canvas = document.createElement('canvas');
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    container.appendChild(canvas);
    KG.canvas = canvas;
    KG.ctx = canvas.getContext('2d');

    // 加载数据
    fetch('/api/knowledge-graph')
        .then(r => r.json())
        .then(data => {
            KG.nodes = data.nodes;
            KG.edges = data.edges;
            setupSimulation();
            startSimulation();
            renderLegend();
        });

    // 事件
    canvas.addEventListener('mousedown', onMouseDown);
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('mouseleave', onMouseUp);
    canvas.addEventListener('click', onCanvasClick);
    canvas.addEventListener('wheel', onWheel, { passive: false });

    // 窗口大小变化
    window.addEventListener('resize', () => {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        KG.centerX = canvas.width / 2;
        KG.centerY = canvas.height / 2;
    });
}

function setupSimulation() {
    const canvas = KG.canvas;
    KG.centerX = canvas.width / 2;
    KG.centerY = canvas.height / 2;

    // 初始化节点位置（圆形分布）
    KG.simNodes = KG.nodes.map((node, i) => {
        const angle = (i / KG.nodes.length) * Math.PI * 2;
        const r = Math.min(canvas.width, canvas.height) * 0.35;
        return {
            ...node,
            x: KG.centerX + Math.cos(angle) * r + (Math.random() - 0.5) * 30,
            y: KG.centerY + Math.sin(angle) * r + (Math.random() - 0.5) * 30,
            vx: 0, vy: 0,
            fx: null, fy: null,
        };
    });

    // 构建边引用
    const nodeMap = {};
    KG.simNodes.forEach(n => { nodeMap[n.id] = n; });

    KG.simEdges = KG.edges.map(e => ({
        source: nodeMap[e.source],
        target: nodeMap[e.target],
        relation: e.relation,
    })).filter(e => e.source && e.target);
}

function startSimulation() {
    if (KG.animationId) cancelAnimationFrame(KG.animationId);

    function tick() {
        stepSimulation();
        renderGraph();
        KG.animationId = requestAnimationFrame(tick);
    }
    tick();
}

function stepSimulation() {
    const nodes = KG.simNodes;
    const edges = KG.simEdges;
    const k = 0.02; // 弹簧强度
    const repulsion = 8000; // 斥力
    const centerForce = 0.005;
    const damping = 0.85;

    // 斥力
    for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
            const dx = nodes[j].x - nodes[i].x;
            const dy = nodes[j].y - nodes[i].y;
            let dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 1) dist = 1;
            const force = repulsion / (dist * dist);
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (nodes[i].fx === null) { nodes[i].vx -= fx; nodes[i].vy -= fy; }
            if (nodes[j].fx === null) { nodes[j].vx += fx; nodes[j].vy += fy; }
        }
    }

    // 弹簧（边吸引力）
    const linkDist = 120;
    for (const edge of edges) {
        const dx = edge.target.x - edge.source.x;
        const dy = edge.target.y - edge.source.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 1) dist = 1;
        const force = (dist - linkDist) * k;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (edge.source.fx === null) { edge.source.vx += fx; edge.source.vy += fy; }
        if (edge.target.fx === null) { edge.target.vx -= fx; edge.target.vy -= fy; }
    }

    // 中心引力
    for (const node of nodes) {
        if (node.fx !== null) continue;
        node.vx += (KG.centerX - node.x) * centerForce;
        node.vy += (KG.centerY - node.y) * centerForce;
        node.vx *= damping;
        node.vy *= damping;
        node.x += node.vx;
        node.y += node.vy;

        // 边界
        const margin = 30;
        if (node.x < margin) { node.x = margin; node.vx = 0; }
        if (node.x > KG.canvas.width - margin) { node.x = KG.canvas.width - margin; node.vx = 0; }
        if (node.y < margin) { node.y = margin; node.vy = 0; }
        if (node.y > KG.canvas.height - margin) { node.y = KG.canvas.height - margin; node.vy = 0; }
    }
}

function renderGraph() {
    const ctx = KG.ctx;
    const canvas = KG.canvas;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 背景
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 绘制边
    for (const edge of KG.simEdges) {
        const isHighlight = KG.selectedNode &&
            (KG.selectedNode.id === edge.source.id || KG.selectedNode.id === edge.target.id);

        ctx.beginPath();
        ctx.moveTo(edge.source.x, edge.source.y);
        ctx.lineTo(edge.target.x, edge.target.y);

        if (isHighlight) {
            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 2;
        } else {
            ctx.strokeStyle = '#cbd5e1';
            ctx.lineWidth = 1;
        }
        ctx.stroke();

        // 关系标签（高亮时显示）
        if (isHighlight) {
            const mx = (edge.source.x + edge.target.x) / 2;
            const my = (edge.source.y + edge.target.y) / 2;
            ctx.font = '10px Inter, sans-serif';
            ctx.fillStyle = '#64748b';
            ctx.textAlign = 'center';
            ctx.fillText(edge.relation, mx, my - 4);
        }
    }

    // 绘制节点
    for (const node of KG.simNodes) {
        const style = KG_NODE_STYLES[node.type] || KG_NODE_STYLES.disease;
        const isHovered = KG.hoveredNode && KG.hoveredNode.id === node.id;
        const isSelected = KG.selectedNode && KG.selectedNode.id === node.id;
        const r = style.radius * (isHovered || isSelected ? 1.2 : 1);

        // 阴影
        if (isHovered || isSelected) {
            ctx.shadowColor = style.color;
            ctx.shadowBlur = 15;
        }

        // 圆
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = style.color;
        ctx.fill();

        ctx.shadowBlur = 0;

        // 边框
        ctx.strokeStyle = isSelected ? '#fff' : 'rgba(255,255,255,.3)';
        ctx.lineWidth = isSelected ? 3 : 1;
        ctx.stroke();

        // 类型图标
        ctx.fillStyle = '#fff';
        ctx.font = `bold ${r * 0.6}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(style.icon, node.x, node.y);

        // 标签
        ctx.font = `${isHovered || isSelected ? 'bold ' : ''}11px Inter, sans-serif`;
        ctx.fillStyle = isHovered || isSelected ? style.color : '#475569';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        // 文本截断
        let label = node.label;
        if (label.length > 6) label = label.substring(0, 6) + '...';
        ctx.fillText(label, node.x, node.y + r + 4);
    }
}

function getNodeAt(x, y) {
    for (const node of KG.simNodes) {
        const style = KG_NODE_STYLES[node.type] || KG_NODE_STYLES.disease;
        const dx = x - node.x;
        const dy = y - node.y;
        if (dx * dx + dy * dy <= style.radius * style.radius) {
            return node;
        }
    }
    return null;
}

function onMouseDown(e) {
    const rect = KG.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const node = getNodeAt(x, y);
    if (node) {
        KG.dragging = node;
        node.fx = node.x;
        node.fy = node.y;
        KG.canvas.style.cursor = 'grabbing';
    } else {
        KG.isPanning = true;
        KG.offsetX = x;
        KG.offsetY = y;
        KG.canvas.style.cursor = 'grabbing';
    }
}

function onMouseMove(e) {
    const rect = KG.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (KG.dragging) {
        KG.dragging.x = x;
        KG.dragging.y = y;
        KG.dragging.fx = x;
        KG.dragging.fy = y;
    } else if (KG.isPanning) {
        // 平移所有节点
        const dx = x - KG.offsetX;
        const dy = y - KG.offsetY;
        for (const node of KG.simNodes) {
            node.x += dx;
            node.y += dy;
        }
        KG.centerX += dx;
        KG.centerY += dy;
        KG.offsetX = x;
        KG.offsetY = y;
    } else {
        const node = getNodeAt(x, y);
        KG.hoveredNode = node;
        KG.canvas.style.cursor = node ? 'pointer' : 'grab';
    }
}

function onMouseUp() {
    if (KG.dragging) {
        KG.dragging.fx = null;
        KG.dragging.fy = null;
        KG.dragging = null;
    }
    KG.isPanning = false;
    KG.canvas.style.cursor = 'grab';
}

function onCanvasClick(e) {
    const rect = KG.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const node = getNodeAt(x, y);
    if (node) {
        KG.selectedNode = node;
        showNodeDetail(node.id);
    } else {
        KG.selectedNode = null;
        document.getElementById('kgDetail').innerHTML =
            '<div class="kg-detail-placeholder">点击节点查看详情</div>';
    }
}

function onWheel(e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const rect = KG.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    for (const node of KG.simNodes) {
        node.x = mx + (node.x - mx) * delta;
        node.y = my + (node.y - my) * delta;
    }
    KG.centerX = mx + (KG.centerX - mx) * delta;
    KG.centerY = my + (KG.centerY - my) * delta;
}

async function showNodeDetail(nodeId) {
    const resp = await fetch(`/api/knowledge-graph/node/${nodeId}`);
    const data = await resp.json();
    if (data.success) {
        const node = data.node;
        const style = KG_NODE_STYLES[node.type] || KG_NODE_STYLES.disease;
        let html = `<div class="kg-detail-title" style="color:${style.color}">${node.label}</div>`;
        html += `<div class="kg-detail-type">${KG_NODE_LABELS[node.type]} · ${node.category}</div>`;
        html += `<div class="kg-detail-desc">${node.description}</div>`;

        // 关联节点
        const outgoing = node.related.filter(r => r.direction === 'outgoing');
        const incoming = node.related.filter(r => r.direction === 'incoming');

        if (outgoing.length > 0) {
            html += '<div class="kg-detail-section"><h5>关联（指出）</h5>';
            outgoing.forEach(r => {
                const s = KG_NODE_STYLES[r.node.type] || KG_NODE_STYLES.disease;
                html += `<div class="kg-relation-item">
                    <span style="color:${s.color};font-weight:600;">${r.node.label}</span>
                    <span class="kg-relation-arrow">←</span>
                    <span style="font-size:11px;color:var(--text-muted);">${r.relation}</span>
                </div>`;
            });
            html += '</div>';
        }

        if (incoming.length > 0) {
            html += '<div class="kg-detail-section"><h5>关联（指入）</h5>';
            incoming.forEach(r => {
                const s = KG_NODE_STYLES[r.node.type] || KG_NODE_STYLES.disease;
                html += `<div class="kg-relation-item">
                    <span class="kg-relation-name" style="color:${s.color};">${r.node.label}</span>
                    <span class="kg-relation-arrow">→</span>
                    <span style="font-size:11px;color:var(--text-muted);">${r.relation}</span>
                </div>`;
            });
            html += '</div>';
        }

        document.getElementById('kgDetail').innerHTML = html;
    }
}

function searchKG() {
    const keyword = document.getElementById('kgSearch').value;
    if (!keyword) { resetKG(); return; }

    fetch(`/api/knowledge-graph/search?q=${encodeURIComponent(keyword)}`)
        .then(r => r.json())
        .then(data => {
            const result = data.result;
            // 更新图
            KG.nodes = result.nodes;
            KG.edges = result.edges;
            setupSimulation();
        });
}

function resetKG() {
    document.getElementById('kgSearch').value = '';
    fetch('/api/knowledge-graph')
        .then(r => r.json())
        .then(data => {
            KG.nodes = data.nodes;
            KG.edges = data.edges;
            setupSimulation();
        });
}

function renderLegend() {
    const legend = document.getElementById('kgLegend');
    let html = '';
    for (const [type, label] of Object.entries(KG_NODE_LABELS)) {
        const style = KG_NODE_STYLES[type];
        html += `<div class="legend-item">
            <span class="legend-dot" style="background:${style.color}"></span>
            <span>${label}</span>
        </div>`;
    }
    legend.innerHTML = html;
}
