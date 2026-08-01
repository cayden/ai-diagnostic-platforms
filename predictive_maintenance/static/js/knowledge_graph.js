/* === 知识图谱可视化 - D3 力导向图 === */

let kgSimulation = null;
let kgSvg = null;

async function loadKnowledgeGraph() {
    const data = await API.get('/api/knowledge-graph');
    if (!data.success) return;

    const container = document.getElementById('kgGraph');
    container.innerHTML = '';

    const width = container.clientWidth;
    const height = container.clientHeight;

    kgSvg = d3.select('#kgGraph').append('svg')
        .attr('width', width)
        .attr('height', height);

    // 颜色映射
    const colorMap = {
        category: '#3b82f6',
        equipment: '#10b981',
        sensor: '#06b6d4',
        fault: '#ef4444',
        symptom: '#f59e0b',
        cause: '#a855f7',
        action: '#84cc16',
        strategy: '#ec4899',
    };

    const nodes = data.nodes.map(d => ({ ...d }));
    const links = data.edges.map(d => ({ ...d }));

    // 力模拟
    kgSimulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(d => 80 + Math.random() * 40))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide().radius(d => 25));

    // 连线
    const link = kgSvg.append('g')
        .selectAll('line')
        .data(links)
        .enter().append('line')
        .attr('stroke', '#25304a')
        .attr('stroke-opacity', 0.4)
        .attr('stroke-width', d => Math.sqrt(d.weight) * 1.5);

    // 节点组
    const node = kgSvg.append('g')
        .selectAll('g')
        .data(nodes)
        .enter().append('g')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // 节点圆
    node.append('circle')
        .attr('r', d => {
            const level = d.properties?.level || 2;
            return Math.max(6, 22 - level * 4);
        })
        .attr('fill', d => colorMap[d.type] || '#64748b')
        .attr('stroke', '#111827')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('click', (event, d) => showNodeDetail(d));

    // 节点文字
    node.append('text')
        .text(d => d.name)
        .attr('font-size', d => {
            const level = d.properties?.level || 2;
            return Math.max(9, 16 - level * 2);
        })
        .attr('fill', '#e2e8f0')
        .attr('text-anchor', 'middle')
        .attr('dy', d => {
            const level = d.properties?.level || 2;
            return Math.max(6, 22 - level * 4) + 14;
        })
        .style('pointer-events', 'none')
        .style('font-family', '-apple-system, sans-serif');

    // 悬浮提示
    node.append('title').text(d => `${d.name} (${d.type})`);

    // tick
    kgSimulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        node.attr('transform', d => {
            d.x = Math.max(30, Math.min(width - 30, d.x));
            d.y = Math.max(30, Math.min(height - 30, d.y));
            return `translate(${d.x}, ${d.y})`;
        });
    });

    // 缩放
    const zoom = d3.zoom()
        .scaleExtent([0.3, 3])
        .on('zoom', (event) => {
            kgSvg.selectAll('g').attr('transform', event.transform);
        });
    kgSvg.call(zoom);
}

function dragstarted(event, d) {
    if (!event.active) kgSimulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) kgSimulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

async function showNodeDetail(node) {
    const data = await API.get(`/api/knowledge-graph/node/${node.id}`);
    if (!data.success) return;

    const n = data.node;
    const panel = document.getElementById('kgDetail');

    let html = `<div class="kg-node-info">
        <h4>${n.name}</h4>
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">类型：${n.type}</div>`;

    if (n.properties && Object.keys(n.properties).length > 0) {
        html += '<div style="font-size:12px;margin-bottom:12px">';
        for (const [k, v] of Object.entries(n.properties)) {
            if (k !== 'level') html += `<div><span style="color:var(--text-muted)">${k}:</span> ${v}</div>`;
        }
        html += '</div>';
    }

    if (data.related && data.related.length > 0) {
        html += `<div style="font-size:13px;font-weight:600;margin-top:12px;margin-bottom:8px">关联节点 (${data.related_count})</div>`;
        data.related.forEach(r => {
            html += `<div class="kg-related-item">
                <span style="color:var(--accent-light);cursor:pointer" onclick="showNodeDetail(${JSON.stringify(r.node).replace(/"/g, '&quot;')})">${r.node.name}</span>
                <span style="color:var(--text-muted);float:right;font-size:11px">${r.relation}</span>
            </div>`;
        });
    }

    html += '</div>';
    panel.innerHTML = html;
    panel.classList.add('show');
}

async function searchKnowledgeGraph(keyword) {
    if (!keyword) {
        document.getElementById('kgDetail').classList.remove('show');
        return;
    }

    const data = await API.get(`/api/knowledge-graph/search?q=${encodeURIComponent(keyword)}`);
    if (!data.success) return;

    const panel = document.getElementById('kgDetail');
    if (data.result.length === 0) {
        panel.innerHTML = `<div class="kg-node-info"><h4>未找到匹配节点</h4><p style="color:var(--text-muted)">搜索：${keyword}</p></div>`;
    } else {
        let html = `<div class="kg-node-info">
            <h4>搜索结果 (${data.result.length})</h4>`;
        data.result.forEach(r => {
            const n = r.node;
            html += `<div class="kg-related-item">
                <span style="color:var(--accent-light);cursor:pointer" onclick="showNodeDetail(${JSON.stringify(n).replace(/"/g, '&quot;')})">${n.name}</span>
                <span style="color:var(--text-muted);float:right;font-size:11px">${n.type}</span>
            </div>`;
        });
        html += '</div>';
        panel.innerHTML = html;
    }
    panel.classList.add('show');
}
