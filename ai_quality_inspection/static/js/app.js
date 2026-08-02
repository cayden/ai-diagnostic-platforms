/* ========== AI质检系统 前端逻辑 ========== */

const API = {
    status: "/api/system/status",
    defectClasses: "/api/defect-classes",
    inspect: "/api/inspect",
    batchInspect: "/api/inspect/batch",
    history: "/api/history",
    statsOverview: "/api/stats/overview",
    defectDist: "/api/stats/defect-distribution",
    spc: "/api/stats/spc",
    trend: "/api/stats/trend",
    chat: "/api/chat",
    chatHistory: "/api/chat/history",
    knowledgeGraph: "/api/knowledge-graph",
    systemConfig: "/api/system/config",
};

let defectClassMap = {};
let currentPage = "dashboard";
let historyPage = 1;

// ========== 初始化 ==========
document.addEventListener("DOMContentLoaded", () => {
    loadDefectClasses();
    refreshDashboard();
    loadHistory();
    loadChatHistory();
    initKG();
    // 默认填充批次号
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    document.getElementById("inspectBatch").value = `BATCH-${today}`;
});

function loadDefectClasses() {
    fetch(API.defectClasses)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                data.classes.forEach(c => {
                    defectClassMap[c.code] = c;
                });
            }
        });
}

// ========== 页面切换 ==========
function switchPage(page) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    document.getElementById("page-" + page).classList.add("active");
    document.querySelector(`.nav-item[data-page="${page}"]`).classList.add("active");
    currentPage = page;

    if (page === "dashboard") refreshDashboard();
    if (page === "history") loadHistory();
    if (page === "stats") loadStats();
    if (page === "knowledge") renderKG();
}

// ========== Toast ==========
function showToast(msg, type = "") {
    const toast = document.getElementById("toast");
    toast.textContent = msg;
    toast.className = "toast show " + type;
    setTimeout(() => toast.classList.remove("show"), 3000);
}

// ========== 质检看板 ==========
function refreshDashboard() {
    Promise.all([
        fetch(API.statsOverview + "?days=7").then(r => r.json()),
        fetch(API.trend + "?days=7").then(r => r.json()),
        fetch(API.defectDist + "?days=7").then(r => r.json()),
        fetch(API.spc + "?days=7").then(r => r.json()),
    ]).then(([statsRes, trendRes, distRes, spcRes]) => {
        const s = statsRes.stats;
        document.getElementById("statTotal").textContent = s.total_inspections || 0;
        document.getElementById("statPassed").textContent = s.passed || 0;
        document.getElementById("statFailed").textContent = s.failed || 0;
        document.getElementById("statPassRate").textContent = (s.pass_rate || 0) + "%";
        const totalDef = Object.values(s.severity_totals || {}).reduce((a, b) => a + b, 0);
        document.getElementById("statDefects").textContent = totalDef;

        renderTrendChart(trendRes.trend);
        renderDefectPieChart(distRes.distribution);
        renderSPCChart(spcRes.spc);
        renderLineBarChart(s.line_stats || []);
        renderBatchTable(s.batch_stats || []);
    });
}

function renderTrendChart(trend) {
    const chart = echarts.init(document.getElementById("chartTrend"));
    const dates = trend.map(t => t.date);
    chart.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["合格率", "检测量"] },
        xAxis: { type: "category", data: dates },
        yAxis: [
            { type: "value", name: "合格率(%)", min: 0, max: 100 },
            { type: "value", name: "检测量" },
        ],
        series: [
            { name: "合格率", type: "line", smooth: true, data: trend.map(t => t.pass_rate),
              itemStyle: { color: "#0066cc" }, areaStyle: { opacity: 0.1 } },
            { name: "检测量", type: "bar", yAxisIndex: 1, data: trend.map(t => t.total),
              itemStyle: { color: "#26A69A" } },
        ],
    });
}

function renderDefectPieChart(dist) {
    const chart = echarts.init(document.getElementById("chartDefectPie"));
    const data = dist.map(d => ({
        name: defectClassMap[d.code]?.name || d.code,
        value: d.count,
    }));
    chart.setOption({
        tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
        legend: { bottom: 0, type: "scroll" },
        series: [{
            type: "pie",
            radius: ["40%", "70%"],
            label: { show: true, formatter: "{b}\n{d}%" },
            data: data,
        }],
    });
}

function renderSPCChart(spc) {
    const chart = echarts.init(document.getElementById("chartSPC"));
    const daily = spc.daily || [];
    chart.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["不良率", "UCL", "CL", "LCL"] },
        xAxis: { type: "category", data: daily.map(d => d.date) },
        yAxis: { type: "value", name: "不良率(%)" },
        series: [
            { name: "不良率", type: "line", data: daily.map(d => d.defect_rate),
              itemStyle: { color: "#E53935" }, lineStyle: { width: 2 },
              markLine: { data: [{ yAxis: spc.ucl, name: "UCL" }], lineStyle: { color: "#c62828", type: "dashed" } } },
            { name: "UCL", type: "line", data: daily.map(() => spc.ucl),
              itemStyle: { color: "#c62828" }, lineStyle: { type: "dashed" } },
            { name: "CL", type: "line", data: daily.map(() => spc.cl),
              itemStyle: { color: "#FFA726" }, lineStyle: { type: "dashed" } },
            { name: "LCL", type: "line", data: daily.map(() => spc.lcl),
              itemStyle: { color: "#2e7d32" }, lineStyle: { type: "dashed" } },
        ],
    });
}

function renderLineBarChart(lines) {
    const chart = echarts.init(document.getElementById("chartLineBar"));
    chart.setOption({
        tooltip: { trigger: "axis" },
        xAxis: { type: "category", data: lines.map(l => l.line) },
        yAxis: { type: "value", name: "合格率(%)", min: 0, max: 100 },
        series: [{
            type: "bar",
            data: lines.map(l => ({
                value: l.pass_rate,
                itemStyle: { color: l.pass_rate >= 90 ? "#2e7d32" : l.pass_rate >= 70 ? "#FFA726" : "#c62828" },
            })),
            label: { show: true, position: "top", formatter: "{c}%" },
        }],
    });
}

function renderBatchTable(batches) {
    const tbody = document.querySelector("#batchTable tbody");
    tbody.innerHTML = "";
    if (!batches.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999;">暂无数据</td></tr>';
        return;
    }
    batches.forEach(b => {
        const rateClass = b.pass_rate >= 90 ? "tag-pass" : b.pass_rate >= 70 ? "tag-warn" : "tag-fail";
        tbody.innerHTML += `<tr>
            <td>${b.batch_no}</td><td>${b.total}</td><td>${b.passed}</td><td>${b.failed}</td>
            <td><span class="tag ${rateClass}">${b.pass_rate}%</span></td>
        </tr>`;
    });
}

// ========== 影像检测 ==========
let selectedFile = null;

function handleFileSelect(input) {
    if (input.files.length === 0) return;
    selectedFile = input.files[0];
    const reader = new FileReader();
    reader.onload = (e) => {
        const container = document.getElementById("previewContainer");
        container.innerHTML = `<img src="${e.target.result}" alt="preview">`;
        container.style.display = "block";
        document.getElementById("btnInspect").disabled = false;
    };
    reader.readAsDataURL(selectedFile);
}

// 拖拽上传
const uploadZone = document.getElementById("uploadZone");
if (uploadZone) {
    uploadZone.addEventListener("dragover", (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
    uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files.length) {
            document.getElementById("fileInput").files = e.dataTransfer.files;
            handleFileSelect(document.getElementById("fileInput"));
        }
    });
}

function runInspection() {
    if (!selectedFile) return;
    const btn = document.getElementById("btnInspect");
    btn.disabled = true;
    btn.textContent = "检测中...";
    document.getElementById("inspectResult").innerHTML = '<div style="text-align:center;padding:60px;color:#999;">AI检测分析中...</div>';

    const formData = new FormData();
    formData.append("image", selectedFile);
    formData.append("product_name", document.getElementById("inspectProduct").value);
    formData.append("product_code", document.getElementById("inspectCode").value);
    formData.append("batch_no", document.getElementById("inspectBatch").value);
    formData.append("line", document.getElementById("inspectLine").value);
    formData.append("process", document.getElementById("inspectProcess").value);

    fetch(API.inspect, { method: "POST", body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                renderInspectionResult(data);
                showToast("检测完成", "success");
            } else {
                showToast("检测失败: " + (data.error || "未知错误"), "error");
                document.getElementById("inspectResult").innerHTML = '<div style="text-align:center;padding:40px;color:#c62828;">检测失败</div>';
            }
        })
        .catch(err => {
            showToast("请求失败: " + err, "error");
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = "开始AI检测";
        });
}

function renderInspectionResult(data) {
    const det = data.detection;
    const quality = data.quality_result;
    const analysis = data.analysis;
    const verdictClass = quality.verdict === "PASS" ? "pass" : "fail";
    const verdictIcon = quality.verdict === "PASS" ? "✅" : "❌";

    let html = `<div class="result-card">
        <div class="result-verdict ${verdictClass}">
            <div class="verdict-icon">${verdictIcon}</div>
            <div class="verdict-text">
                <h2>${quality.verdict_label}</h2>
                <p>检出 ${quality.total_defects} 个缺陷 | 严重:${quality.defect_counts.critical} 一般:${quality.defect_counts.major} 轻微:${quality.defect_counts.minor}</p>
            </div>
        </div>
        <div class="detection-canvas-wrapper">
            <canvas id="detCanvas"></canvas>
        </div>`;

    // 缺陷列表
    if (det.detections.length > 0) {
        html += `<div class="defect-list"><h4>缺陷列表 (${det.detections.length})</h4>`;
        det.detections.forEach((d, i) => {
            const sevTag = `tag-${d.severity}`;
            const sevLabel = { critical: "严重", major: "一般", minor: "轻微" }[d.severity] || "";
            html += `<div class="defect-item">
                <div class="defect-color" style="background:${d.color}"></div>
                <div class="defect-info">
                    <strong>${i + 1}. ${d.class_name}</strong>
                    <span class="tag ${sevTag}" style="margin-left:8px;">${sevLabel}</span>
                    <span style="margin-left:8px;color:#666;">置信度: ${(d.confidence * 100).toFixed(1)}%</span>
                </div>
            </div>`;
        });
        html += "</div>";
    }

    // LLM分析
    if (analysis && analysis.summary) {
        html += `<div class="analysis-section">
            <h4>📊 AI分析总结</h4>
            <p>${analysis.summary}</p>
        </div>`;

        if (analysis.risk_assessment) {
            const ra = analysis.risk_assessment;
            const riskColor = ra.level === "high" ? "#c62828" : ra.level === "medium" ? "#FFA726" : "#2e7d32";
            html += `<div class="analysis-section">
                <h4>⚠️ 风险评估: <span class="tag" style="background:${riskColor}20;color:${riskColor}">${ra.label}</span></h4>
                <p>${ra.advice}</p>
            </div>`;
        }

        if (analysis.disposition) {
            const disp = analysis.disposition;
            html += `<div class="analysis-section">
                <h4>🔧 处置建议: ${disp.action_label}</h4>
                <p>${disp.description}</p>
            </div>`;
        }

        if (analysis.root_causes && analysis.root_causes.length) {
            html += `<div class="analysis-section"><h4>🔍 根因分析</h4>`;
            analysis.root_causes.forEach(rc => {
                html += `<div style="margin-bottom:8px;padding:8px;background:#f5f7fa;border-radius:4px;">
                    <strong>${rc.defect_name}</strong> (${rc.count}个)<br>
                    <span style="color:#666;">可能原因: ${rc.possible_causes.join("、")}</span><br>
                    <span style="color:#666;">影响: ${rc.impact}</span>
                </div>`;
            });
            html += "</div>";
        }

        if (analysis.recommendations && analysis.recommendations.length) {
            html += `<div class="analysis-section"><h4>💡 改进建议</h4><ul>`;
            analysis.recommendations.forEach(r => { html += `<li>${r}</li>`; });
            html += "</ul></div>";
        }

        if (analysis.follow_up && analysis.follow_up.length) {
            html += `<div class="analysis-section"><h4>📋 后续行动</h4><ul>`;
            analysis.follow_up.forEach(f => { html += `<li>${f}</li>`; });
            html += "</ul></div>";
        }
    }

    // 耗时
    html += `<div style="margin-top:12px;color:#999;font-size:12px;">检测耗时: ${data.timing.detection}s | 分析耗时: ${data.timing.analysis}s | 总耗时: ${data.timing.total}s</div>`;

    html += "</div>";

    document.getElementById("inspectResult").innerHTML = html;

    // 绘制检测框
    drawDetections(data.image_url, det.detections);
}

function drawDetections(imageUrl, detections) {
    const canvas = document.getElementById("detCanvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
        const maxW = 700;
        let w = img.width, h = img.height;
        if (w > maxW) { h = h * (maxW / w); w = maxW; }
        canvas.width = w;
        canvas.height = h;
        ctx.drawImage(img, 0, 0, w, h);

        // 绘制检测框
        detections.forEach(d => {
            const bx = d.bbox;
            const sx = w / img.width;
            const sy = h / img.height;
            const x1 = bx.x1 * sx, y1 = bx.y1 * sy;
            const x2 = bx.x2 * sx, y2 = bx.y2 * sy;

            // 半透明填充
            ctx.fillStyle = d.color + "30";
            ctx.fillRect(x1, y1, x2 - x1, y2 - y1);

            // 边框
            ctx.strokeStyle = d.color;
            ctx.lineWidth = 2;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

            // 标签
            const label = `${d.class_name} ${(d.confidence * 100).toFixed(0)}%`;
            ctx.font = "bold 13px sans-serif";
            const textW = ctx.measureText(label).width;
            ctx.fillStyle = d.color;
            ctx.fillRect(x1, y1 - 20, textW + 10, 20);
            ctx.fillStyle = "#fff";
            ctx.fillText(label, x1 + 5, y1 - 5);
        });
    };
    img.src = imageUrl;
}

// ========== 检测记录 ==========
function loadHistory() {
    const search = document.getElementById("historySearch").value;
    const verdict = document.getElementById("historyVerdict").value;
    const url = `${API.history}?page=${historyPage}&per_page=15&search=${encodeURIComponent(search)}&verdict=${verdict}`;

    fetch(url).then(r => r.json()).then(data => {
        const tbody = document.querySelector("#historyTable tbody");
        tbody.innerHTML = "";
        if (!data.records.length) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:#999;">暂无记录</td></tr>';
            return;
        }
        data.records.forEach(r => {
            const verdictTag = r.verdict === "PASS" ? "tag-pass" : "tag-fail";
            const riskTag = r.risk_level === "high" ? "tag-fail" : r.risk_level === "medium" ? "tag-warn" : "tag-pass";
            tbody.innerHTML += `<tr>
                <td style="font-size:12px;">${r.record_id}</td>
                <td>${r.product_name}</td>
                <td>${r.batch_no}</td>
                <td>${r.line}</td>
                <td><span class="tag ${verdictTag}">${r.verdict_label}</span></td>
                <td>${r.defect_count}</td>
                <td><span class="tag ${riskTag}">${r.risk_label || "低"}</span></td>
                <td>${(r.total_time || 0).toFixed(2)}s</td>
                <td style="font-size:12px;">${r.created_at?.slice(0, 16).replace("T", " ") || ""}</td>
                <td><button class="btn" style="padding:4px 10px;" onclick="showRecordDetail('${r.record_id}')">详情</button></td>
            </tr>`;
        });

        renderPagination(data.total, data.page, data.per_page);
    });
}

function renderPagination(total, page, perPage) {
    const totalPages = Math.ceil(total / perPage);
    const container = document.getElementById("historyPagination");
    if (totalPages <= 1) { container.innerHTML = ""; return; }

    let html = "";
    html += `<button ${page <= 1 ? "disabled" : ""} onclick="goToPage(${page - 1})">上一页</button>`;
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || Math.abs(i - page) <= 2) {
            html += `<button class="${i === page ? "active" : ""}" onclick="goToPage(${i})">${i}</button>`;
        } else if (Math.abs(i - page) === 3) {
            html += `<button disabled>...</button>`;
        }
    }
    html += `<button ${page >= totalPages ? "disabled" : ""} onclick="goToPage(${page + 1})">下一页</button>`;
    container.innerHTML = html;
}

function goToPage(page) {
    historyPage = page;
    loadHistory();
}

function showRecordDetail(recordId) {
    fetch(`${API.history}/${recordId}`).then(r => r.json()).then(data => {
        if (!data.success) return;
        const r = data.record;
        const det = r.detection_result || {};
        const quality = r.quality_result || {};
        const analysis = r.analysis_result || {};
        const verdictClass = quality.verdict === "PASS" ? "tag-pass" : "tag-fail";

        let html = `<div style="display:flex;gap:20px;flex-wrap:wrap;">
            <div style="flex:1;min-width:300px;">
                <h3 style="margin-bottom:12px;">基本信息</h3>
                <table class="data-table" style="margin-bottom:16px;">
                    <tr><td>记录ID</td><td>${r.record_id}</td></tr>
                    <tr><td>产品</td><td>${r.product_name}</td></tr>
                    <tr><td>批次号</td><td>${r.batch_no}</td></tr>
                    <tr><td>产线</td><td>${r.line}</td></tr>
                    <tr><td>工序</td><td>${r.process}</td></tr>
                    <tr><td>判定</td><td><span class="tag ${verdictClass}">${quality.verdict_label}</span></td></tr>
                    <tr><td>缺陷数</td><td>${quality.total_defects || 0}</td></tr>
                    <tr><td>检测时间</td><td>${r.created_at?.slice(0, 19).replace("T", " ") || ""}</td></tr>
                </table>
                <h3 style="margin-bottom:12px;">检测图片</h3>
                <img src="/api/image/${r.image_filename}" style="max-width:100%;border-radius:4px;border:1px solid #e0e0e0;">
            </div>
            <div style="flex:1;min-width:300px;">
                <h3 style="margin-bottom:12px;">缺陷详情</h3>`;

        if (det.detections && det.detections.length) {
            det.detections.forEach((d, i) => {
                html += `<div class="defect-item" style="margin-bottom:6px;">
                    <div class="defect-color" style="background:${d.color}"></div>
                    <div class="defect-info">
                        <strong>${i + 1}. ${d.class_name}</strong>
                        <span class="tag tag-${d.severity}" style="margin-left:8px;">${d.severity}</span>
                        <span style="margin-left:8px;">置信度: ${(d.confidence * 100).toFixed(1)}%</span>
                    </div>
                </div>`;
            });
        } else {
            html += "<p>无缺陷检出</p>";
        }

        if (analysis.summary) {
            html += `<h3 style="margin:16px 0 8px;">AI分析</h3>
                <p style="margin-bottom:8px;">${analysis.summary}</p>`;
            if (analysis.disposition) {
                html += `<p><strong>处置: ${analysis.disposition.action_label}</strong> - ${analysis.disposition.description}</p>`;
            }
        }

        html += "</div></div>";
        document.getElementById("modalBody").innerHTML = html;
        document.getElementById("recordModal").classList.add("active");
    });
}

function closeModal() {
    document.getElementById("recordModal").classList.remove("active");
}

// ========== 质量统计 ==========
function loadStats() {
    const days = document.getElementById("statsDays").value;
    Promise.all([
        fetch(API.statsOverview + `?days=${days}`).then(r => r.json()),
        fetch(API.trend + `?days=${days}`).then(r => r.json()),
        fetch(API.defectDist + `?days=${days}`).then(r => r.json()),
        fetch(API.spc + `?days=${days}`).then(r => r.json()),
    ]).then(([statsRes, trendRes, distRes, spcRes]) => {
        const s = statsRes.stats;
        const cards = document.getElementById("statsCards");
        const totalDef = Object.values(s.severity_totals || {}).reduce((a, b) => a + b, 0);
        cards.innerHTML = `
            <div class="stat-card"><div class="stat-icon">📷</div><div class="stat-value">${s.total_inspections || 0}</div><div class="stat-label">总检测数</div></div>
            <div class="stat-card pass"><div class="stat-icon">✅</div><div class="stat-value">${s.passed || 0}</div><div class="stat-label">合格</div></div>
            <div class="stat-card fail"><div class="stat-icon">❌</div><div class="stat-value">${s.failed || 0}</div><div class="stat-label">不合格</div></div>
            <div class="stat-card rate"><div class="stat-icon">📊</div><div class="stat-value">${s.pass_rate || 0}%</div><div class="stat-label">合格率</div></div>
            <div class="stat-card warn"><div class="stat-icon">⚠️</div><div class="stat-value">${totalDef}</div><div class="stat-label">缺陷总数</div></div>
        `;

        renderStatsTrendChart(trendRes.trend);
        renderSeverityChart(s.severity_totals);
        renderTopDefectsChart(distRes.distribution);
        renderBatchRankChart(s.batch_stats);
    });
}

function renderStatsTrendChart(trend) {
    const chart = echarts.init(document.getElementById("chartStatsTrend"));
    chart.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["合格", "不合格", "合格率"] },
        xAxis: { type: "category", data: trend.map(t => t.date) },
        yAxis: [
            { type: "value", name: "数量" },
            { type: "value", name: "合格率(%)", min: 0, max: 100 },
        ],
        series: [
            { name: "合格", type: "bar", stack: "total", data: trend.map(t => t.passed), itemStyle: { color: "#2e7d32" } },
            { name: "不合格", type: "bar", stack: "total", data: trend.map(t => t.failed), itemStyle: { color: "#c62828" } },
            { name: "合格率", type: "line", yAxisIndex: 1, smooth: true, data: trend.map(t => t.pass_rate), itemStyle: { color: "#0066cc" } },
        ],
    });
}

function renderSeverityChart(severity) {
    const chart = echarts.init(document.getElementById("chartSeverity"));
    chart.setOption({
        tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
        series: [{
            type: "pie",
            radius: "60%",
            data: [
                { name: "严重", value: severity.critical || 0, itemStyle: { color: "#c62828" } },
                { name: "一般", value: severity.major || 0, itemStyle: { color: "#1565c0" } },
                { name: "轻微", value: severity.minor || 0, itemStyle: { color: "#FFA726" } },
            ],
            label: { formatter: "{b}: {c}" },
        }],
    });
}

function renderTopDefectsChart(dist) {
    const chart = echarts.init(document.getElementById("chartTopDefects"));
    const top5 = dist.slice(0, 5);
    chart.setOption({
        tooltip: { trigger: "axis" },
        xAxis: { type: "category", data: top5.map(d => defectClassMap[d.code]?.name || d.code), axisLabel: { rotate: 30 } },
        yAxis: { type: "value" },
        series: [{
            type: "bar",
            data: top5.map((d, i) => ({
                value: d.count,
                itemStyle: { color: ["#E53935", "#FF7043", "#FFA726", "#9CCC65", "#26A69A"][i] },
            })),
            label: { show: true, position: "top" },
        }],
    });
}

function renderBatchRankChart(batches) {
    const chart = echarts.init(document.getElementById("chartBatchRank"));
    chart.setOption({
        tooltip: { trigger: "axis" },
        xAxis: { type: "category", data: batches.map(b => b.batch_no), axisLabel: { rotate: 30 } },
        yAxis: { type: "value", name: "合格率(%)", min: 0, max: 100 },
        series: [{
            type: "bar",
            data: batches.map(b => ({
                value: b.pass_rate,
                itemStyle: { color: b.pass_rate >= 90 ? "#2e7d32" : b.pass_rate >= 70 ? "#FFA726" : "#c62828" },
            })),
            label: { show: true, position: "top", formatter: "{c}%" },
        }],
    });
}

// ========== AI 问答 ==========
function sendChat() {
    const input = document.getElementById("chatInput");
    const message = input.value.trim();
    if (!message) return;
    input.value = "";

    addChatMessage("user", message);

    fetch(API.chat, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
    }).then(r => r.json()).then(data => {
        if (data.success) {
            addChatMessage("bot", data.response.content);
        }
    });
}

function quickAsk(question) {
    document.getElementById("chatInput").value = question;
    sendChat();
}

function addChatMessage(role, content) {
    const messages = document.getElementById("chatMessages");
    const avatar = role === "user" ? "👤" : "🤖";
    const div = document.createElement("div");
    div.className = `chat-message ${role}`;
    div.innerHTML = `<div class="msg-avatar">${avatar}</div><div class="msg-content">${content}</div>`;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function loadChatHistory() {
    fetch(API.chatHistory).then(r => r.json()).then(data => {
        if (!data.success || !data.history.length) return;
        const messages = document.getElementById("chatMessages");
        // 保留欢迎语
        data.history.reverse().forEach(h => {
            addChatMessage("user", h.message);
            addChatMessage("bot", h.response.content);
        });
    });
}

// ========== 系统设置 ==========
function saveSettings() {
    const data = {
        detection_mode: document.getElementById("setDetMode").value,
        llm_mode: document.getElementById("setLlmMode").value,
    };
    const apiKey = document.getElementById("setApiKey").value;
    if (apiKey) data.llm_api_key = apiKey;

    const conf = parseFloat(document.getElementById("setConf").value);
    if (conf) data.conf_threshold = conf;

    fetch(API.systemConfig, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    }).then(r => r.json()).then(res => {
        if (res.success) {
            showToast("配置已保存", "success");
        } else {
            showToast("保存失败", "error");
        }
    });
}
