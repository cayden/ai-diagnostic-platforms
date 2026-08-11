const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const {
  FaDatabase, FaLock, FaSearch, FaUsers, FaFolderOpen, FaRobot, FaKey,
  FaClipboardList, FaChartLine, FaUpload, FaCogs, FaCommentDots, FaShieldAlt,
  FaUserShield, FaServer, FaBookOpen, FaCheckCircle, FaArrowRight, FaIndustry,
  FaLightbulb, FaEye, FaHistory, FaFileAlt, FaCpu, FaNetworkWired, FaFileUpload,
  FaClock,   FaExclamationTriangle, FaHandshake, FaBuilding, FaQuoteLeft,
  FaTachometerAlt, FaMoneyBillWave, FaLayerGroup, FaFilePdf, FaFileWord,
  FaFileExcel, FaTags, FaProjectDiagram, FaLockOpen, FaMicrochip
} = require("react-icons/fa");

const W = 13.33, H = 7.5;
const NAVY = "1E2761", NAVY_DARK = "121737", NAVY_SOFT = "EAECF7";
const TEAL = "028090", TEAL_D = "02606C", TEAL_LIGHT = "E4F3F4";
const AMBER = "F2A03D", AMBER_LIGHT = "FDF1DC";
const BG = "F7F8FB", CARD = "FFFFFF", INK = "23283B", MUTED = "5E6480";
const BORDER = "E3E6EE", RED = "C0392B", RED_LIGHT = "FBEAE8";
const HEAD = "Microsoft YaHei", BODY = "Microsoft YaHei";

const makeShadow = () => ({ type: "outer", color: "1A2340", blur: 9, offset: 3, angle: 90, opacity: 0.10 });

function iconSvg(IconComponent, color, size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}
async function iconPng(IconComponent, color) {
  const buf = await sharp(Buffer.from(iconSvg(IconComponent, color))).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

async function buildIcons() {
  const defs = {
    db: [FaDatabase, NAVY], lock: [FaLock, "FFFFFF"], search: [FaSearch, NAVY],
    users: [FaUsers, "FFFFFF"], folder: [FaFolderOpen, NAVY], robot: [FaRobot, "FFFFFF"],
    key: [FaKey, NAVY], clip: [FaClipboardList, "FFFFFF"], chart: [FaChartLine, NAVY],
    upload: [FaUpload, NAVY], cogs: [FaCogs, NAVY], chat: [FaCommentDots, "FFFFFF"],
    shield: [FaShieldAlt, NAVY], usershield: [FaUserShield, "FFFFFF"], server: [FaServer, NAVY],
    book: [FaBookOpen, "FFFFFF"], check: [FaCheckCircle, TEAL], arrow: [FaArrowRight, TEAL],
    industry: [FaIndustry, NAVY], bulb: [FaLightbulb, "FFFFFF"], eye: [FaEye, NAVY],
    history: [FaHistory, NAVY], file: [FaFileAlt, NAVY], cpu: [FaCpu, NAVY],
    network: [FaNetworkWired, "FFFFFF"], fileup: [FaFileUpload, NAVY], clock: [FaClock, NAVY],
    warn: [FaExclamationTriangle, "FFFFFF"], handshake: [FaHandshake, NAVY],
    building: [FaBuilding, "FFFFFF"], quote: [FaQuoteLeft, "FFFFFF"],
    tacho: [FaTachometerAlt, NAVY], money: [FaMoneyBillWave, NAVY], layers: [FaLayerGroup, NAVY],
    pdf: [FaFilePdf, NAVY], word: [FaFileWord, NAVY], excel: [FaFileExcel, NAVY],
    tags: [FaTags, NAVY], project: [FaProjectDiagram, NAVY], lockopen: [FaLockOpen, "FFFFFF"],
    cpu: [FaMicrochip, NAVY]
  };
  const out = {};
  const jobs = Object.entries(defs).map(async ([k, [ic, c]]) => { out[k] = await iconPng(ic, c); });
  await Promise.all(jobs);
  return out;
}

function contentHead(slide, IC, title, sub) {
  slide.background = { color: BG };
  slide.addShape("rect", { x: 0.7, y: 0.5, w: 0.14, h: 0.85, fill: { color: TEAL } });
  slide.addText(title, { x: 1.0, y: 0.38, w: 11.5, h: 0.7, fontFace: HEAD, fontSize: 30, bold: true, color: NAVY, margin: 0 });
  if (sub) slide.addText(sub, { x: 1.0, y: 1.02, w: 11.5, h: 0.4, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0 });
}
function footer(slide, idx, total) {
  slide.addShape("rect", { x: 0.7, y: 7.12, w: 11.93, h: 0.012, fill: { color: BORDER } });
  slide.addText("湖企智库 · 企业AI本地知识库解决方案", { x: 0.7, y: 7.18, w: 6, h: 0.25, fontFace: BODY, fontSize: 9, color: MUTED, margin: 0 });
  slide.addText(String(idx) + " / " + String(total), { x: 11.6, y: 7.18, w: 1.03, h: 0.25, fontFace: BODY, fontSize: 9, color: MUTED, align: "right", margin: 0 });
}
function iconCircle(slide, IC, key, x, y, d, bg) {
  slide.addShape("ellipse", { x, y, w: d, h: d, fill: { color: bg } });
  slide.addImage({ data: IC[key], x: x + d * 0.22, y: y + d * 0.22, w: d * 0.56, h: d * 0.56 });
}
function card(slide, IC, x, y, w, h, iconKey, iconBg, title, bodyLines) {
  slide.addShape("rect", { x, y, w, h, fill: { color: CARD }, line: { color: BORDER, width: 1 }, rectRadius: 0.06, shadow: makeShadow() });
  iconCircle(slide, IC, iconKey, x + 0.32, y + 0.32, 0.62, iconBg);
  slide.addText(title, { x: x + 1.12, y: y + 0.34, w: w - 1.3, h: 0.42, fontFace: HEAD, fontSize: 16, bold: true, color: INK, margin: 0 });
  const runs = bodyLines.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < bodyLines.length - 1 } }));
  slide.addText(runs, { x: x + 0.34, y: y + 0.95, w: w - 0.68, h: h - 1.15, fontFace: BODY, fontSize: 12, color: MUTED, paraSpaceAfter: 5, lineSpacing: 1.12 });
}
const runList = (items) => items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } }));

(async () => {
  const IC = await buildIcons();
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "WorkBuddy";
  pres.title = "湖企智库 - 企业AI本地知识库解决方案";

  const TOTAL = 11;

  /* ============ S1 封面 ============ */
  let s = pres.addSlide();
  s.background = { color: NAVY_DARK };
  s.addShape("rect", { x: 0, y: 0, w: W, h: 0.14, fill: { color: TEAL } });
  s.addShape("rect", { x: 0.9, y: 1.15, w: 4.6, h: 0.02, fill: { color: TEAL } });
  s.addText("HUZHOU ENTERPRISE AI KNOWLEDGE BASE", { x: 0.9, y: 0.85, w: 9, h: 0.3, fontFace: BODY, fontSize: 12, color: "9FB4D8", charSpacing: 3, margin: 0 });
  s.addText("湖企智库", { x: 0.9, y: 1.85, w: 8.5, h: 1.35, fontFace: HEAD, fontSize: 66, bold: true, color: "FFFFFF", margin: 0 });
  s.addText("企业 AI 本地知识库 · 智能问答解决方案", { x: 0.9, y: 3.25, w: 9.5, h: 0.6, fontFace: HEAD, fontSize: 26, color: "D8E1F5", margin: 0 });
  s.addText("面向湖州制造业 · 敏感数据全本地化处理", { x: 0.9, y: 3.95, w: 9.5, h: 0.4, fontFace: BODY, fontSize: 14, color: "9FB4D8", margin: 0 });
  const pills = ["DeepSeek 本地部署", "数据不出域", "开箱即用演示"];
  let px = 0.9;
  pills.forEach((p) => {
    const w = 0.32 * p.length + 0.7;
    s.addShape("roundRect", { x: px, y: 4.7, w, h: 0.5, fill: { color: "1D2A5C" }, line: { color: TEAL, width: 1 }, rectRadius: 0.25 });
    s.addText(p, { x: px, y: 4.7, w, h: 0.5, fontFace: BODY, fontSize: 12.5, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
    px += w + 0.3;
  });
  iconCircle(s, IC, "shield", 11.35, 2.5, 1.35, "1D2A5C");
  s.addImage({ data: IC["network"], x: 11.68, y: 2.83, w: 0.68, h: 0.68 });
  s.addText("本地部署", { x: 10.95, y: 4.1, w: 2.15, h: 0.4, fontFace: HEAD, fontSize: 15, bold: true, color: "FFFFFF", align: "center", margin: 0 });
  s.addText("模型 + 知识 + 推理\n全链路内网", { x: 10.95, y: 4.5, w: 2.15, h: 0.75, fontFace: BODY, fontSize: 11, color: "9FB4D8", align: "center", margin: 0 });
  s.addShape("rect", { x: 0.9, y: 6.55, w: 11.5, h: 0.012, fill: { color: "2A3A6E" } });
  s.addText("演示版本 v1.0 · 适用于方案汇报与企业展厅演示", { x: 0.9, y: 6.72, w: 9, h: 0.3, fontFace: BODY, fontSize: 10, color: "7C8FBD", margin: 0 });

  /* ============ S2 痛点 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "企业知识管理的四大痛点", "湖州制造企业在数字化转型中最普遍面临的现实问题");
  s.addText("制度、工艺、客户与财务知识散落各处，且多涉及敏感数据 —— 上云不敢，查找困难。", { x: 1.0, y: 1.5, w: 11.4, h: 0.4, fontFace: BODY, fontSize: 14, bold: true, color: TEAL_D, margin: 0 });
  card(s, IC, 0.9, 2.1, 5.55, 2.3, "folder", NAVY_SOFT, "知识分散 · 检索靠人",
    ["制度文档、工艺文件、客户资料散落在文件服务器、OA 与个人电脑", "想找一份文件平均要翻 3~5 个系统，新员工上手慢"]);
  card(s, IC, 6.88, 2.1, 5.55, 2.3, "lock", NAVY_SOFT, "敏感数据 · 不敢上云",
    ["客户信息、财务数据、工艺配方触碰合规红线", "数据出域风险高，公有云大模型 API 无法直接使用"]);
  card(s, IC, 0.9, 4.62, 5.55, 2.3, "warn", RED_LIGHT, "经验流失 · 难以沉淀",
    ["老师傅的工艺诀窍、异常处理经验没有结构化沉淀", "人员流动导致隐性知识大量流失"]);
  card(s, IC, 6.88, 4.62, 5.55, 2.3, "search", NAVY_SOFT, "检索低效 · 不懂语义",
    ["传统关键词搜索理解不了语义", "问「发票报销规定」搜不到「出差费用怎么报销」"]);
  footer(s, 2, TOTAL);

  /* ============ S3 方案总览 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "方案总览：本地 DeepSeek + RAG 知识增强", "让企业知识「存得安全 · 问得聪明 · 答得有据」");
  s.addShape("rect", { x: 0.9, y: 1.55, w: 11.53, h: 1.0, fill: { color: NAVY }, rectRadius: 0.08 });
  s.addImage({ data: IC["quote"], x: 1.2, y: 1.8, w: 0.5, h: 0.5 });
  s.addText("本地化部署 DeepSeek 大模型 + 向量检索增强生成（RAG），企业私有知识不出内网即可获得智能问答能力。", { x: 1.9, y: 1.55, w: 10.3, h: 1.0, fontFace: BODY, fontSize: 16, bold: true, color: "FFFFFF", valign: "middle", margin: 0 });
  const vals = [
    ["shield", "数据 100% 本地化", "模型、知识、推理全链路在内网，敏感数据零出域"],
    ["bulb", "语义级智能检索", "向量检索理解问题意图，跨文档精准定位答案"],
    ["money", "长期成本更优", "一次 GPU 投入，7×24 在线，不受 API 限流与涨价影响"]
  ];
  let vx = 0.9;
  vals.forEach(([ik, t, d]) => {
    s.addShape("rect", { x: vx, y: 2.85, w: 3.71, h: 2.15, fill: { color: CARD }, line: { color: BORDER, width: 1 }, rectRadius: 0.07, shadow: makeShadow() });
    iconCircle(s, IC, ik, vx + 0.35, 3.15, 0.62, TEAL_LIGHT);
    s.addText(t, { x: vx + 1.15, y: 3.18, w: 2.4, h: 0.42, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: vx + 0.35, y: 3.75, w: 3.0, h: 1.1, fontFace: BODY, fontSize: 11.5, color: MUTED, margin: 0 });
    vx += 3.91;
  });
  s.addText("RAG 问答流水线", { x: 0.9, y: 5.25, w: 5, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  const steps = [["fileup", "文档上传"], ["cogs", "解析分块"], ["db", "向量入库"], ["search", "语义检索"], ["robot", "DeepSeek 生成"]];
  let sx = 0.9;
  steps.forEach(([ik, t], i) => {
    s.addShape("rect", { x: sx, y: 5.75, w: 2.05, h: 0.95, fill: { color: i === 4 ? NAVY : CARD }, line: { color: i === 4 ? NAVY : BORDER, width: 1 }, rectRadius: 0.06 });
    s.addImage({ data: IC[ik], x: sx + 0.2, y: 5.95, w: 0.45, h: 0.45 });
    s.addText(t, { x: sx + 0.78, y: 5.75, w: 1.2, h: 0.95, fontFace: BODY, fontSize: 13, bold: true, color: i === 4 ? "FFFFFF" : INK, valign: "middle", margin: 0 });
    if (i < 4) s.addImage({ data: IC["arrow"], x: sx + 2.12, y: 6.08, w: 0.3, h: 0.3 });
    sx += 2.42;
  });
  footer(s, 3, TOTAL);

  /* ============ S4 总体架构 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "总体架构：四层一体，全部落在企业内网", "从接入、应用到模型与数据，全链路私有化");
  s.addShape("rect", { x: 0.7, y: 1.35, w: 9.75, h: 5.4, fill: { color: "FBFCFE" }, line: { color: TEAL, width: 1.2, dashType: "dash" }, rectRadius: 0.1 });
  s.addText("企业内网安全边界", { x: 0.95, y: 1.45, w: 3, h: 0.3, fontFace: BODY, fontSize: 11, bold: true, color: TEAL_D, margin: 0 });
  const layer = (y, label, items, h, titleSize) => {
    s.addText(label, { x: 0.95, y: y + h / 2 - 0.18, w: 1.05, h: 0.36, fontFace: BODY, fontSize: 11, bold: true, color: MUTED, margin: 0 });
    let x = 2.25;
    const iw = 2.45;
    items.forEach(([t, sub, last]) => {
      const c = last ? NAVY : CARD;
      s.addShape("rect", { x, y, w: iw, h, fill: { color: c }, line: { color: last ? NAVY : BORDER, width: 1 }, rectRadius: 0.06 });
      if (last) {
        s.addText(t, { x, y: y + 0.12, w: iw, h: 0.4, fontFace: BODY, fontSize: titleSize, bold: true, color: "FFFFFF", align: "center", margin: 0 });
        if (sub) s.addText(sub, { x, y: y + 0.52, w: iw, h: 0.32, fontFace: BODY, fontSize: 9.5, color: "C7D4F0", align: "center", margin: 0 });
      } else {
        s.addText(t, { x, y: y + 0.12, w: iw, h: 0.4, fontFace: BODY, fontSize: titleSize, bold: true, color: INK, align: "center", margin: 0 });
        if (sub) s.addText(sub, { x, y: y + 0.52, w: iw, h: 0.32, fontFace: BODY, fontSize: 9.5, color: MUTED, align: "center", margin: 0 });
      }
      x += iw + 0.18;
    });
  };
  layer(1.75, "用户接入", [["员工 Web 端", ""], ["企业微信", ""], ["开放 API", ""]], 0.82, 12.5);
  layer(2.95, "应用功能", [["知识库管理", ""], ["智能问答", ""], ["权限控制", ""], ["审计日志", ""]], 0.82, 12.5);
  layer(4.15, "AI 服务层", [["RAG 检索引擎", "语义检索+重排"], ["本地 Embedding", "bge-m3"], ["DeepSeek 本地推理", "Ollama 7B/14B/32B"]], 1.02, 12.5);
  layer(5.6, "数据存储", [["文档存储", "PDF/Word/Excel"], ["向量数据库", "ChromaDB"], ["审计日志库", "SQLite"]], 0.82, 12.5);
  s.addShape("rect", { x: 10.75, y: 3.35, w: 1.95, h: 1.5, fill: { color: RED_LIGHT }, line: { color: RED, width: 1, dashType: "dash" }, rectRadius: 0.08 });
  s.addText("互联网", { x: 10.75, y: 3.5, w: 1.95, h: 0.35, fontFace: HEAD, fontSize: 12, bold: true, color: RED, align: "center", margin: 0 });
  s.addText("公有云 API\n不接入", { x: 10.75, y: 3.85, w: 1.95, h: 0.75, fontFace: BODY, fontSize: 11, color: RED, align: "center", margin: 0 });
  s.addImage({ data: IC["lockopen"], x: 11.55, y: 3.95, w: 0.35, h: 0.35 });
  s.addText("模型 · 知识 · 推理\n全链路本地化，数据不出域", { x: 10.75, y: 5.2, w: 1.95, h: 0.85, fontFace: BODY, fontSize: 10.5, bold: true, color: TEAL_D, align: "center", margin: 0 });
  footer(s, 4, TOTAL);

  /* ============ S5 技术选型 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "技术选型：DeepSeek 本地化部署矩阵", "按企业硬件条件灵活选择模型规格，支持离线安装包交付");
  s.addText("DeepSeek 本地模型规格", { x: 0.9, y: 1.55, w: 6, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  const rows = [
    [{ text: "模型规格", options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, align: "center" } },
     { text: "显存建议", options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, align: "center" } },
     { text: "适用场景", options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, align: "center" } }],
    [{ text: "deepseek-r1:7b", options: { bold: true, color: INK } }, { text: "16GB", options: { align: "center", color: INK } }, { text: "中小型企业 / 演示环境", options: { color: MUTED } }],
    [{ text: "deepseek-r1:14b", options: { bold: true, color: INK } }, { text: "32GB", options: { align: "center", color: INK } }, { text: "中型企业知识问答", options: { color: MUTED } }],
    [{ text: "deepseek-r1:32b", options: { bold: true, color: INK } }, { text: "64GB+", options: { align: "center", color: INK } }, { text: "大型企业 / 高精度场景", options: { color: MUTED } }]
  ];
  s.addTable(rows, { x: 0.9, y: 2.0, w: 6.3, h: 2.6, colW: [2.1, 1.3, 2.9], border: { pt: 0.75, color: BORDER }, fontFace: BODY, fontSize: 12, rowH: 0.55, valign: "middle" });
  s.addText("配套本地组件", { x: 7.6, y: 1.55, w: 5, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  const comps = [
    ["server", "Ollama 推理引擎", "本地运行 DeepSeek，支持 OpenAI 兼容接口"],
    ["db", "向量数据库 ChromaDB", "知识片段向量化存储与相似度检索"],
    ["network", "本地 Embedding bge-m3", "中文语义向量化，支持中英混合检索"],
    ["file", "文档解析引擎", "PDF / Word / Excel / PPT / TXT / MD 自动解析"]
  ];
  let cy = 2.0;
  comps.forEach(([ik, t, d]) => {
    s.addShape("rect", { x: 7.6, y: cy, w: 4.83, h: 0.88, fill: { color: CARD }, line: { color: BORDER, width: 1 }, rectRadius: 0.06 });
    iconCircle(s, IC, ik, 7.8, cy + 0.14, 0.55, TEAL_LIGHT);
    s.addText(t, { x: 8.5, y: cy + 0.1, w: 3.8, h: 0.32, fontFace: HEAD, fontSize: 12.5, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: 8.5, y: cy + 0.42, w: 3.8, h: 0.34, fontFace: BODY, fontSize: 9.5, color: MUTED, margin: 0 });
    cy += 1.0;
  });
  s.addShape("rect", { x: 0.9, y: 5.0, w: 6.3, h: 1.75, fill: { color: TEAL_LIGHT }, rectRadius: 0.08 });
  s.addText("为什么选本地部署 DeepSeek？", { x: 1.2, y: 5.2, w: 5.7, h: 0.35, fontFace: HEAD, fontSize: 13, bold: true, color: TEAL_D, margin: 0 });
  s.addText(runList(["开源模型可私有化，推理不产生外部流量", "敏感数据全程留在内网，满足合规审查", "企业展厅 / 工厂内网环境可离线演示"]), { x: 1.2, y: 5.6, w: 5.7, h: 1.0, fontFace: BODY, fontSize: 11.5, color: TEAL_D, paraSpaceAfter: 4 });
  footer(s, 5, TOTAL);

  /* ============ S6 数据安全 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "数据安全设计：四层防护 + 合规就绪", "为敏感数据场景量身设计的安全体系");
  const secs = [
    ["network", "网络隔离", "系统仅运行于企业内网，不开放公网端口；与互联网物理/逻辑隔离", NAVY_SOFT],
    ["usershield", "权限控制", "角色化权限：管理员 / 部门主管 / 普通员工，敏感知识分级授权", NAVY_SOFT],
    ["history", "全程审计", "文档操作、问答行为、导出行为全量留痕，可追溯可追责", NAVY_SOFT],
    ["check", "合规就绪", "满足《数据安全法》《个人信息保护法》本地化要求，数据不出域", TEAL_LIGHT]
  ];
  let sy = 1.6;
  secs.forEach(([ik, t, d, bg], i) => {
    const x = i % 2 === 0 ? 0.9 : 6.88;
    s.addShape("rect", { x, y: sy, w: 5.55, h: 1.95, fill: { color: CARD }, line: { color: BORDER, width: 1 }, rectRadius: 0.07, shadow: makeShadow() });
    iconCircle(s, IC, ik, x + 0.35, sy + 0.3, 0.68, bg);
    s.addText(t, { x: x + 1.25, y: sy + 0.32, w: 4.0, h: 0.42, fontFace: HEAD, fontSize: 16, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: x + 0.35, y: sy + 0.95, w: 4.85, h: 0.9, fontFace: BODY, fontSize: 12, color: MUTED, lineSpacing: 1.2, margin: 0 });
    if (i % 2 === 1) sy += 2.15;
  });
  s.addShape("rect", { x: 0.9, y: 5.85, w: 11.53, h: 0.95, fill: { color: NAVY }, rectRadius: 0.08 });
  s.addImage({ data: IC["shield"], x: 1.2, y: 6.05, w: 0.55, h: 0.55 });
  s.addText("核心承诺：模型不出域 · 知识不出域 · 推理不出域 —— 企业数据主权完全自持", { x: 1.95, y: 5.85, w: 10.2, h: 0.95, fontFace: HEAD, fontSize: 15, bold: true, color: "FFFFFF", valign: "middle", margin: 0 });
  footer(s, 6, TOTAL);

  /* ============ S7 功能模块 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "系统功能模块：企业开箱即用的完整能力", "覆盖知识入库、智能问答、治理管控全流程");
  const mods = [
    ["folder", "文档知识库", "多格式文档上传、自动解析、分块向量化，目录化管理"],
    ["chat", "智能问答", "DeepSeek 结合检索结果生成回答，支持追问与多轮对话"],
    ["eye", "引用溯源", "每条答案附来源文档与原文片段，点击即可跳转核验"],
    ["key", "权限管理", "部门 / 角色 / 知识分级，敏感知识仅授权可见"],
    ["clip", "审计日志", "全量操作留痕：谁、何时、问了什么、导出了什么"],
    ["chart", "数据看板", "知识规模、问答热度、检索命中率、系统状态一目了然"]
  ];
  let mx = 0.9, my = 1.6;
  mods.forEach(([ik, t, d], i) => {
    s.addShape("rect", { x: mx, y: my, w: 3.71, h: 1.62, fill: { color: CARD }, line: { color: BORDER, width: 1 }, rectRadius: 0.07, shadow: makeShadow() });
    iconCircle(s, IC, ik, mx + 0.3, my + 0.28, 0.6, TEAL_LIGHT);
    s.addText(t, { x: mx + 1.08, y: my + 0.3, w: 2.5, h: 0.38, fontFace: HEAD, fontSize: 14.5, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: mx + 0.3, y: my + 0.82, w: 3.1, h: 0.72, fontFace: BODY, fontSize: 10.5, color: MUTED, lineSpacing: 1.15, margin: 0 });
    mx += 3.91;
    if ((i + 1) % 3 === 0) { mx = 0.9; my += 1.85; }
  });
  footer(s, 7, TOTAL);

  /* ============ S8 演示流程 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "企业现场演示流程：5 分钟讲透价值", "一套标准演示脚本，可直接用于企业展厅与方案汇报");
  const demo = [
    ["fileup", "上传企业文档", "制度 / 工艺 / 报价等示例文档一键入库"],
    ["cogs", "自动解析入库", "分块 → 向量化，看板实时显示知识规模"],
    ["chat", "现场提问", "「出差报销标准？」「客户投诉如何处理？」"],
    ["check", "答案 + 溯源", "秒级返回带引用来源，点击核验原文"],
    ["shield", "安全演示", "展示权限分级与审计日志，强调数据不出域"]
  ];
  let dx = 0.9;
  demo.forEach(([ik, t, d], i) => {
    s.addShape("ellipse", { x: dx + 0.55, y: 1.7, w: 0.9, h: 0.9, fill: { color: i === 4 ? NAVY : TEAL } });
    s.addText(String(i + 1), { x: dx + 0.55, y: 1.7, w: 0.9, h: 0.9, fontFace: HEAD, fontSize: 22, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
    if (i < 4) s.addImage({ data: IC["arrow"], x: dx + 1.62, y: 2.0, w: 0.3, h: 0.3 });
    s.addShape("rect", { x: dx, y: 2.85, w: 2.28, h: 2.05, fill: { color: CARD }, line: { color: BORDER, width: 1 }, rectRadius: 0.07, shadow: makeShadow() });
    iconCircle(s, IC, ik, dx + 0.28, 3.1, 0.55, TEAL_LIGHT);
    s.addText(t, { x: dx + 0.28, y: 3.75, w: 1.75, h: 0.4, fontFace: HEAD, fontSize: 13.5, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: dx + 0.28, y: 4.18, w: 1.78, h: 0.65, fontFace: BODY, fontSize: 9.5, color: MUTED, lineSpacing: 1.12, margin: 0 });
    dx += 2.48;
  });
  s.addShape("rect", { x: 0.9, y: 5.3, w: 11.53, h: 1.45, fill: { color: TEAL_LIGHT }, rectRadius: 0.08 });
  s.addText("演示配套物料", { x: 1.2, y: 5.48, w: 4, h: 0.35, fontFace: HEAD, fontSize: 14, bold: true, color: TEAL_D, margin: 0 });
  s.addText(runList(["预置湖州制造企业示例知识库（制度 / 工艺 / 售后 / 财务）", "模拟模式免 GPU 即可演示完整流程；接入本地 DeepSeek 即切换真实推理", "一键切换演示数据，覆盖展厅大屏与笔记本两种环境"]), { x: 1.2, y: 5.85, w: 10.9, h: 0.85, fontFace: BODY, fontSize: 11.5, color: TEAL_D, paraSpaceAfter: 3 });
  footer(s, 8, TOTAL);

  /* ============ S9 部署方案 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "部署方案：三档配置 + 三步实施", "按企业规模与预算选择，支持离线交付");
  s.addText("硬件配置建议", { x: 0.9, y: 1.55, w: 6, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  const hw = [
    [{ text: "方案", options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, align: "center" } },
     { text: "内存 / 显存", options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, align: "center" } },
     { text: "适用企业", options: { fill: { color: NAVY }, color: "FFFFFF", bold: true, align: "center" } }],
    [{ text: "轻量版 · 7B", options: { bold: true, color: INK } }, { text: "16GB 内存", options: { align: "center", color: INK } }, { text: "小微企业 / 演示", options: { color: MUTED } }],
    [{ text: "标准版 · 14B", options: { bold: true, color: INK } }, { text: "32GB 内存 / 独显", options: { align: "center", color: INK } }, { text: "中型制造企业", options: { color: MUTED } }],
    [{ text: "企业版 · 32B", options: { bold: true, color: INK } }, { text: "64GB+ / 服务器GPU", options: { align: "center", color: INK } }, { text: "集团 / 高精度场景", options: { color: MUTED } }]
  ];
  s.addTable(hw, { x: 0.9, y: 2.0, w: 6.3, h: 2.6, colW: [1.9, 2.1, 2.3], border: { pt: 0.75, color: BORDER }, fontFace: BODY, fontSize: 12, rowH: 0.55, valign: "middle" });
  s.addText("三步快速实施", { x: 0.9, y: 5.0, w: 6, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  const impl = [
    ["server", "部署模型引擎", "内网安装 Ollama 与 DeepSeek 模型，离线安装包支持"],
    ["folder", "导入企业知识", "批量上传制度 / 工艺 / 售后文档，自动解析入库"],
    ["handshake", "培训与上线", "管理员培训、权限配置、演示数据就绪，一天即可上线"]
  ];
  let iy = 5.45;
  impl.forEach(([ik, t, d]) => {
    s.addShape("rect", { x: 0.9, y: iy, w: 6.3, h: 0.52, fill: { color: "FFFFFF" }, line: { color: BORDER, width: 1 }, rectRadius: 0.05 });
    s.addImage({ data: IC[ik], x: 1.05, y: iy + 0.11, w: 0.3, h: 0.3 });
    s.addText(t, { x: 1.5, y: iy + 0.02, w: 1.7, h: 0.48, fontFace: HEAD, fontSize: 12, bold: true, color: NAVY, valign: "middle", margin: 0 });
    s.addText(d, { x: 3.2, y: iy + 0.02, w: 3.9, h: 0.48, fontFace: BODY, fontSize: 10.5, color: MUTED, valign: "middle", margin: 0 });
    iy += 0.62;
  });
  s.addShape("rect", { x: 7.6, y: 1.55, w: 4.83, h: 5.3, fill: { color: NAVY }, rectRadius: 0.1 });
  s.addText("为什么选择我们这套方案", { x: 7.95, y: 1.85, w: 4.1, h: 0.4, fontFace: HEAD, fontSize: 16, bold: true, color: "FFFFFF", margin: 0 });
  s.addText(runList(["已交付 3 个同源 AI 平台，架构成熟稳定", "演示系统开箱即用：模拟模式 + 真实模式双通道", "中文场景深度优化，回答贴合企业业务语言", "纯内网部署，无需改造现有网络", "支持从演示环境平滑升级到生产环境"]), { x: 7.95, y: 2.45, w: 4.15, h: 3.0, fontFace: BODY, fontSize: 12.5, color: "D8E1F5", paraSpaceAfter: 10, lineSpacing: 1.15 });
  s.addShape("rect", { x: 7.95, y: 5.7, w: 4.1, h: 0.8, fill: { color: "1D2A5C" }, line: { color: TEAL, width: 1 }, rectRadius: 0.06 });
  s.addText("1 天部署 · 当天可演示", { x: 7.95, y: 5.7, w: 4.1, h: 0.8, fontFace: HEAD, fontSize: 14, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  footer(s, 9, TOTAL);

  /* ============ S10 价值总结 ============ */
  s = pres.addSlide();
  contentHead(s, IC, "价值总结：看得见的变化", "对湖州企业而言，这套系统的价值可以用四组数字概括");
  const stats = [
    ["tacho", "小时级 → 秒级", "知识检索效率", "原先人工翻找数小时，现在智能问答秒级返回"],
    ["shield", "0 出域", "敏感数据", "模型 / 知识 / 推理全本地化，数据主权自持"],
    ["clock", "7×24", "持续在线", "不受公有云 API 限流、波动与涨价影响"],
    ["book", "100%", "知识沉淀", "老师傅经验结构化入库，人走经验留"]
  ];
  let sx2 = 0.9;
  stats.forEach(([ik, num, label, d]) => {
    s.addShape("rect", { x: sx2, y: 1.7, w: 2.78, h: 3.6, fill: { color: CARD }, line: { color: BORDER, width: 1 }, rectRadius: 0.08, shadow: makeShadow() });
    iconCircle(s, IC, ik, sx2 + 1.09, 2.0, 0.6, TEAL_LIGHT);
    s.addText(num, { x: sx2 + 0.1, y: 2.85, w: 2.58, h: 0.75, fontFace: HEAD, fontSize: 30, bold: true, color: NAVY, align: "center", margin: 0 });
    s.addText(label, { x: sx2 + 0.1, y: 3.7, w: 2.58, h: 0.4, fontFace: HEAD, fontSize: 13, bold: true, color: TEAL_D, align: "center", margin: 0 });
    s.addText(d, { x: sx2 + 0.25, y: 4.2, w: 2.28, h: 1.0, fontFace: BODY, fontSize: 10.5, color: MUTED, align: "center", lineSpacing: 1.2, margin: 0 });
    sx2 += 2.98;
  });
  s.addShape("rect", { x: 0.9, y: 5.6, w: 11.53, h: 1.15, fill: { color: TEAL_LIGHT }, rectRadius: 0.08 });
  s.addText("从「找文档」到「问知识」，从「怕泄密」到「放心用」—— 让湖州企业的知识真正变成资产。", { x: 1.2, y: 5.6, w: 10.9, h: 1.15, fontFace: HEAD, fontSize: 15.5, bold: true, color: TEAL_D, valign: "middle", margin: 0 });
  footer(s, 10, TOTAL);

  /* ============ S11 结束页 ============ */
  s = pres.addSlide();
  s.background = { color: NAVY_DARK };
  s.addShape("rect", { x: 0, y: H - 0.14, w: W, h: 0.14, fill: { color: TEAL } });
  iconCircle(s, IC, "shield", 6.27, 1.35, 0.8, "1D2A5C");
  s.addImage({ data: IC["network"], x: 6.52, y: 1.6, w: 0.3, h: 0.3 });
  s.addText("谢谢观看", { x: 1.67, y: 2.6, w: 10, h: 1.1, fontFace: HEAD, fontSize: 54, bold: true, color: "FFFFFF", align: "center", margin: 0 });
  s.addText("湖企智库 · 让企业知识安全地聪明起来", { x: 1.67, y: 3.95, w: 10, h: 0.5, fontFace: HEAD, fontSize: 18, color: "D8E1F5", align: "center", margin: 0 });
  s.addShape("rect", { x: 5.87, y: 4.7, w: 1.6, h: 0.045, fill: { color: TEAL } });
  s.addText("演示版本 · 欢迎现场体验", { x: 1.67, y: 5.15, w: 10, h: 0.4, fontFace: BODY, fontSize: 13, color: "9FB4D8", align: "center", margin: 0 });

  await pres.writeFile({ fileName: "/Users/cayden/WorkBuddy/2026-07-31-17-28-37/local_kb_system/ppt/out/湖企智库_方案演示.pptx" });
  console.log("PPT generated OK");
})().catch((e) => { console.error(e); process.exit(1); });
