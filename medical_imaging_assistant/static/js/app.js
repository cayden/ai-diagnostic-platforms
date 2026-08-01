/* ==================== 全局状态 ==================== */
const App = {
    currentView: 'analysis',
    currentAnalysis: null,
    detections: [],
    showBoxes: true,
    showLabels: true,
    boxOpacity: 0.4,
    imageElement: null,
    historyPage: 1,
    chatContext: '',
};

const COLORS = {
    '结节': '#3b82f6',
    '肿块': '#ef4444',
    '钙化': '#f59e0b',
    '囊性病变': '#8b5cf6',
    '实性病变': '#ec4899',
    '磨玻璃影': '#06b6d4',
    '纤维条索': '#10b981',
    '胸腔积液': '#f97316',
};

const RISK_COLORS = {
    '低风险': 'low',
    '中风险': 'mid',
    '高风险': 'high',
};

const BM_COLORS = {
    '良性': 'benign',
    '良性可能性大': 'benign',
    '不确定': 'uncertain',
    '恶性可能性大': 'malignant',
};

/* ==================== 导航 ==================== */
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const view = item.dataset.view;
        switchView(view);
    });
});

function switchView(view) {
    App.currentView = view;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelector(`.nav-item[data-view="${view}"]`).classList.add('active');
    document.getElementById(`view-${view}`).classList.add('active');

    if (view === 'history') loadHistory();
    if (view === 'dashboard') loadDashboard();
    if (view === 'chat') loadChatHistory();
    if (view === 'knowledge') initKnowledgeGraph();
}

/* ==================== 影像上传 ==================== */
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        handleFileUpload();
    }
});
fileInput.addEventListener('change', handleFileUpload);

async function handleFileUpload() {
    const file = fileInput.files[0];
    if (!file) return;

    // 显示上传中
    document.getElementById('uploadPrompt').style.display = 'none';
    document.getElementById('uploadLoading').style.display = 'block';
    document.getElementById('imageViewer').style.display = 'none';

    // 动画步骤
    const steps = document.querySelectorAll('.loading-steps .step');
    steps[0].classList.add('active');
    setTimeout(() => { steps[0].classList.remove('active'); steps[0].classList.add('done'); steps[1].classList.add('active'); }, 800);
    setTimeout(() => { steps[1].classList.remove('active'); steps[1].classList.add('done'); steps[2].classList.add('active'); }, 1600);

    const formData = new FormData();
    formData.append('image', file);
    formData.append('patient_name', document.getElementById('patientName').value || '未知患者');
    formData.append('patient_age', document.getElementById('patientAge').value);
    formData.append('patient_gender', document.getElementById('patientGender').value);
    formData.append('exam_type', document.getElementById('examType').value);
    formData.append('clinical_info', document.getElementById('clinicalInfo').value);

    try {
        const resp = await fetch('/api/analyze', { method: 'POST', body: formData });
        const data = await resp.json();

        if (data.success) {
            steps[2].classList.remove('active'); steps[2].classList.add('done');
            setTimeout(() => {
                document.getElementById('uploadLoading').style.display = 'none';
                document.getElementById('uploadPrompt').style.display = 'block';
                showAnalysisResult(data);
                toast('分析完成', 'success');
            }, 500);
        } else {
            throw new Error(data.error || '分析失败');
        }
    } catch (err) {
        document.getElementById('uploadLoading').style.display = 'none';
        document.getElementById('uploadPrompt').style.display = 'block';
        resetSteps();
        toast('分析失败: ' + err.message, 'error');
    }
}

function resetSteps() {
    document.querySelectorAll('.loading-steps .step').forEach(s => {
        s.classList.remove('active', 'done');
    });
}

/* ==================== 影像显示与检测框绘制 ==================== */
function showAnalysisResult(data) {
    App.currentAnalysis = data;
    App.detections = data.detection.detections;

    document.getElementById('imageViewer').style.display = 'block';
    document.getElementById('resultPanel').style.display = 'block';

    // 加载图像
    const img = new Image();
    img.onload = () => {
        App.imageElement = img;
        drawCanvas();
        document.getElementById('imageInfo').textContent =
            `${img.width}×${img.height}px | ${App.detections.length}个检测区域`;
    };
    img.src = data.image_base64;

    // 显示分析结果
    renderAnalysisResult(data);
    // 设置聊天上下文
    App.chatContext = JSON.stringify({
        detection: data.detection,
        analysis: data.analysis,
    });
}

function drawCanvas() {
    if (!App.imageElement) return;
    const canvas = document.getElementById('imageCanvas');
    const ctx = canvas.getContext('2d');
    const img = App.imageElement;

    // 适配显示尺寸
    const maxW = canvas.parentElement.clientWidth - 20;
    const maxH = 580;
    let scale = Math.min(maxW / img.width, maxH / img.height, 1);
    canvas.width = img.width * scale;
    canvas.height = img.height * scale;

    // 绘制图像
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    // 绘制检测框
    if (App.showBoxes) {
        App.detections.forEach((det, idx) => {
            const [x1, y1, x2, y2] = det.bbox.map((v, i) => v * (i % 2 === 0 ? scale : scale));
            const color = COLORS[det.class_name] || '#3b82f6';
            const conf = det.confidence;

            // 半透明填充
            ctx.fillStyle = hexToRgba(color, App.boxOpacity);
            ctx.fillRect(x1, y1, x2 - x1, y2 - y1);

            // 边框
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

            // 标签
            if (App.showLabels) {
                const label = `${det.class_name} ${conf.toFixed(2)}`;
                ctx.font = 'bold 12px Inter, sans-serif';
                const textW = ctx.measureText(label).width;
                ctx.fillStyle = color;
                ctx.fillRect(x1, y1 - 18, textW + 10, 18);
                ctx.fillStyle = '#fff';
                ctx.fillText(label, x1 + 5, y1 - 5);

                // 编号
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(x1 + 8, y1 + 8, 10, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.font = 'bold 10px Inter, sans-serif';
                ctx.fillText(idx + 1, x1 + 5, y1 + 12);
            }
        });
    }
}

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

// 工具栏切换
document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        btn.classList.toggle('active');
        const tool = btn.dataset.tool;
        if (tool === 'box') App.showBoxes = btn.classList.contains('active');
        if (tool === 'label') App.showLabels = btn.classList.contains('active');
        if (tool === 'opacity') {
            const slider = document.getElementById('opacitySlider');
            slider.value = slider.value > 50 ? 20 : 80;
            App.boxOpacity = slider.value / 100;
        }
        drawCanvas();
    });
});

document.getElementById('opacitySlider').addEventListener('input', (e) => {
    App.boxOpacity = e.target.value / 100;
    drawCanvas();
});

/* ==================== 分析结果渲染 ==================== */
function renderAnalysisResult(data) {
    const analysis = data.analysis;
    const detection = data.detection;
    const timing = data.timing;

    document.getElementById('timingBadge').textContent =
        `检测 ${timing.detection}s · 分析 ${timing.analysis}s · 共 ${timing.total}s`;

    let html = '';

    // 总体印象
    if (analysis.overall_impression) {
        html += `<div class="analysis-section">
            <h4>总体印象</h4>
            <div class="impression-text">${analysis.overall_impression}</div>
        </div>`;
    }

    // 风险评估
    if (analysis.risk_level) {
        const riskClass = RISK_COLORS[analysis.risk_level] || 'low';
        const riskColor = riskClass === 'high' ? '#dc2626' : (riskClass === 'mid' ? '#f59e0b' : '#16a34a');
        html += `<div class="risk-card ${riskClass}">
            <div class="risk-label">风险评估</div>
            <div class="risk-value">${analysis.risk_level}（${analysis.risk_score}/100）</div>
            <div class="risk-score-bar"><div class="risk-score-fill" style="width:${analysis.risk_score}%;background:${riskColor}"></div></div>
        </div>`;
    }

    // 检测区域详情
    if (analysis.findings && analysis.findings.length > 0) {
        html += `<div class="analysis-section"><h4>检测区域详情 (${analysis.findings.length})</h4>`;
        analysis.findings.forEach((f, idx) => {
            const bmClass = BM_COLORS[f.benign_malignant] || 'uncertain';
            const det = detection.detections[idx] || {};
            const color = COLORS[det.class_name] || '#3b82f6';
            html += `<div class="detection-item ${bmClass}">
                <div class="detection-header">
                    <span class="detection-name">
                        <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:6px;"></span>
                        ${f.region || det.class_name}
                    </span>
                    <span class="confidence-badge">置信度 ${(det.confidence * 100).toFixed(1)}%</span>
                </div>
                <div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px;">${f.description}</div>
                <div class="detection-attrs">`;
            if (f.size_mm) html += `<span class="attr-tag">大小: ${f.size_mm}mm</span>`;
            if (f.shape) html += `<span class="attr-tag">形态: ${f.shape}</span>`;
            if (f.edge) html += `<span class="attr-tag">边缘: ${f.edge}</span>`;
            if (f.density) html += `<span class="attr-tag">密度: ${f.density}</span>`;
            html += `<span class="bm-badge ${bmClass}">${f.benign_malignant}</span>`;
            html += `</div>
                <div style="font-size:12px;color:var(--text-secondary);margin-top:6px;">建议: ${f.recommendation}</div>
            </div>`;
        });
        html += '</div>';
    }

    // 风险因素
    if (analysis.risk_factors && analysis.risk_factors.length > 0) {
        html += `<div class="analysis-section">
            <h4>风险因素</h4>
            <div class="tag-list">${analysis.risk_factors.map(r => `<span class="tag">${r}</span>`).join('')}</div>
        </div>`;
    }

    // 鉴别诊断
    if (analysis.differential_diagnosis && analysis.differential_diagnosis.length > 0) {
        html += `<div class="analysis-section">
            <h4>鉴别诊断</h4>
            <div class="tag-list">${analysis.differential_diagnosis.map(d => `<span class="tag" style="background:#fef3c7;color:#92400e;border-color:#fde68a;">${d}</span>`).join('')}</div>
        </div>`;
    }

    // 建议
    if (analysis.recommendations && analysis.recommendations.length > 0) {
        html += `<div class="analysis-section">
            <h4>处理建议</h4>
            <ul class="recommendation-list">${analysis.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>
        </div>`;
    }

    // 随访建议
    if (analysis.follow_up) {
        html += `<div class="analysis-section">
            <h4>随访建议</h4>
            <div class="impression-text">${analysis.follow_up}</div>
        </div>`;
    }

    // 免责声明
    if (analysis.disclaimer) {
        html += `<div style="font-size:11px;color:var(--text-muted);margin-top:12px;padding:8px 12px;background:#fef3c7;border-radius:6px;">
            ⚠️ ${analysis.disclaimer}
        </div>`;
    }

    // 操作按钮
    html += `<div style="display:flex;gap:8px;margin-top:16px;">
        <button class="btn btn-primary" onclick="exportReport()">导出报告</button>
        <button class="btn btn-ghost" onclick="askAIAboutResult()">AI解读结果</button>
    </div>`;

    document.getElementById('resultBody').innerHTML = html;
}

function exportReport() {
    if (!App.currentAnalysis) return;
    const report = App.currentAnalysis.report;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `report_${report.report_id}.json`;
    a.click();
    toast('报告已导出', 'success');
}

function askAIAboutResult() {
    if (!App.currentAnalysis) return;
    switchView('chat');
    const det = App.currentAnalysis.detection;
    const analysis = App.currentAnalysis.analysis;
    const msg = `请解读以下影像分析结果：检出${det.detections.length}个区域，风险等级为${analysis.risk_level}。${analysis.overall_impression}`;
    document.getElementById('chatInput').value = msg;
    sendMessage();
}

/* ==================== 历史记录 ==================== */
async function loadHistory(page = 1) {
    App.historyPage = page;
    const search = document.getElementById('historySearch').value;
    const resp = await fetch(`/api/history?page=${page}&per_page=15&search=${encodeURIComponent(search)}`);
    const data = await resp.json();

    if (data.success) {
        renderHistoryList(data.records, data.total, page);
    }
}

document.getElementById('historySearch').addEventListener('input', () => {
    clearTimeout(window.searchTimer);
    window.searchTimer = setTimeout(() => loadHistory(1), 300);
});

function renderHistoryList(records, total, page) {
    const list = document.getElementById('historyList');
    if (records.length === 0) {
        list.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text-muted);">暂无历史记录</div>';
        document.getElementById('historyPagination').innerHTML = '';
        return;
    }

    list.innerHTML = records.map(r => {
        const riskClass = RISK_COLORS[r.risk_level] || 'low';
        const date = new Date(r.created_at).toLocaleString('zh-CN');
        return `<div class="history-card" onclick="showRecordDetail('${r.record_id}')">
            <div class="history-thumb">
                <img src="/api/uploads/${r.image_filename}" alt="">
            </div>
            <div class="history-info">
                <div class="history-name">${r.patient_name} · ${r.exam_type}</div>
                <div class="history-meta">
                    <span>${date}</span>
                    <span>${r.findings_count}个区域</span>
                    <span>ID: ${r.record_id}</span>
                </div>
            </div>
            <div class="history-actions">
                <span class="risk-pill ${riskClass}">${r.risk_level}</span>
                <button class="btn btn-ghost" onclick="event.stopPropagation();deleteRecord('${r.record_id}')">删除</button>
            </div>
        </div>`;
    }).join('');

    // 分页
    const totalPages = Math.ceil(total / 15);
    if (totalPages > 1) {
        let pages = '';
        for (let i = 1; i <= totalPages; i++) {
            pages += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="loadHistory(${i})">${i}</button>`;
        }
        document.getElementById('historyPagination').innerHTML = pages;
    } else {
        document.getElementById('historyPagination').innerHTML = '';
    }
}

async function showRecordDetail(recordId) {
    const resp = await fetch(`/api/history/${recordId}`);
    const data = await resp.json();
    if (data.success) {
        const r = data.record;
        const body = document.getElementById('recordModalBody');
        let html = `<div class="analysis-section">
            <h4>患者信息</h4>
            <div class="impression-text">
                姓名: ${r.patient_name} | 年龄: ${r.patient_age || '未填写'} | 性别: ${r.patient_gender || '未填写'}<br>
                检查类型: ${r.exam_type} | 记录ID: ${r.record_id}<br>
                时间: ${new Date(r.created_at).toLocaleString('zh-CN')}
            </div>
        </div>`;

        const img = new Image();
        img.src = `/api/uploads/${r.image_filename}`;
        img.onload = () => {
            // 重新渲染
        };

        if (r.analysis_result && r.analysis_result.overall_impression) {
            html += `<div class="analysis-section">
                <h4>总体印象</h4>
                <div class="impression-text">${r.analysis_result.overall_impression}</div>
            </div>`;
        }

        if (r.analysis_result && r.analysis_result.risk_level) {
            const riskClass = RISK_COLORS[r.analysis_result.risk_level] || 'low';
            html += `<div class="risk-card ${riskClass}">
                <div class="risk-label">风险评估</div>
                <div class="risk-value">${r.analysis_result.risk_level}（${r.analysis_result.risk_score}/100）</div>
            </div>`;
        }

        if (r.analysis_result && r.analysis_result.findings) {
            html += `<div class="analysis-section"><h4>检测区域 (${r.analysis_result.findings.length})</h4>`;
            r.analysis_result.findings.forEach(f => {
                const bmClass = BM_COLORS[f.benign_malignant] || 'uncertain';
                html += `<div class="detection-item ${bmClass}">
                    <div class="detection-header">
                        <span class="detection-name">${f.region}</span>
                        <span class="bm-badge ${bmClass}">${f.benign_malignant}</span>
                    </div>
                    <div style="font-size:12px;color:var(--text-secondary);">${f.description}</div>
                </div>`;
            });
            html += '</div>';
        }

        if (r.analysis_result && r.analysis_result.recommendations) {
            html += `<div class="analysis-section"><h4>处理建议</h4>
                <ul class="recommendation-list">${r.analysis_result.recommendations.map(r2 => `<li>${r2}</li>`).join('')}</ul>
            </div>`;
        }

        if (r.analysis_result && r.analysis_result.follow_up) {
            html += `<div class="analysis-section"><h4>随访建议</h4>
                <div class="impression-text">${r.analysis_result.follow_up}</div>
            </div>`;
        }

        html += `<div style="font-size:11px;color:var(--text-muted);margin-top:12px;padding:8px 12px;background:#fef3c7;border-radius:6px;">
            ⚠️ ${r.analysis_result?.disclaimer || '本报告仅供参考，不能替代专业医师诊断'}
        </div>`;

        body.innerHTML = html;
        document.getElementById('recordModal').style.display = 'flex';
    }
}

async function deleteRecord(recordId) {
    if (!confirm('确认删除此记录？此操作不可撤销。')) return;
    const resp = await fetch(`/api/history/${recordId}`, { method: 'DELETE' });
    const data = await resp.json();
    if (data.success) {
        toast('记录已删除', 'success');
        loadHistory(App.historyPage);
    } else {
        toast('删除失败', 'error');
    }
}

/* ==================== AI 问答 ==================== */
const chatInput = document.getElementById('chatInput');
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        chatInput.value = chip.dataset.q;
        sendMessage();
    });
});

async function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg) return;

    // 显示用户消息
    appendChatMsg('user', msg);
    chatInput.value = '';

    // 显示typing
    const typingId = 'typing-' + Date.now();
    const messages = document.getElementById('chatMessages');
    const typingHtml = `<div class="chat-msg assistant" id="${typingId}">
        <div class="chat-avatar">AI</div>
        <div class="chat-bubble"><div class="typing-indicator"><span></span><span></span><span></span></div></div>
    </div>`;
    messages.insertAdjacentHTML('beforeend', typingHtml);
    messages.scrollTop = messages.scrollHeight;

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, context: App.chatContext }),
        });
        const data = await resp.json();

        document.getElementById(typingId).remove();
        if (data.success) {
            const content = typeof data.response === 'object' ? data.response.content : data.response;
            appendChatMsg('assistant', content);
        } else {
            appendChatMsg('assistant', '抱歉，处理您的问题时出错。');
        }
    } catch (err) {
        document.getElementById(typingId).remove();
        appendChatMsg('assistant', '网络错误，请稍后重试。');
    }
}

function appendChatMsg(role, content) {
    const messages = document.getElementById('chatMessages');
    const avatar = role === 'user' ? '你' : 'AI';
    const html = `<div class="chat-msg ${role}">
        <div class="chat-avatar">${avatar}</div>
        <div class="chat-bubble">${escapeHtml(content)}</div>
    </div>`;
    messages.insertAdjacentHTML('beforeend', html);
    messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadChatHistory() {
    const resp = await fetch('/api/chat/history');
    const data = await resp.json();
    if (data.success && data.records.length > 0) {
        const messages = document.getElementById('chatMessages');
        messages.innerHTML = '';
        data.records.forEach(r => {
            appendChatMsg('user', r.user_message);
            appendChatMsg('assistant', r.assistant_response);
        });
    } else {
        const messages = document.getElementById('chatMessages');
        messages.innerHTML = `<div class="chat-msg assistant">
            <div class="chat-avatar">AI</div>
            <div class="chat-bubble">您好！我是医学影像AI助手，可以回答关于肺结节、良恶性判定、CT检查、随访计划等影像诊断相关问题。请问有什么可以帮您的？</div>
        </div>`;
    }
}

async function clearChat() {
    await fetch('/api/chat/clear', { method: 'DELETE' });
    document.getElementById('chatMessages').innerHTML = '';
    loadChatHistory();
    toast('问答历史已清空', 'info');
}

/* ==================== 统计看板 ==================== */
async function loadDashboard() {
    const resp = await fetch('/api/history/stats');
    const data = await resp.json();
    if (data.success) {
        const stats = data.stats;
        const grid = document.getElementById('dashboardGrid');

        let html = '';

        // 总量卡片
        html += `<div class="stat-card">
            <div class="stat-card-title">总分析次数</div>
            <div class="stat-big-number">${stats.total_records}</div>
        </div>`;

        // 风险分布
        html += `<div class="stat-card">
            <div class="stat-card-title">风险等级分布</div>`;
        const total = stats.risk_distribution['低风险'] + stats.risk_distribution['中风险'] + stats.risk_distribution['高风险'];
        const riskData = [
            { label: '低风险', count: stats.risk_distribution['低风险'], color: '#16a34a' },
            { label: '中风险', count: stats.risk_distribution['中风险'], color: '#f59e0b' },
            { label: '高风险', count: stats.risk_distribution['高风险'], color: '#dc2626' },
        ];
        riskData.forEach(r => {
            const pct = total > 0 ? (r.count / total * 100).toFixed(0) : 0;
            html += `<div class="bar-chart-item">
                <div class="bar-chart-label"><span>${r.label}</span><span>${r.count} (${pct}%)</span></div>
                <div class="bar-chart-bar"><div class="bar-chart-fill" style="width:${pct}%;background:${r.color}"></div></div>
            </div>`;
        });
        html += '</div>';

        // 良恶性分布
        html += `<div class="stat-card">
            <div class="stat-card-title">良恶性判定分布</div>`;
        const bmData = [
            { label: '良性', count: stats.benign_distribution['良性'], color: '#16a34a' },
            { label: '良性可能性大', count: stats.benign_distribution['良性可能性大'], color: '#84cc16' },
            { label: '不确定', count: stats.benign_distribution['不确定'], color: '#f59e0b' },
            { label: '恶性可能性大', count: stats.benign_distribution['恶性可能性大'], color: '#dc2626' },
        ];
        const bmTotal = bmData.reduce((s, d) => s + d.count, 0);
        bmData.forEach(r => {
            const pct = bmTotal > 0 ? (r.count / bmTotal * 100).toFixed(0) : 0;
            html += `<div class="bar-chart-item">
                <div class="bar-chart-label"><span>${r.label}</span><span>${r.count} (${pct}%)</span></div>
                <div class="bar-chart-bar"><div class="bar-chart-fill" style="width:${pct}%;background:${r.color}"></div></div>
            </div>`;
        });
        html += '</div>';

        // 检测类别分布
        html += `<div class="stat-card">
            <div class="stat-card-title">检测类别分布</div>`;
        const classEntries = Object.entries(stats.class_distribution).sort((a, b) => b[1] - a[1]);
        const maxCount = Math.max(...classEntries.map(e => e[1]), 1);
        classEntries.forEach(([cls, count]) => {
            const pct = (count / maxCount * 100).toFixed(0);
            const color = COLORS[cls] || '#3b82f6';
            html += `<div class="bar-chart-item">
                <div class="bar-chart-label"><span>${cls}</span><span>${count}</span></div>
                <div class="bar-chart-bar"><div class="bar-chart-fill" style="width:${pct}%;background:${color}"></div></div>
            </div>`;
        });
        html += '</div>';

        // AI问答数
        html += `<div class="stat-card">
            <div class="stat-card-title">AI 问答总数</div>
            <div class="stat-big-number" style="color:var(--primary)">${stats.total_chats}</div>
        </div>`;

        grid.innerHTML = html;
    }
}

/* ==================== 设置 ==================== */
async function loadSystemStatus() {
    const resp = await fetch('/api/system/status');
    const data = await resp.json();
    if (data.success) {
        const status = data.status;
        const yoloText = status.yolo_mode === 'simulation' ? '模拟模式' : '模型模式';
        const llmText = status.llm_configured ? 'API已配置' : (status.llm_mode === 'simulation' ? '模拟模式' : 'API模式');
        document.querySelector('.sidebar-footer .status-row:nth-child(1) span:last-child').textContent = `YOLO: ${yoloText}`;
        document.querySelector('.sidebar-footer .status-row:nth-child(2) span:last-child').textContent = `LLM: ${llmText}`;

        // 设置弹窗默认值
        document.getElementById('yoloModeSelect').value = String(status.yolo_mode === 'simulation');
        document.getElementById('llmModeSelect').value = String(status.llm_mode === 'simulation');
    }
}

async function saveSettings() {
    const apiKey = document.getElementById('apiKeyInput').value;
    const yoloSim = document.getElementById('yoloModeSelect').value === 'true';
    const llmSim = document.getElementById('llmModeSelect').value === 'true';

    const resp = await fetch('/api/system/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            deepseek_api_key: apiKey,
            yolo_use_simulation: yoloSim,
            llm_use_simulation: llmSim,
        }),
    });
    const data = await resp.json();
    if (data.success) {
        toast('设置已保存', 'success');
        closeModal('settingsModal');
        loadSystemStatus();
    }
}

/* ==================== 弹窗 ==================== */
function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

// 点击遮罩关闭
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.style.display = 'none';
    });
});

/* ==================== Toast ==================== */
function toast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    container.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0';
        t.style.transform = 'translateX(400px)';
        setTimeout(() => t.remove(), 300);
    }, 3000);
}

/* ==================== 初始化 ==================== */
loadSystemStatus();
