/* === 预测性维护平台 - 主应用 JS === */

const API = {
    get: (url) => fetch(url).then(r => r.json()),
    post: (url, data) => fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    }).then(r => r.json()),
    postForm: (url, formData) => fetch(url, {
        method: 'POST',
        body: formData,
    }).then(r => r.json()),
};

let autoRefresh = true;
let refreshTimer = null;
let currentEquipmentId = null;
let healthDistChart = null;
let alertStatsChart = null;

// === 页面切换 ===
function switchPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');

    if (page === 'overview') loadOverview();
    else if (page === 'equipment') loadEquipment();
    else if (page === 'alerts') loadAlerts();
    else if (page === 'workorders') loadWorkOrders();
    else if (page === 'diagnosis') loadDiagnosisPage();
    else if (page === 'knowledge') loadKnowledgeGraph();
    else if (page === 'settings') loadSettings();
}

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => switchPage(item.dataset.page));
});

// === Toast ===
function showToast(msg, type = '') {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast ' + type;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
}

// === 模态框 ===
function openModal(title, bodyHtml) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = bodyHtml;
    document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// === 健康度颜色 ===
function healthColor(h) {
    if (h >= 85) return 'health-excellent';
    if (h >= 70) return 'health-good';
    if (h >= 50) return 'health-warning';
    if (h >= 30) return 'health-critical';
    return 'health-failed';
}

function healthColorHex(h) {
    if (h >= 85) return '#10b981';
    if (h >= 70) return '#84cc16';
    if (h >= 50) return '#f59e0b';
    if (h >= 30) return '#ef4444';
    return '#dc2626';
}

// === 总览 ===
async function loadOverview() {
    const data = await API.get('/api/analysis/overview');
    if (!data.success) return;
    const ov = data.overview;

    // KPI
    const kpiHtml = `
        <div class="kpi-card k-blue">
            <div class="kpi-label">设备总数</div>
            <div class="kpi-value">${ov.total_equipment}</div>
            <div class="kpi-sub">运行中 ${ov.running_equipment} | 停机 ${ov.stopped_equipment} | 维护 ${ov.maintenance_equipment}</div>
        </div>
        <div class="kpi-card k-green">
            <div class="kpi-label">平均健康度</div>
            <div class="kpi-value" style="color:${healthColorHex(ov.avg_health)}">${ov.avg_health.toFixed(0)}</div>
            <div class="kpi-sub">全设备平均</div>
        </div>
        <div class="kpi-card k-orange">
            <div class="kpi-label">待处理告警</div>
            <div class="kpi-value">${ov.alert_stats.emergency + ov.alert_stats.critical + ov.alert_stats.warning}</div>
            <div class="kpi-sub">紧急 ${ov.alert_stats.emergency} | 严重 ${ov.alert_stats.critical} | 警告 ${ov.alert_stats.warning}</div>
        </div>
        <div class="kpi-card k-red">
            <div class="kpi-label">待处理工单</div>
            <div class="kpi-value">${ov.work_order_stats.pending + (ov.work_order_stats.in_progress || 0)}</div>
            <div class="kpi-sub">已完成 ${ov.work_order_stats.completed} | 已取消 ${ov.work_order_stats.cancelled}</div>
        </div>
    `;
    document.getElementById('kpiRow').innerHTML = kpiHtml;

    // 健康度分布图
    if (!healthDistChart) {
        healthDistChart = echarts.init(document.getElementById('healthDistChart'));
    }
    const hd = ov.health_distribution;
    healthDistChart.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, textStyle: { color: '#94a3b8' } },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            color: ['#10b981', '#84cc16', '#f59e0b', '#ef4444', '#dc2626'],
            data: [
                { value: hd.excellent, name: '优秀(≥85)' },
                { value: hd.good, name: '良好(70-85)' },
                { value: hd.warning, name: '警告(50-70)' },
                { value: hd.critical, name: '危险(30-50)' },
                { value: hd.failed, name: '故障(<30)' },
            ],
            label: { color: '#e2e8f0' },
        }],
    });

    // 告警统计图
    if (!alertStatsChart) {
        alertStatsChart = echarts.init(document.getElementById('alertStatsChart'));
    }
    alertStatsChart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: '10%', right: '5%', top: '10%', bottom: '15%' },
        xAxis: { type: 'category', data: ['紧急', '严重', '警告', '信息'], axisLabel: { color: '#94a3b8' } },
        yAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
        series: [{
            type: 'bar',
            data: [
                { value: ov.alert_stats.emergency, itemStyle: { color: '#dc2626' } },
                { value: ov.alert_stats.critical, itemStyle: { color: '#ef4444' } },
                { value: ov.alert_stats.warning, itemStyle: { color: '#f59e0b' } },
                { value: ov.alert_stats.info, itemStyle: { color: '#06b6d4' } },
            ],
            barWidth: '40%',
        }],
    });

    // 设备概览
    const eqData = await API.get('/api/equipment');
    if (eqData.success) {
        document.getElementById('equipmentOverview').innerHTML = eqData.equipment.map(eq => renderEquipmentCard(eq)).join('');
    }

    // 最近告警
    if (ov.recent_alerts && ov.recent_alerts.length > 0) {
        document.getElementById('recentAlertsTable').innerHTML = renderAlertsTable(ov.recent_alerts);
    } else {
        document.getElementById('recentAlertsTable').innerHTML = '<div class="empty-state">暂无告警</div>';
    }
}

// === 设备卡片 ===
function renderEquipmentCard(eq) {
    const health = eq.health_score || 100;
    const latest = eq.latest_data;
    const sensors = latest ? latest.sensors : {};
    const statusText = { running: '运行中', stopped: '已停机', maintenance: '维护中' }[eq.status] || eq.status;

    const sensorTags = Object.entries(sensors).map(([type, val]) => {
        const thresholds = { vibration: 7, temperature: 80, current: 32, pressure: 1.6, acoustic: 85, flow_rate: 60 };
        const danger = { vibration: 11.2, temperature: 95, current: 40, pressure: 2.0, acoustic: 95, flow_rate: 40 };
        let cls = '';
        if (danger[type] && val >= danger[type]) cls = 'danger';
        else if (thresholds[type] && val >= thresholds[type]) cls = 'abnormal';
        const units = { vibration: 'mm/s', temperature: '°C', current: 'A', pressure: 'MPa', rpm: 'RPM', flow_rate: 'L/min', acoustic: 'dB' };
        return `<span class="eq-sensor-tag ${cls}">${type}: ${val}${units[type] || ''}</span>`;
    }).join('');

    return `
        <div class="eq-card" onclick="showEquipmentDetail('${eq.equipment_id}')">
            <div class="eq-card-header">
                <div>
                    <div class="eq-name">${eq.name}</div>
                    <div class="eq-meta">${eq.equipment_id} | ${eq.location || ''}</div>
                </div>
                <span class="eq-status status-${eq.status}">${statusText}</span>
            </div>
            <div class="eq-health-bar">
                <div class="eq-health-fill ${healthColor(health)}" style="width:${health}%"></div>
            </div>
            <div class="eq-health-label">
                <span>健康度</span>
                <span style="color:${healthColorHex(health)};font-weight:700">${health.toFixed(0)}/100</span>
            </div>
            <div class="eq-sensors">${sensorTags}</div>
        </div>
    `;
}

// === 设备列表 ===
async function loadEquipment() {
    const data = await API.get('/api/equipment');
    if (!data.success) return;
    document.getElementById('equipmentList').innerHTML = data.equipment.map(eq => renderEquipmentCard(eq)).join('') ||
        '<div class="empty-state">暂无设备</div>';
}

// === 设备详情 ===
async function showEquipmentDetail(equipmentId) {
    currentEquipmentId = equipmentId;
    switchPage('equipment-detail');
    const data = await API.get(`/api/equipment/${equipmentId}`);
    if (!data.success) return;

    const eq = data.equipment;
    document.getElementById('detailTitle').textContent = `${eq.name} - 设备详情`;

    const latest = data.latest_data;
    const sensors = latest ? latest.sensors : {};
    const detection = data.detection || {};
    const health = eq.health_score || 100;

    const sensorUnits = { vibration: 'mm/s', temperature: '°C', current: 'A', pressure: 'MPa', rpm: 'RPM', flow_rate: 'L/min', acoustic: 'dB' };
    const sensorThresholds = {
        vibration: { normal: 4.5, warn: 7, danger: 11.2 },
        temperature: { normal: 65, warn: 80, danger: 95 },
        current: { normal: 25, warn: 32, danger: 40 },
        pressure: { normal: 1.2, warn: 1.6, danger: 2.0 },
        rpm: { normal: 1600, warn: 1750 },
        flow_rate: { normal: 120, warn: 140 },
        acoustic: { normal: 75, warn: 85, danger: 95 },
    };

    const sensorCards = Object.entries(sensors).map(([type, val]) => {
        const th = sensorThresholds[type] || {};
        let cls = '';
        if (th.danger && val >= th.danger) cls = 'danger';
        else if (th.warn && val >= th.warn) cls = 'abnormal';
        const pct = th.normal ? Math.min(100, (val / th.danger) * 100) : 50;
        const barColor = cls === 'danger' ? '#ef4444' : cls === 'abnormal' ? '#f59e0b' : '#10b981';
        return `
            <div class="sensor-card ${cls}">
                <div class="sensor-name">${type}</div>
                <div class="sensor-value">${val}<span class="sensor-unit">${sensorUnits[type] || ''}</span></div>
                <div class="sensor-bar"><div class="sensor-bar-fill" style="width:${pct}%;background:${barColor}"></div></div>
            </div>
        `;
    }).join('');

    // 传感器曲线图
    const sensorHistory = data.sensor_history || [];
    const chartData = {};
    sensorHistory.forEach(d => {
        Object.entries(d.sensors || {}).forEach(([type, val]) => {
            if (!chartData[type]) chartData[type] = [];
            chartData[type].push(val);
        });
    });

    const riskNames = { low: '低风险', moderate: '中风险', high: '高风险', critical: '危险', imminent: '即将故障' };
    const riskColors = { low: '#10b981', moderate: '#84cc16', high: '#f59e0b', critical: '#ef4444', imminent: '#dc2626' };
    const riskLevel = detection.risk_level || 'low';

    // 健康度趋势
    const healthTrend = data.health_trend || [];
    const healthData = healthTrend.map(h => h.health);

    // RUL
    const rul = detection.rul_hours;
    const rulConf = detection.rul_confidence || 0;
    let rulClass = 'safe';
    if (rul !== null && rul !== undefined) {
        if (rul < 24) rulClass = 'danger';
        else if (rul < 72) rulClass = 'warning';
    }

    const statusText = { running: '运行中', stopped: '已停机', maintenance: '维护中' }[eq.status] || eq.status;

    let html = `
        <div class="card">
            <div class="card-body">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px">
                    <div>
                        <div style="font-size:18px;font-weight:700;margin-bottom:4px">${eq.name}</div>
                        <div style="color:var(--text-secondary);font-size:13px">
                            ${eq.equipment_id} | ${eq.type} | ${eq.location || ''}<br>
                            ${eq.manufacturer || ''} ${eq.model || ''} | 额定功率: ${eq.rated_power || '-'} | 安装日期: ${eq.install_date || '-'}
                        </div>
                    </div>
                    <div style="display:flex;gap:8px">
                        <span class="eq-status status-${eq.status}">${statusText}</span>
                        ${eq.status === 'running' ? `<button class="btn btn-sm btn-warning" onclick="controlEquipment('${eq.equipment_id}', 'stop')">停机</button>` : ''}
                        ${eq.status === 'stopped' ? `<button class="btn btn-sm btn-success" onclick="controlEquipment('${eq.equipment_id}', 'start')">启动</button>` : ''}
                        <button class="btn btn-sm" onclick="controlEquipment('${eq.equipment_id}', 'maintenance')">维护</button>
                        <button class="btn btn-sm btn-primary" onclick="resetEquipment('${eq.equipment_id}')">重置</button>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
                    <div style="text-align:center">
                        <div style="font-size:12px;color:var(--text-secondary)">健康度</div>
                        <div style="font-size:36px;font-weight:800;color:${healthColorHex(health)}">${health.toFixed(0)}</div>
                        <div class="eq-health-bar" style="margin-top:8px">
                            <div class="eq-health-fill ${healthColor(health)}" style="width:${health}%"></div>
                        </div>
                    </div>
                    <div style="text-align:center">
                        <div style="font-size:12px;color:var(--text-secondary)">风险等级</div>
                        <div style="font-size:24px;font-weight:700;color:${riskColors[riskLevel] || '#94a3b8'};margin-top:8px">${riskNames[riskLevel] || '未知'}</div>
                    </div>
                    <div style="text-align:center">
                        <div style="font-size:12px;color:var(--text-secondary)">RUL 预测</div>
                        <div style="font-size:24px;font-weight:700;color:${rul === null ? '#94a3b8' : (rulClass === 'danger' ? '#ef4444' : rulClass === 'warning' ? '#f59e0b' : '#10b981')};margin-top:8px">
                            ${rul !== null && rul !== undefined ? rul.toFixed(0) + 'h' : '稳定'}
                        </div>
                        ${rul !== null ? `<div style="font-size:11px;color:var(--text-muted)">置信度 ${rulConf}%</div>` : ''}
                    </div>
                </div>
                ${detection.summary ? `<div style="margin-top:16px;padding:12px;background:var(--bg-panel);border-radius:6px;font-size:13px;color:var(--text-secondary);border-left:3px solid ${riskColors[riskLevel] || '#3b82f6'}">${detection.summary}</div>` : ''}
            </div>
        </div>

        <div class="card">
            <div class="card-header"><h3>传感器实时数据</h3></div>
            <div class="card-body">
                <div class="sensor-grid">${sensorCards}</div>
            </div>
        </div>

        <div class="card">
            <div class="card-header"><h3>传感器趋势曲线</h3></div>
            <div class="card-body">
                <div id="sensorTrendChart" class="chart-container" style="height:350px"></div>
            </div>
        </div>

        <div class="overview-grid">
            <div class="card">
                <div class="card-header"><h3>健康度趋势</h3></div>
                <div class="card-body">
                    <div id="healthTrendChart" class="chart-container" style="height:200px"></div>
                </div>
            </div>
            <div class="card">
                <div class="card-header"><h3>AI 分析与诊断</h3></div>
                <div class="card-body" id="diagPanel">加载中...</div>
            </div>
        </div>
    `;

    document.getElementById('equipmentDetailContent').innerHTML = html;

    // 绘制传感器趋势图
    const chart = echarts.init(document.getElementById('sensorTrendChart'));
    const series = Object.entries(chartData).map(([type, vals]) => ({
        name: type,
        type: 'line',
        data: vals,
        smooth: true,
        showSymbol: false,
    }));
    chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { top: 0, textStyle: { color: '#94a3b8' } },
        grid: { left: '8%', right: '5%', top: '15%', bottom: '10%' },
        xAxis: { type: 'category', data: sensorHistory.map((_, i) => i), axisLabel: { color: '#94a3b8' } },
        yAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
        series: series,
    });

    // 健康度趋势图
    const hChart = echarts.init(document.getElementById('healthTrendChart'));
    hChart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: '8%', right: '5%', top: '10%', bottom: '10%' },
        xAxis: { type: 'category', data: healthData.map((_, i) => i), axisLabel: { color: '#94a3b8' } },
        yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#94a3b8' } },
        series: [{
            type: 'line',
            data: healthData,
            smooth: true,
            showSymbol: false,
            areaStyle: { color: {
                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: 'rgba(59,130,246,0.3)' }, { offset: 1, color: 'rgba(59,130,246,0)' }],
            }},
            lineStyle: { color: '#3b82f6', width: 2 },
        }],
    });

    // 加载诊断信息
    loadDiagnosis(eq.equipment_id, eq.type);

    // 自动刷新
    if (refreshTimer) clearInterval(refreshTimer);
    if (autoRefresh && eq.status === 'running') {
        refreshTimer = setInterval(() => {
            if (document.getElementById('page-equipment-detail').classList.contains('active')) {
                showEquipmentDetail(currentEquipmentId);
            }
        }, 5000);
    }
}

// === 诊断面板 ===
async function loadDiagnosis(equipmentId, equipmentType) {
    const panel = document.getElementById('diagPanel');
    const data = await API.get(`/api/analysis/${equipmentId}`);
    if (!data.success) { panel.innerHTML = '诊断失败'; return; }

    const diag = data.fault_diagnosis;
    const rul = data.rul_prediction;

    let html = '';

    // RUL
    if (rul.rul_hours !== null && rul.rul_hours !== undefined) {
        const rulClass = rul.rul_hours < 24 ? 'danger' : rul.rul_hours < 72 ? 'warning' : 'safe';
        html += `
            <div class="rul-card" style="margin-bottom:12px">
                <div class="rul-label">剩余使用寿命预测 (RUL)</div>
                <div class="rul-value ${rulClass}">${rul.rul_hours.toFixed(0)}<span class="rul-unit">小时</span></div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:4px">
                    置信度 ${rul.confidence}% | 退化率 ${rul.degradation_rate}
                    ${rul.estimated_failure_time ? `| 预计 ${rul.estimated_failure_time}` : ''}
                </div>
                <div class="rul-recommendation">${rul.recommendation}</div>
            </div>
        `;
    }

    // 故障诊断
    if (diag.fault_type) {
        html += `
            <div class="diag-result">
                <div class="diag-fault-name" style="color:${diag.confidence > 0.6 ? '#ef4444' : '#f59e0b'}">${diag.fault_name}</div>
                <div style="font-size:13px;color:var(--text-secondary)">${diag.stage || ''} | 置信度 ${diag.confidence}%</div>
                <div class="diag-confidence-bar">
                    <div class="diag-confidence-fill" style="width:${diag.confidence * 100}%"></div>
                </div>
                <div style="font-size:13px;color:var(--text-secondary);white-space:pre-line;margin-top:8px">${diag.description}</div>
            </div>
        `;

        if (diag.all_candidates && diag.all_candidates.length > 1) {
            html += '<div class="diag-candidates"><div style="font-size:12px;color:var(--text-muted);margin-bottom:6px">其他可能故障</div>';
            diag.all_candidates.slice(1).forEach(c => {
                html += `<div class="diag-candidate"><span>${c.fault_name}</span><span style="color:var(--text-muted)">${c.score}</span></div>`;
            });
            html += '</div>';
        }

        if (diag.recommendations && diag.recommendations.length > 0) {
            html += '<div style="margin-top:12px"><div style="font-size:13px;font-weight:600;margin-bottom:6px">维修建议</div><ul class="diag-recommendations">';
            diag.recommendations.forEach(r => { html += `<li>${r}</li>`; });
            html += '</ul></div>';
        }
    } else {
        html += '<div class="empty-state" style="padding:24px">设备运行正常，未检测到故障征兆</div>';
    }

    panel.innerHTML = html;
}

// === 诊断页面 ===
async function loadDiagnosisPage() {
    const eqData = await API.get('/api/equipment');
    if (!eqData.success) return;

    const eqOptions = eqData.equipment.map(eq =>
        `<option value="${eq.equipment_id}">${eq.name}</option>`).join('');

    document.getElementById('diagnosisContent').innerHTML = `
        <div class="card">
            <div class="card-header"><h3>故障诊断</h3></div>
            <div class="card-body">
                <div style="display:flex;gap:12px;margin-bottom:16px">
                    <select id="diagEqSelect" class="form-select" style="max-width:300px">${eqOptions}</select>
                    <button class="btn btn-primary" onclick="runDiagnosis()">开始诊断</button>
                </div>
                <div id="diagResultArea"></div>
            </div>
        </div>
    `;
}

async function runDiagnosis() {
    const eqId = document.getElementById('diagEqSelect').value;
    if (!eqId) return;
    const data = await API.get(`/api/diagnosis/${eqId}`);
    if (!data.success) return;
    const diag = data.diagnosis;

    let html = '';
    if (diag.fault_type) {
        html += `
            <div class="diag-result">
                <div class="diag-fault-name" style="color:${diag.confidence > 0.6 ? '#ef4444' : '#f59e0b'}">${diag.fault_name}</div>
                <div style="font-size:13px;color:var(--text-secondary)">${diag.stage || ''} | 置信度 ${(diag.confidence * 100).toFixed(0)}%</div>
                <div class="diag-confidence-bar"><div class="diag-confidence-fill" style="width:${diag.confidence * 100}%"></div></div>
                <div style="font-size:13px;color:var(--text-secondary);white-space:pre-line;margin-top:8px">${diag.description}</div>
            </div>
        `;
        if (diag.recommendations) {
            html += '<div style="margin-top:12px"><div style="font-size:13px;font-weight:600;margin-bottom:6px">维修建议</div><ul class="diag-recommendations">';
            diag.recommendations.forEach(r => { html += `<li>${r}</li>`; });
            html += '</ul></div>';
        }
    } else {
        html += '<div class="empty-state">设备运行正常</div>';
    }
    document.getElementById('diagResultArea').innerHTML = html;
}

// === 告警 ===
async function loadAlerts() {
    const level = document.getElementById('alertFilter').value;
    const ack = document.getElementById('alertAckFilter').value;
    const url = `/api/alerts?per_page=50${level ? '&level=' + level : ''}${ack ? '&acknowledged=' + ack : ''}`;
    const data = await API.get(url);
    if (!data.success) return;

    if (data.alerts.length === 0) {
        document.getElementById('alertsList').innerHTML = '<div class="empty-state">暂无告警</div>';
        return;
    }

    document.getElementById('alertsList').innerHTML = data.alerts.map(a => {
        const levelNames = { emergency: '紧急', critical: '严重', warning: '警告', info: '信息' };
        return `
            <div class="alert-item level-${a.level}">
                <div class="alert-header">
                    <div class="alert-title">
                        <span class="alert-badge badge-${a.level}">${levelNames[a.level] || a.level}</span>
                        ${a.fault_name || '告警'}
                    </div>
                    <div style="font-size:12px;color:var(--text-muted)">${a.created_at}</div>
                </div>
                <div class="alert-body">
                    ${a.description || ''}
                    ${a.rul_hours ? `<br><span style="color:var(--warning)">RUL 预测：${a.rul_hours.toFixed(0)} 小时</span>` : ''}
                </div>
                <div class="alert-meta">
                    <span>设备：${a.equipment_name || a.equipment_id}</span>
                    <span>健康度：${a.health_score ? a.health_score.toFixed(0) : '-'}</span>
                    ${a.acknowledged ? '<span style="color:var(--success)">已确认</span>' : '<span style="color:var(--warning)">未确认</span>'}
                </div>
                ${a.recommendations && a.recommendations.length > 0 ? `
                    <div style="margin-top:10px;font-size:12px;color:var(--text-secondary)">
                        <strong>建议：</strong>${a.recommendations.slice(0, 2).join('；')}
                    </div>
                ` : ''}
                ${!a.acknowledged ? `
                    <div class="alert-actions">
                        <button class="btn btn-sm btn-success" onclick="acknowledgeAlert('${a.alert_id}')">确认告警</button>
                        <button class="btn btn-sm" onclick="showEquipmentDetail('${a.equipment_id}')">查看设备</button>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

async function acknowledgeAlert(alertId) {
    await API.post(`/api/alerts/${alertId}/acknowledge`, { handler: '运维人员' });
    showToast('告警已确认', 'success');
    loadAlerts();
}

// === 工单 ===
async function loadWorkOrders() {
    const status = document.getElementById('orderStatusFilter').value;
    const url = `/api/work-orders?per_page=50${status ? '&status=' + status : ''}`;
    const data = await API.get(url);
    if (!data.success) return;

    if (data.orders.length === 0) {
        document.getElementById('workOrdersList').innerHTML = '<div class="empty-state">暂无工单</div>';
        return;
    }

    const statusNames = { pending: '待处理', in_progress: '进行中', completed: '已完成', cancelled: '已取消' };
    const priorityNames = { urgent: '紧急', high: '高', medium: '中', low: '低' };

    document.getElementById('workOrdersList').innerHTML = data.orders.map(o => `
        <div class="order-item">
            <div class="order-header">
                <div>
                    <strong>${o.order_id}</strong>
                    <span style="margin-left:8px;color:var(--text-secondary)">${o.equipment_name || o.equipment_id}</span>
                </div>
                <div style="display:flex;gap:6px">
                    <span class="priority-badge p-${o.priority}">${priorityNames[o.priority] || o.priority}</span>
                    <span class="order-status-badge os-${o.status}">${statusNames[o.status] || o.status}</span>
                </div>
            </div>
            <div style="font-size:13px;color:var(--text-secondary);margin-bottom:8px">
                ${o.fault_name || ''} ${o.description || ''}
            </div>
            ${o.recommendations && o.recommendations.length > 0 ? `
                <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">
                    <strong>建议：</strong>${o.recommendations.join('；')}
                </div>
            ` : ''}
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div style="font-size:12px;color:var(--text-muted)">
                    ${o.technician ? '维修人：' + o.technician : ''} ${o.completed_at ? '完成于 ' + o.completed_at : '创建于 ' + o.created_at}
                </div>
                ${o.status === 'pending' || o.status === 'in_progress' ? `
                    <div style="display:flex;gap:6px">
                        ${o.status === 'pending' ? `<button class="btn btn-sm btn-primary" onclick="updateOrder('${o.order_id}', 'in_progress')">开始维修</button>` : ''}
                        <button class="btn btn-sm btn-success" onclick="completeOrder('${o.order_id}')">完成</button>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

async function updateOrder(orderId, status) {
    await API.post(`/api/work-orders/${orderId}/update`, { status });
    showToast('工单状态已更新', 'success');
    loadWorkOrders();
}

async function completeOrder(orderId) {
    openModal('完成工单', `
        <div class="form-group">
            <label class="form-label">维修人</label>
            <input type="text" id="orderTech" class="form-input" placeholder="维修人员姓名">
        </div>
        <div class="form-group">
            <label class="form-label">维修结果</label>
            <textarea id="orderResult" class="form-input" rows="4" placeholder="维修结果描述"></textarea>
        </div>
        <div style="text-align:right">
            <button class="btn btn-success" onclick="submitCompleteOrder('${orderId}')">确认完成</button>
        </div>
    `);
}

async function submitCompleteOrder(orderId) {
    const tech = document.getElementById('orderTech').value;
    const result = document.getElementById('orderResult').value;
    await API.post(`/api/work-orders/${orderId}/update`, { status: 'completed', technician: tech, result });
    closeModal();
    showToast('工单已完成', 'success');
    loadWorkOrders();
}

// === 设备控制 ===
async function controlEquipment(equipmentId, action) {
    await API.post(`/api/equipment/${equipmentId}/control`, { action });
    showToast(`设备已${action === 'start' ? '启动' : action === 'stop' ? '停机' : '进入维护'}`, 'success');
    if (currentEquipmentId === equipmentId) {
        showEquipmentDetail(equipmentId);
    }
}

async function resetEquipment(equipmentId) {
    await API.post(`/api/system/reset-equipment/${equipmentId}`, {});
    showToast('设备已重置为健康状态', 'success');
    showEquipmentDetail(equipmentId);
}

// === 注入故障 ===
function injectFaultDialog() {
    const faultOptions = [
        { code: 'bearing_wear', name: '轴承磨损' },
        { code: 'imbalance', name: '转子不平衡' },
        { code: 'misalignment', name: '轴系不对中' },
        { code: 'overload', name: '过载运行' },
        { code: 'lubrication_failure', name: '润滑失效' },
        { code: 'cavitation', name: '气蚀' },
        { code: 'seal_failure', name: '密封失效' },
        { code: 'electrical_fault', name: '电气故障' },
    ];

    openModal('注入故障（演示用）', `
        <div class="form-group">
            <label class="form-label">选择设备</label>
            <select id="injectEq" class="form-select"></select>
        </div>
        <div class="form-group">
            <label class="form-label">故障类型</label>
            <select id="injectFault" class="form-select">
                ${faultOptions.map(f => `<option value="${f.code}">${f.name}</option>`).join('')}
            </select>
        </div>
        <div class="form-group">
            <label class="form-label">严重程度: <span id="sevVal">0.5</span></label>
            <input type="range" id="injectSev" min="0.1" max="1.0" step="0.1" value="0.5" style="width:100%" oninput="document.getElementById('sevVal').textContent=this.value">
        </div>
        <div style="text-align:right">
            <button class="btn btn-primary" onclick="submitInjectFault()">注入故障</button>
        </div>
    `);

    API.get('/api/equipment').then(data => {
        if (data.success) {
            document.getElementById('injectEq').innerHTML = data.equipment
                .map(e => `<option value="${e.equipment_id}">${e.name}</option>`).join('');
        }
    });
}

async function submitInjectFault() {
    const eqId = document.getElementById('injectEq').value;
    const fault = document.getElementById('injectFault').value;
    const sev = parseFloat(document.getElementById('injectSev').value);
    const data = await API.post('/api/system/inject-fault', {
        equipment_id: eqId, fault_type: fault, severity: sev,
    });
    closeModal();
    if (data.success) {
        showToast(`已注入故障，系统将自动检测并预警`, 'warning');
        setTimeout(() => loadOverview(), 5000);
    } else {
        showToast('注入失败', 'error');
    }
}

// === 添加设备 ===
function showAddEquipmentDialog() {
    openModal('添加设备', `
        <div class="form-group"><label class="form-label">设备名称</label><input type="text" id="addEqName" class="form-input"></div>
        <div class="form-group"><label class="form-label">设备ID</label><input type="text" id="addEqId" class="form-input" placeholder="EQ-006"></div>
        <div class="form-group"><label class="form-label">设备类型</label>
            <select id="addEqType" class="form-select">
                <option value="motor">电机</option><option value="pump">水泵</option>
                <option value="bearing">轴承</option><option value="compressor">压缩机</option>
                <option value="gearbox">齿轮箱</option>
            </select>
        </div>
        <div class="form-group"><label class="form-label">位置</label><input type="text" id="addEqLoc" class="form-input"></div>
        <div class="form-group"><label class="form-label">制造商</label><input type="text" id="addEqMfr" class="form-input"></div>
        <div style="text-align:right"><button class="btn btn-primary" onclick="submitAddEquipment()">添加</button></div>
    `);
}

async function submitAddEquipment() {
    const data = {
        equipment_id: document.getElementById('addEqId').value || `EQ-${Date.now()}`,
        name: document.getElementById('addEqName').value,
        type: document.getElementById('addEqType').value,
        location: document.getElementById('addEqLoc').value,
        manufacturer: document.getElementById('addEqMfr').value,
    };
    const res = await API.post('/api/equipment', data);
    closeModal();
    if (res.success) { showToast('设备已添加', 'success'); loadEquipment(); }
    else showToast('添加失败', 'error');
}

// === 系统设置 ===
async function loadSettings() {
    const status = await API.get('/api/system/status');
    document.getElementById('settingsContent').innerHTML = `
        <div class="card">
            <div class="card-header"><h3>系统配置</h3></div>
            <div class="card-body">
                <div class="form-group">
                    <label class="form-label">传感器采样间隔（秒）</label>
                    <input type="number" id="cfgInterval" class="form-input" value="${status.status.sensor_interval}" min="1" max="60">
                </div>
                <div class="form-group">
                    <label class="form-label">退化速度倍率</label>
                    <input type="number" id="cfgDegrade" class="form-input" value="1.0" min="0.1" max="10" step="0.1">
                </div>
                <button class="btn btn-primary" onclick="saveSettings()">保存配置</button>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><h3>系统信息</h3></div>
            <div class="card-body">
                <table class="data-table">
                    <tr><td>系统版本</td><td>v${status.status.version}</td></tr>
                    <tr><td>设备数量</td><td>${status.status.total_equipment}</td></tr>
                    <tr><td>数据采集线程</td><td>${status.status.data_thread_running ? '运行中' : '已停止'}</td></tr>
                    <tr><td>采样间隔</td><td>${status.status.sensor_interval} 秒</td></tr>
                </table>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><h3>故障注入与演示</h3></div>
            <div class="card-body">
                <p style="color:var(--text-secondary);font-size:13px;margin-bottom:12px">
                    通过注入故障或加速退化来演示系统的预测性维护能力。
                </p>
                <button class="btn btn-warning" onclick="injectFaultDialog()">注入故障</button>
            </div>
        </div>
    `;
}

async function saveSettings() {
    const interval = parseInt(document.getElementById('cfgInterval').value);
    const degrade = parseFloat(document.getElementById('cfgDegrade').value);
    await API.post('/api/system/config', { sensor_interval: interval, degradation_speed: degrade });
    showToast('配置已保存', 'success');
}

// === 自动刷新 ===
function autoRefreshToggle() {
    autoRefresh = !autoRefresh;
    document.getElementById('autoRefreshBtn').textContent = '自动刷新: ' + (autoRefresh ? '开' : '关');
    if (!autoRefresh && refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

// === 知识图谱搜索 ===
function searchKG(e) {
    if (e.key === 'Enter') {
        const keyword = document.getElementById('kgSearchInput').value;
        searchKnowledgeGraph(keyword);
    }
}

// === 初始化 ===
loadOverview();

// 定时刷新总览
setInterval(() => {
    if (autoRefresh && document.getElementById('page-overview').classList.contains('active')) {
        loadOverview();
    }
}, 10000);
