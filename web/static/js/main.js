const DATA_ROOT = "./data/mountain_windows";

const DATA_PATHS = {
  index: `${DATA_ROOT}/mountain_window_index.json`,
  summary: `${DATA_ROOT}/mountain_summary.json`,
  sideWidth: `${DATA_ROOT}/mountain_side_width_summary.json`,
  systemSummary: `${DATA_ROOT}/mountain_system_summary.json`,
  windowsTable: `${DATA_ROOT}/mountain_windows_table.json`,
  segmentsTable: `${DATA_ROOT}/mountain_segments_table.json`,
};

// 窗口地图分级口径：
// 使用“所有山脉 + 主判读侧宽 + 可靠窗口”的 local_CBI 统一计算 4 类 Jenks 自然断点。
// 4 类来自 06b 原始 local_CBI 分级逻辑：k = min(4, len(unique_values))。
const WINDOW_CBI_NATURAL_CLASS_COUNT = 4;
const WINDOW_CBI_COLORS = ["#b7c7d6", "#6aaed6", "#f2b84b", "#8b1e2d"];
const WINDOW_CBI_LEVEL_LABELS = ["很弱", "弱", "较强", "强"];

const state = {
  index: null,
  summaryRows: [],
  sideWidthRows: [],
  mountainSystemRows: [],
  windowRows: [],
  segmentRows: [],
  windowCbiNaturalBreaks: [],
  windowCbiBreakSourceCount: 0,
  geoCache: new Map(),
  map: null,
  boundaryLayer: null,
  windowLayer: null,
  segmentLayer: null,
  pointLayer: null,
  charts: {},
};

const elements = {
  mountainInput: document.getElementById("mountainSearchInput"),
  mountainSelect: document.getElementById("mountainSelect"),
  mountainList: document.getElementById("mountainList"),
  windowColorSelect: document.getElementById("windowColorSelect"),
  mapModeSelect: document.getElementById("mapModeSelect"),
  queryButton: document.getElementById("queryButton"),
  statusMessage: document.getElementById("statusMessage"),
  errorMessage: document.getElementById("errorMessage"),
  mapMeta: document.getElementById("mapMeta"),
  legendContent: document.getElementById("legendContent"),
  interpretationText: document.getElementById("interpretationText"),
};

const metricElements = {
  mountainCbi: document.getElementById("metricMountainCbi"),
  mountainLevel: document.getElementById("metricMountainLevel"),
  localSignal: document.getElementById("metricLocalSignal"),
  localLevel: document.getElementById("metricLocalLevel"),
  sideWidth: document.getElementById("metricSideWidth"),
  reliableCoverage: document.getElementById("metricReliableCoverage"),
  highCoverage: document.getElementById("metricHighCoverage"),
  segmentRatio: document.getElementById("metricSegmentRatio"),
  evidence: document.getElementById("metricEvidence"),
};

function initMap() {
  const map = L.map("map", {
    zoomControl: true,
    preferCanvas: true,
  }).setView([35.6, 104.5], 4);

  const baseLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  const boundaryLayer = L.geoJSON(null, {
    style: {
      color: "#243447",
      weight: 3,
      opacity: 0.95,
      dashArray: "8 6",
    },
  }).addTo(map);

  const windowLayer = L.geoJSON(null, {
    style: windowStyle,
    onEachFeature: bindWindowPopup,
  }).addTo(map);

  const segmentLayer = L.geoJSON(null, {
    style: {
      color: "#f2b84b",
      weight: 8,
      opacity: 0.94,
      lineCap: "round",
    },
    onEachFeature: bindSegmentPopup,
  }).addTo(map);

  const pointLayer = L.geoJSON(null, {
    pointToLayer: (feature, latlng) => {
      const side = feature.properties?.side || "未知";
      return L.circleMarker(latlng, {
        radius: 4.2,
        color: "#ffffff",
        weight: 0.8,
        fillColor: side === "A" ? "#1e5b89" : side === "B" ? "#c37d2e" : "#8fa3b5",
        fillOpacity: 0.82,
      });
    },
    onEachFeature: bindPointPopup,
  }).addTo(map);

  L.control.layers(
    { OpenStreetMap: baseLayer },
    {
      "山脉线": boundaryLayer,
      "移动窗口 CBI": windowLayer,
      "分异连续段": segmentLayer,
      "地名特征点": pointLayer,
    },
    { collapsed: false }
  ).addTo(map);

  state.map = map;
  state.boundaryLayer = boundaryLayer;
  state.windowLayer = windowLayer;
  state.segmentLayer = segmentLayer;
  state.pointLayer = pointLayer;
}

function initCharts() {
  state.charts.windowCbi = echarts.init(document.getElementById("windowCbiChart"));
  state.charts.smallBig = echarts.init(document.getElementById("smallBigChart"));
  state.charts.sideWidth = echarts.init(document.getElementById("sideWidthChart"));
  state.charts.segment = echarts.init(document.getElementById("segmentChart"));

  window.addEventListener("resize", () => {
    Object.values(state.charts).forEach((chart) => chart.resize());
  });
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} 读取失败，HTTP ${response.status}`);
  }
  return response.json();
}

async function loadInitialData() {
  try {
    setStatus("正在读取 06b 静态索引和指标表……");
    const [index, summaryRows, sideWidthRows, mountainSystemRows, windowRows, segmentRows] = await Promise.all([
      fetchJson(DATA_PATHS.index),
      fetchJson(DATA_PATHS.summary),
      fetchJson(DATA_PATHS.sideWidth),
      fetchJson(DATA_PATHS.systemSummary),
      fetchJson(DATA_PATHS.windowsTable),
      fetchJson(DATA_PATHS.segmentsTable),
    ]);

    state.index = index;
    state.summaryRows = Array.isArray(summaryRows) ? summaryRows : [];
    state.sideWidthRows = Array.isArray(sideWidthRows) ? sideWidthRows : [];
    state.mountainSystemRows = Array.isArray(mountainSystemRows) ? mountainSystemRows : [];
    state.windowRows = Array.isArray(windowRows) ? windowRows : [];
    state.segmentRows = Array.isArray(segmentRows) ? segmentRows : [];

    computeWindowCbiNaturalBreaks();
    ensureInfoPanels();
    fillMountainOptions();

    elements.queryButton.disabled = false;
    clearError();
    setStatus("06b 静态数据读取完成。请输入或选择山脉名称。");
  } catch (error) {
    console.error(error);
    showError(
      "未找到 06b 网页静态数据。请先运行 scripts/06b_mountain_moving_window_cbi.py，"
      + "再运行 scripts/09_export_mountain_window_web_data.py。"
    );
    setStatus("数据尚未就绪。");
    elements.queryButton.disabled = true;
  }
}

function fillMountainOptions() {
  const mountains = getMountainNames();
  elements.mountainSelect.innerHTML = "";
  elements.mountainList.innerHTML = "";

  mountains.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    elements.mountainSelect.appendChild(option);

    const dataOption = document.createElement("option");
    dataOption.value = name;
    elements.mountainList.appendChild(dataOption);
  });

  if (mountains.length > 0) {
    elements.mountainInput.value = mountains[0];
  }
}

function getMountainNames() {
  const fromIndex = state.index?.mountains?.map((row) => row.boundary_name) || [];
  if (fromIndex.length) return fromIndex;
  return state.summaryRows.map((row) => row.boundary_name).filter(Boolean);
}

function findMountainMeta(name) {
  return (state.index?.mountains || []).find((row) => row.boundary_name === name) || null;
}

function getSummaryRow(name) {
  return state.summaryRows.find((row) => row.boundary_name === name) || null;
}

function splitPipeList(value) {
  if (!value || value === null) return [];
  return String(value).split("|").map((item) => item.trim()).filter(Boolean);
}

function getMountainSystemRow(name) {
  return state.mountainSystemRows.find((row) => {
    const systemName = row.mountain_system_name || "";
    const found = splitPipeList(row.sub_mountains_found);
    const configured = splitPipeList(row.sub_mountains_configured);
    return systemName === name
      || found.includes(name)
      || configured.includes(name)
      || (name === "横断山" && systemName === "横断山系");
  }) || null;
}

function getPrimaryWidth(name) {
  const summary = getSummaryRow(name);
  return Number(summary?.primary_side_width_km ?? summary?.side_width_km ?? 50);
}

function getPrimaryWindowRows(name) {
  const width = getPrimaryWidth(name);
  return state.windowRows
    .filter((row) => row.boundary_name === name && Number(row.side_width_km) === width)
    .sort((a, b) => Number(a.center_station_km) - Number(b.center_station_km));
}

function getPrimarySegmentRows(name) {
  const width = getPrimaryWidth(name);
  return state.segmentRows
    .filter((row) => row.boundary_name === name && Number(row.side_width_km) === width)
    .sort((a, b) => Number(a.start_station_km) - Number(b.start_station_km));
}

function getSideWidthRows(name) {
  return state.sideWidthRows
    .filter((row) => row.boundary_name === name)
    .sort((a, b) => Number(a.side_width_km) - Number(b.side_width_km));
}

function isTruthy(value) {
  return value === true || value === "true" || value === "True" || value === 1 || value === "1";
}

function isCbiMetric(metric) {
  return metric === "CBI" || metric === "small_CBI" || metric === "big_CBI";
}

function computeWindowCbiNaturalBreaks() {
  const primaryWidthByMountain = new Map();

  state.summaryRows.forEach((row) => {
    if (!row.boundary_name) return;
    const width = Number(row.primary_side_width_km ?? row.side_width_km);
    if (Number.isFinite(width)) {
      primaryWidthByMountain.set(row.boundary_name, width);
    }
  });

  const values = state.windowRows
    .filter((row) => {
      const primaryWidth = primaryWidthByMountain.get(row.boundary_name);
      const sideWidth = Number(row.side_width_km);
      const value = Number(row.CBI);
      return Number.isFinite(primaryWidth)
        && Number.isFinite(sideWidth)
        && Math.abs(sideWidth - primaryWidth) < 1e-6
        && isTruthy(row.reliable_window)
        && Number.isFinite(value);
    })
    .map((row) => Number(row.CBI))
    .sort((a, b) => a - b);

  state.windowCbiBreakSourceCount = values.length;
  state.windowCbiNaturalBreaks = jenksNaturalBreaks(values, WINDOW_CBI_NATURAL_CLASS_COUNT);

  console.info(
    "window local_CBI Jenks breaks from primary reliable windows:",
    state.windowCbiNaturalBreaks,
    "n=",
    state.windowCbiBreakSourceCount
  );
}

function jenksNaturalBreaks(values, maxClasses = 4) {
  const sorted = values
    .map(Number)
    .filter(Number.isFinite)
    .sort((a, b) => a - b);

  if (!sorted.length) return [];

  const uniqueCount = new Set(sorted.map((value) => value.toFixed(12))).size;
  const k = Math.min(maxClasses, uniqueCount, sorted.length);

  if (k <= 1) {
    return [sorted[0], sorted[sorted.length - 1]];
  }

  const n = sorted.length;
  const lower = Array.from({ length: n + 1 }, () => Array(k + 1).fill(0));
  const variance = Array.from({ length: n + 1 }, () => Array(k + 1).fill(Infinity));

  for (let i = 1; i <= k; i += 1) {
    lower[1][i] = 1;
    variance[1][i] = 0;
  }

  for (let l = 2; l <= n; l += 1) {
    let sum = 0;
    let sumSquares = 0;
    let weight = 0;
    let currentVariance = 0;

    for (let m = 1; m <= l; m += 1) {
      const lowerClassLimit = l - m + 1;
      const value = sorted[lowerClassLimit - 1];
      sum += value;
      sumSquares += value * value;
      weight += 1;
      currentVariance = sumSquares - (sum * sum) / weight;
      const previousIndex = lowerClassLimit - 1;

      if (previousIndex === 0) continue;

      for (let j = 2; j <= k; j += 1) {
        const candidate = currentVariance + variance[previousIndex][j - 1];
        if (variance[l][j] >= candidate) {
          lower[l][j] = lowerClassLimit;
          variance[l][j] = candidate;
        }
      }
    }

    lower[l][1] = 1;
    variance[l][1] = currentVariance;
  }

  const breaks = Array(k + 1).fill(0);
  breaks[0] = sorted[0];
  breaks[k] = sorted[n - 1];

  let count = k;
  let idx = n;

  while (count >= 2) {
    const splitIndex = Math.max(0, Math.min(n - 1, lower[idx][count] - 2));
    breaks[count - 1] = sorted[splitIndex];
    idx = lower[idx][count] - 1;
    count -= 1;
  }

  return breaks;
}

async function loadGeoJson(relativePath) {
  const fullPath = `${DATA_ROOT}/${relativePath.replace(/^mountain_windows\//, "")}`;
  if (!state.geoCache.has(fullPath)) {
    state.geoCache.set(fullPath, fetchJson(fullPath));
  }
  return state.geoCache.get(fullPath);
}

function getCurrentMountainName() {
  const typed = (elements.mountainInput.value || "").trim();
  if (typed) return typed;
  return elements.mountainSelect.value;
}

async function runQuery() {
  clearError();
  const mountainName = getCurrentMountainName();
  const meta = findMountainMeta(mountainName);

  if (!meta) {
    showError(`没有找到“${mountainName}”的网页数据。请检查山脉名称或重新运行 09 导出脚本。`);
    return;
  }

  try {
    setStatus(`正在加载 ${mountainName} 的山脉线、移动窗口和连续段 GeoJSON……`);

    const [boundaryGeoJson, windowGeoJson, segmentGeoJson, pointGeoJson] = await Promise.all([
      loadGeoJson(meta.boundary_file),
      loadGeoJson(meta.window_file),
      loadGeoJson(meta.segment_file),
      loadGeoJson(meta.point_file),
    ]);

    renderMap(boundaryGeoJson, windowGeoJson, segmentGeoJson, pointGeoJson);
    renderMetrics(mountainName);
    renderMountainSystemPanel(mountainName);
    renderIndexReadingGuide(mountainName);
    renderCharts(mountainName);
    renderInterpretation(mountainName);

    const summary = getSummaryRow(mountainName);
    const sideWidth = summary?.primary_side_width_km ?? meta.primary_side_width_km;
    const cbiText = meta.has_cbi ? `窗口 ${meta.n_windows} 个 | 连续段 ${meta.n_segments} 个` : "样本不足/无有效窗口";

    elements.mapMeta.textContent = `${mountainName} | 主侧宽 ${formatNumber(sideWidth, 0)} km | ${cbiText} | 地名点 ${meta.n_place_points || 0} 个`;
    setStatus("查询完成。");
  } catch (error) {
    console.error(error);
    showError(`查询失败：${error.message}`);
    setStatus("查询失败。");
  }
}

function renderMap(boundaryGeoJson, windowGeoJson, segmentGeoJson, pointGeoJson) {
  const mode = elements.mapModeSelect.value;

  state.boundaryLayer.clearLayers();
  state.windowLayer.clearLayers();
  state.segmentLayer.clearLayers();
  state.pointLayer.clearLayers();

  if (mode === "all" || mode === "points") {
    state.boundaryLayer.addData(boundaryGeoJson);
  }
  if (mode === "all" || mode === "windows") {
    state.windowLayer.addData(windowGeoJson);
  }
  if (mode === "all" || mode === "segments") {
    state.segmentLayer.addData(segmentGeoJson);
  }
  if (mode === "all" || mode === "points") {
    state.pointLayer.addData(pointGeoJson);
  }

  updateLegend();
  fitCurrentMapBounds();
}

function fitCurrentMapBounds() {
  const layers = [
    ...state.boundaryLayer.getLayers(),
    ...state.windowLayer.getLayers(),
    ...state.segmentLayer.getLayers(),
    ...state.pointLayer.getLayers(),
  ];

  if (!layers.length) return;

  const group = L.featureGroup(layers);
  const bounds = group.getBounds();

  if (bounds.isValid()) {
    state.map.fitBounds(bounds.pad(0.12));
  }
}

function windowStyle(feature) {
  const metric = elements.windowColorSelect.value;
  const value = Number(feature.properties?.[metric] ?? 0);

  return {
    color: getValueColor(value, metric),
    weight: feature.properties?.valid_contrast_window ? 7 : 5,
    opacity: feature.properties?.reliable_window ? 0.88 : 0.42,
    lineCap: "round",
  };
}

function getValueColor(value, metric) {
  if (metric === "window_membership_change_ratio") {
    if (value >= 0.50) return "#8b1e2d";
    if (value >= 0.25) return "#d05d2d";
    if (value >= 0.10) return "#f2b84b";
    return "#2f8f6b";
  }

  if (metric === "sample_balance") {
    if (value >= 0.80) return "#2f8f6b";
    if (value >= 0.60) return "#6aaed6";
    if (value >= 0.40) return "#f2b84b";
    return "#d05d2d";
  }

  if (isCbiMetric(metric)) {
    return getWindowCbiNaturalColor(value);
  }

  return "#6aaed6";
}

function getWindowCbiNaturalClassIndex(value) {
  const breaks = state.windowCbiNaturalBreaks;
  if (!Number.isFinite(value) || !breaks || breaks.length < 2) return 0;

  const upperBreaks = breaks.slice(1);

  for (let i = 0; i < upperBreaks.length; i += 1) {
    if (value <= upperBreaks[i] || i === upperBreaks.length - 1) {
      return Math.max(0, Math.min(i, WINDOW_CBI_COLORS.length - 1));
    }
  }

  return WINDOW_CBI_COLORS.length - 1;
}

function getWindowCbiNaturalColor(value) {
  return WINDOW_CBI_COLORS[getWindowCbiNaturalClassIndex(value)];
}

function bindWindowPopup(feature, layer) {
  const p = feature.properties || {};

  layer.bindPopup(`
    <div class="popup-card">
      <strong>移动窗口 #${escapeHtml(p.window_id ?? "—")}</strong>
      <div>station：${formatNumber(p.start_station_km)} - ${formatNumber(p.end_station_km)} km</div>
      <div>CBI：${formatNumber(p.CBI)} | small：${formatNumber(p.small_CBI)} | big：${formatNumber(p.big_CBI)}</div>
      <div>分位数等级：${escapeHtml(p.CBI_quantile_level || p.CBI_level || "—")} | 自然断点等级：${escapeHtml(p.CBI_natural_level || "—")}</div>
      <div>分级一致：${formatBool(p.CBI_level_agreement)} | 可靠：${formatBool(p.reliable_window)}</div>
      <div>A/B 点数：${escapeHtml(p.n_left ?? "—")} / ${escapeHtml(p.n_right ?? "—")}</div>
      <div>主导社区：A=${escapeHtml(p.top_A || "—")}，B=${escapeHtml(p.top_B || "—")}</div>
      <div>clip 风险：${escapeHtml(p.clip_risk_level || "—")}；station：${escapeHtml(p.station_reference_quality || "—")}</div>
    </div>
  `);
}

function bindSegmentPopup(feature, layer) {
  const p = feature.properties || {};

  layer.bindPopup(`
    <div class="popup-card">
      <strong>分异连续段 #${escapeHtml(p.contrast_segment_id ?? "—")}</strong>
      <div>范围：${formatNumber(p.start_station_km)} - ${formatNumber(p.end_station_km)} km</div>
      <div>长度：${formatNumber(p.contrast_segment_length_km)} km</div>
      <div>平均 local_CBI：${formatNumber(p.segment_local_CBI_mean)}</div>
      <div>最大 local_CBI：${formatNumber(p.segment_local_CBI_max)}</div>
      <div>主导社区：A=${escapeHtml(p.dominant_A_mode || "—")}，B=${escapeHtml(p.dominant_B_mode || "—")}</div>
    </div>
  `);
}

function bindPointPopup(feature, layer) {
  const p = feature.properties || {};
  const displayName = p.clean_name || p.raw_name || p.full_name || "未命名";

  layer.bindPopup(`
    <div class="popup-card">
      <strong>${escapeHtml(displayName)}</strong>
      <div>原始地名：${escapeHtml(p.raw_name || p.full_name || "—")}</div>
      <div>name_body：${escapeHtml(p.name_body || "—")}</div>
      <div>特征字 char：${escapeHtml(p.char || "—")}</div>
      <div>small_feature：${escapeHtml(p.small_feature || p.feature_id || "—")}</div>
      <div>big_feature：${escapeHtml(p.big_feature || p.semantic_type || "—")}</div>
      <div>community_id：${escapeHtml(p.community_id || "—")}</div>
      <div>side：${escapeHtml(p.side || "—")}；dist_m：${formatNumber(p.dist_m, 1)}</div>
      <div>station_km：${formatNumber(Number(p.station_m || 0) / 1000, 2)}</div>
    </div>
  `);
}

function updateLegend() {
  const metric = elements.windowColorSelect.value;
  let labels;

  if (metric === "window_membership_change_ratio") {
    labels = [
      ["低 < 0.10", "#2f8f6b"],
      ["中 0.10-0.25", "#f2b84b"],
      ["偏高 0.25-0.50", "#d05d2d"],
      ["高 ≥ 0.50", "#8b1e2d"],
    ];
  } else if (metric === "sample_balance") {
    labels = [
      ["低 < 0.40", "#d05d2d"],
      ["中 0.40-0.60", "#f2b84b"],
      ["较好 0.60-0.80", "#6aaed6"],
      ["好 ≥ 0.80", "#2f8f6b"],
    ];
  } else if (isCbiMetric(metric)) {
    labels = buildWindowCbiNaturalLegend(metric);
  } else {
    labels = [["当前指标", "#6aaed6"]];
  }

  elements.legendContent.innerHTML = labels.map(([label, color]) => `
    <div class="legend-item">
      <span class="legend-line" style="background:${color}"></span>
      <span>${label}</span>
    </div>
  `).join("");
}

function buildWindowCbiNaturalLegend(metric) {
  const breaks = state.windowCbiNaturalBreaks;

  if (!breaks || breaks.length < 2) {
    return [["自然断点未生成", "#b7c7d6"]];
  }

  const metricLabel = metric === "CBI" ? "local_CBI" : metric;
  const rows = [];

  for (let i = 0; i < breaks.length - 1; i += 1) {
    const left = formatNumber(breaks[i]);
    const right = formatNumber(breaks[i + 1]);
    const level = WINDOW_CBI_LEVEL_LABELS[i] || `第 ${i + 1} 类`;
    const prefix = i === 0 ? `${left}-${right}` : `>${left}-${right}`;

    rows.push([
      `${level} ${prefix}`,
      WINDOW_CBI_COLORS[Math.min(i, WINDOW_CBI_COLORS.length - 1)],
    ]);
  }

  rows.push([
    `${metricLabel} 自然断点：主侧宽可靠窗口 n=${state.windowCbiBreakSourceCount}`,
    "transparent",
  ]);

  return rows;
}

function renderMetrics(name) {
  const row = getSummaryRow(name) || {};
  const meta = findMountainMeta(name) || {};
  const noCbiLabel = meta.has_cbi === false ? "无有效窗口" : "未计算";

  metricElements.mountainCbi.textContent = row.mountain_CBI === undefined ? noCbiLabel : formatNumber(row.mountain_CBI);
  metricElements.mountainLevel.textContent = row.mountain_CBI_level || noCbiLabel;
  metricElements.localSignal.textContent = row.local_signal_CBI === undefined ? noCbiLabel : formatNumber(row.local_signal_CBI);
  metricElements.localLevel.textContent = row.local_signal_level || noCbiLabel;
  metricElements.sideWidth.textContent = `${formatNumber(row.primary_side_width_km ?? meta.primary_side_width_km, 0)} km`;
  metricElements.reliableCoverage.textContent = formatPercent(row.reliable_coverage_ratio);
  metricElements.highCoverage.textContent = formatPercent(row.high_CBI_coverage_ratio);
  metricElements.segmentRatio.textContent = formatPercent(row.contrast_segment_ratio);
  metricElements.evidence.textContent = row.evidence_quality || (meta.has_cbi === false ? "样本不足/无有效窗口" : "尚未计算 CBI");
}

/* ============================================================
   新增：自动插入“复合山系综合评价”和“指标阅读说明”面板
   不需要改 index.html，main.js 会自动创建 DOM。
============================================================ */

function ensureInfoPanels() {
  if (document.getElementById("mountainSystemPanel") && document.getElementById("indexReadingGuide")) {
    return;
  }

  const mapElement = document.getElementById("map");
  const mapSection = mapElement ? (mapElement.closest("section") || mapElement.parentElement) : null;
  const parent = mapSection?.parentElement || document.body;

  if (!document.getElementById("mountainSystemPanel")) {
    const panel = document.createElement("section");
    panel.id = "mountainSystemPanel";
    panel.style.display = "none";
    panel.style.margin = "20px 0";
    parent.insertBefore(panel, mapSection);
  }

  if (!document.getElementById("indexReadingGuide")) {
    const guide = document.createElement("section");
    guide.id = "indexReadingGuide";
    guide.style.margin = "20px 0";
    parent.insertBefore(guide, mapSection);
  }
}

function renderMountainSystemPanel(name) {
  ensureInfoPanels();

  const container = document.getElementById("mountainSystemPanel");
  if (!container) return;

  const row = getMountainSystemRow(name);

  if (!row) {
    container.innerHTML = "";
    container.style.display = "none";
    return;
  }

  container.style.display = "block";

  container.innerHTML = `
    <div style="
      background:#ffffff;
      border:1px solid #d8e5ef;
      border-radius:18px;
      padding:22px;
      box-shadow:0 8px 24px rgba(30, 60, 90, 0.06);
    ">
      <h2 style="margin:0 0 16px 0;color:#003459;font-size:22px;">复合山系综合评价</h2>

      <div style="
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
        gap:14px;
        margin-bottom:16px;
      ">
        ${metricBox("mountain_system_name", row.mountain_system_name)}
        ${metricBox("mountain_system_CBI", formatNumber(row.mountain_system_CBI))}
        ${metricBox("weighted_local_signal_CBI", formatNumber(row.weighted_local_signal_CBI))}
        ${metricBox("system_reliable_coverage_ratio", formatPercent(row.system_reliable_coverage_ratio))}
        ${metricBox("system_high_CBI_coverage_ratio", formatPercent(row.system_high_CBI_coverage_ratio))}
        ${metricBox("system_contrast_segment_ratio", formatPercent(row.system_contrast_segment_ratio))}
        ${metricBox("system_evidence_quality", row.system_evidence_quality || "—")}
        ${metricBox("n_sub_mountains_found", row.n_sub_mountains_found || 0)}
      </div>

      <div style="
        background:#f5f9fc;
        border-left:5px solid #1e5b89;
        padding:12px 14px;
        border-radius:10px;
        color:#243447;
        line-height:1.75;
        font-size:14px;
      ">
        <strong>阅读方式：</strong>
        单条山脉的 <code>mountain_CBI</code> 评价的是 shp 中某一条山脉线；
        <code>mountain_system_CBI</code> 评价的是复合山系，由多个子山脉按
        <strong>长度 × 可靠覆盖 × 置信度</strong> 加权汇总。
        对横断山这类复合山系，不能只看单条“横断山”线的 mountain_CBI。
      </div>

      <div style="margin-top:12px;color:#435b6d;line-height:1.8;font-size:14px;">
        <strong>已纳入子山脉：</strong>${escapeHtml(row.sub_mountains_found || "—")}<br/>
        <strong>缺失子山脉：</strong>${escapeHtml(row.sub_mountains_missing || "无")}<br/>
        <strong>系统解释：</strong>${escapeHtml(row.system_interpretation || "—")}
      </div>
    </div>
  `;
}

function renderIndexReadingGuide(name) {
  ensureInfoPanels();

  const container = document.getElementById("indexReadingGuide");
  if (!container) return;

  const row = getSummaryRow(name);
  const meta = findMountainMeta(name);
  const systemRow = getMountainSystemRow(name);

  const judgement = getMountainJudgement(row, meta);
  const specialNote = getSpecialMountainNote(name, systemRow);

  container.innerHTML = `
    <div style="
      background:#ffffff;
      border:1px solid #d8e5ef;
      border-radius:18px;
      padding:22px;
      box-shadow:0 8px 24px rgba(30, 60, 90, 0.06);
    ">
      <h2 style="margin:0 0 16px 0;color:#003459;font-size:22px;">怎样阅读和判断这些指标？</h2>

      <div style="
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
        gap:14px;
        margin-bottom:16px;
      ">
        ${explainBox("1. 先看 evidence_quality", "它判断结果能不能正式解释。无可靠窗口或诊断性证据不能直接下强结论；正式可靠最好；正式可用但需注意 clip 表示可以用，但要说明线性参考风险。")}
        ${explainBox("2. 再看 mountain_CBI", "它是整条山脉尺度综合指数，不等于某个窗口的 CBI。它综合 local_CBI 强度、可靠覆盖、高 CBI 覆盖、候选分异覆盖和连续段比例。")}
        ${explainBox("3. 再看 local_signal_CBI", "它表示有没有局部强信号。local_signal 高但 mountain_CBI 低，通常说明局部差异明显，但覆盖范围或连续性不足。")}
        ${explainBox("4. 看 reliable_coverage_ratio", "可靠覆盖比例越高，说明可靠窗口覆盖整条山脉越充分。覆盖比例低时，即使局部窗口很红，也不能说整条山脉强分隔。")}
        ${explainBox("5. 看 contrast_segment_ratio", "它表示地名文化社区分异连续段覆盖比例。为 0 不代表没有分隔作用，只代表没有识别到满足连续合并条件的连续段。")}
        ${explainBox("6. 看 clip 风险", "clip 风险高说明 station_m 线性参考或窗口归属可能受山脉线几何影响。可以用，但论文里要写谨慎解释。")}
      </div>

      <div style="
        background:#fff8e8;
        border-left:5px solid #f2b84b;
        padding:12px 14px;
        border-radius:10px;
        line-height:1.8;
        color:#4c3a14;
        margin-bottom:14px;
      ">
        <strong>当前查询判断：</strong>${judgement}
      </div>

      <div style="
        background:#eef6fb;
        border-left:5px solid #1e5b89;
        padding:12px 14px;
        border-radius:10px;
        line-height:1.8;
        color:#243447;
      ">
        <strong>核心原则：</strong><br/>
        ① 局部窗口 local_CBI 高，不等于整条山脉 mountain_CBI 高。<br/>
        ② 地图颜色显示的是窗口尺度 local_CBI，不是山脉整体等级。<br/>
        ③ 山脉整体判断应以 mountain_CBI、rank、evidence_quality、reliable_coverage_ratio 和 contrast_segment_ratio 综合判断。<br/>
        ④ 横断山这类复合山系，应同时参考 mountain_system_CBI。
        ${specialNote ? `<br/><br/><strong>特殊说明：</strong>${specialNote}` : ""}
      </div>

      <div style="margin-top:14px;color:#435b6d;line-height:1.8;font-size:14px;">
        <strong>当前数值：</strong>
        mountain_CBI=${formatNumber(row?.mountain_CBI)}；
        local_signal_CBI=${formatNumber(row?.local_signal_CBI)}；
        reliable_coverage=${formatPercent(row?.reliable_coverage_ratio)}；
        high_CBI_coverage=${formatPercent(row?.high_CBI_coverage_ratio)}；
        contrast_segment_ratio=${formatPercent(row?.contrast_segment_ratio)}；
        evidence_quality=${escapeHtml(row?.evidence_quality || "—")}。
      </div>
    </div>
  `;
}

function metricBox(label, value) {
  return `
    <div style="
      background:linear-gradient(180deg,#f6fbff,#ffffff);
      border:1px solid #d8e5ef;
      border-radius:14px;
      padding:14px 16px;
      min-height:78px;
    ">
      <div style="font-size:12px;color:#4f6f86;margin-bottom:10px;">${escapeHtml(label)}</div>
      <div style="font-size:22px;font-weight:800;color:#003459;">${escapeHtml(value ?? "—")}</div>
    </div>
  `;
}

function explainBox(title, text) {
  return `
    <div style="
      background:#f7fbff;
      border:1px solid #d8e5ef;
      border-radius:14px;
      padding:14px;
      line-height:1.75;
      color:#243447;
      font-size:14px;
    ">
      <div style="font-weight:700;color:#003459;margin-bottom:6px;">${escapeHtml(title)}</div>
      <div>${escapeHtml(text)}</div>
    </div>
  `;
}

function getMountainJudgement(row, meta) {
  if (!row) {
    if (meta?.has_cbi === false) {
      return "当前山脉没有形成有效 moving-window CBI，主要作为空间展示或样本不足案例，不宜判断文化分隔强弱。";
    }
    return "当前山脉暂无可用 CBI 指标。";
  }

  const cbi = Number(row.mountain_CBI || 0);
  const localSignal = Number(row.local_signal_CBI || 0);
  const reliableCoverage = Number(row.reliable_coverage_ratio || 0);
  const segmentRatio = Number(row.contrast_segment_ratio || 0);
  const evidence = String(row.evidence_quality || "");

  if (evidence.includes("无可靠窗口")) {
    return "无可靠窗口，不能正式判断山脉文化分隔强弱。";
  }

  if (evidence.includes("诊断性")) {
    return "结果更适合作为诊断性证据，不能作为论文主结论。";
  }

  if (localSignal >= 0.5 && reliableCoverage < 0.3) {
    return "局部地名文化分异信号较强，但可靠覆盖不足，更适合解释为局部强信号，而不是整条山脉强分隔。";
  }

  if (cbi >= 0.5 && reliableCoverage >= 0.3) {
    return "山脉尺度综合分隔证据较强，可作为重点解释对象，但仍需结合 clip 风险和连续段结果。";
  }

  if (cbi >= 0.25 || localSignal >= 0.35) {
    return "存在一定地名文化分异信号，但整体分隔强度需要结合覆盖比例和连续段比例谨慎解释。";
  }

  if (segmentRatio > 0) {
    return "虽然 mountain_CBI 不高，但存在地名文化社区分异连续段，可作为局部空间证据。";
  }

  return "当前结果显示山脉尺度综合分隔证据偏弱，若现实认知较强，应优先检查山脉线数据、侧宽设置和样本覆盖。";
}

function getSpecialMountainNote(name, systemRow) {
  if (name === "横断山") {
    return "当前“横断山”是 shp 中单条线要素，不能等同于完整横断山系。现实横断山更适合按高黎贡山、怒山、云岭、沙鲁里山、大雪山、邛崃山等子山脉构建复合山系指标。";
  }

  if (systemRow && systemRow.mountain_system_name) {
    return `${name} 属于 ${systemRow.mountain_system_name}，建议同时查看复合山系综合评价。`;
  }

  return "";
}

/* ============================================================
   图表
============================================================ */

function renderCharts(name) {
  const windows = getPrimaryWindowRows(name);
  const segments = getPrimarySegmentRows(name);
  const sideWidths = getSideWidthRows(name);

  renderWindowCbiChart(windows);
  renderSmallBigChart(windows);
  renderSideWidthChart(sideWidths);
  renderSegmentChart(segments);
}

function renderWindowCbiChart(windows) {
  state.charts.windowCbi.setOption({
    animationDuration: 500,
    tooltip: { trigger: "axis" },
    grid: { left: 54, right: 24, top: 38, bottom: 42 },
    xAxis: {
      type: "value",
      name: "station_km",
      axisLabel: { color: "#60788c" },
      splitLine: { lineStyle: { color: "rgba(215, 225, 235, 0.65)" } },
    },
    yAxis: {
      type: "value",
      name: "local_CBI",
      axisLabel: { color: "#60788c" },
      splitLine: { lineStyle: { color: "rgba(215, 225, 235, 0.65)" } },
    },
    series: [
      {
        name: "CBI",
        type: "line",
        smooth: true,
        symbolSize: 7,
        lineStyle: { color: "#1e5b89", width: 3 },
        itemStyle: { color: "#1e5b89" },
        areaStyle: { color: "rgba(30, 91, 137, 0.10)" },
        data: windows.map((row) => [Number(row.center_station_km), Number(row.CBI)]),
      },
    ],
  });
}

function renderSmallBigChart(windows) {
  const labels = windows.map((row) => Number(row.center_station_km));

  state.charts.smallBig.setOption({
    animationDuration: 500,
    tooltip: { trigger: "axis" },
    legend: { top: 0, textStyle: { color: "#60788c" } },
    grid: { left: 54, right: 24, top: 42, bottom: 42 },
    xAxis: {
      type: "category",
      name: "station_km",
      data: labels,
      axisLabel: { color: "#60788c" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#60788c" },
      splitLine: { lineStyle: { color: "rgba(215, 225, 235, 0.65)" } },
    },
    series: [
      {
        name: "small_CBI",
        type: "bar",
        itemStyle: { color: "#1e5b89" },
        data: windows.map((row) => Number(row.small_CBI || 0)),
      },
      {
        name: "big_CBI",
        type: "bar",
        itemStyle: { color: "#c37d2e" },
        data: windows.map((row) => Number(row.big_CBI || 0)),
      },
    ],
  });
}

function renderSideWidthChart(sideWidths) {
  state.charts.sideWidth.setOption({
    animationDuration: 500,
    tooltip: { trigger: "axis" },
    legend: { top: 0, textStyle: { color: "#60788c" } },
    grid: { left: 54, right: 24, top: 42, bottom: 42 },
    xAxis: {
      type: "category",
      data: sideWidths.map((row) => `${row.side_width_km} km`),
      axisLabel: { color: "#60788c" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#60788c" },
      splitLine: { lineStyle: { color: "rgba(215, 225, 235, 0.65)" } },
    },
    series: [
      {
        name: "选择得分",
        type: "line",
        smooth: true,
        data: sideWidths.map((row) => Number(row.side_width_selection_score || 0)),
        lineStyle: { color: "#1e5b89", width: 3 },
        itemStyle: { color: "#1e5b89" },
      },
      {
        name: "可靠覆盖",
        type: "bar",
        data: sideWidths.map((row) => Number(row.reliable_coverage_ratio || 0)),
        itemStyle: { color: "#9c6a2a" },
      },
    ],
  });
}

function renderSegmentChart(segments) {
  state.charts.segment.setOption({
    animationDuration: 500,
    tooltip: { trigger: "axis" },
    grid: { left: 90, right: 24, top: 32, bottom: 36 },
    xAxis: {
      type: "value",
      axisLabel: { color: "#60788c" },
      splitLine: { lineStyle: { color: "rgba(215, 225, 235, 0.65)" } },
    },
    yAxis: {
      type: "category",
      data: segments.map((row) => `段 ${row.contrast_segment_id}`).reverse(),
      axisLabel: { color: "#60788c" },
    },
    series: [
      {
        name: "segment_local_CBI_mean",
        type: "bar",
        itemStyle: { color: "#d05d2d", borderRadius: [0, 8, 8, 0] },
        data: segments.map((row) => Number(row.segment_local_CBI_mean || 0)).reverse(),
      },
    ],
  });
}

function renderInterpretation(name) {
  const row = getSummaryRow(name);

  if (!row) {
    const meta = findMountainMeta(name) || {};
    elements.interpretationText.textContent =
      `${name} 已从 raw 山脉 shp 中导出山脉线和地名点，可在地图上查看空间分布。`
      + `但当前 06b 结果表中该山脉未形成有效 moving-window CBI，通常意味着两侧样本不足或可靠窗口不足。`
      + `因此网页不强行给出 mountain_CBI 数值，以免把低证据区域误读为可靠分隔。`
      + `当前网页已加载地名点 ${meta.n_place_points || 0} 个。`;
    return;
  }

  const segmentText = Number(row.n_contrast_segments || 0) > 0
    ? `识别到 ${row.n_contrast_segments} 条地名文化社区分异连续段，说明局部山段存在连续的两侧社区结构差异。`
    : "未识别到满足合并条件的分异连续段，但这不代表山脉尺度文化分隔强度低，应结合 local_signal_CBI 与覆盖比例解释。";

  const systemRow = getMountainSystemRow(name);
  const systemText = systemRow
    ? ` 复合山系补充评价：${systemRow.mountain_system_name} 的 mountain_system_CBI 为 ${formatNumber(systemRow.mountain_system_CBI)}，`
      + `山系级证据质量为“${systemRow.system_evidence_quality || "—"}”，`
      + `可靠覆盖为 ${formatPercent(systemRow.system_reliable_coverage_ratio)}，`
      + `该值由 ${systemRow.n_sub_mountains_found || 0} 条子山脉按长度×可靠覆盖×置信度加权得到，不能与单条“${name}”线的 mountain_CBI 混为一谈。`
    : "";

  elements.interpretationText.textContent =
    `${name} 的 mountain_CBI 为 ${formatNumber(row.mountain_CBI)}，rank 为 ${escapeHtml(row.mountain_CBI_rank || "—")}；`
    + `自然断点展示等级为“${row.mountain_CBI_natural_level || row.mountain_CBI_level || "—"}”，证据质量为“${row.evidence_quality || "—"}”。`
    + `整体强弱判断以 mountain_CBI、rank 和 evidence_quality 为主，不以窗口地图颜色直接替代。`
    + ` local_signal_CBI 为 ${formatNumber(row.local_signal_CBI)}，当前主判读侧宽为 ${formatNumber(row.primary_side_width_km, 0)} km；`
    + `可靠覆盖比例为 ${formatPercent(row.reliable_coverage_ratio)}，高 CBI 覆盖比例为 ${formatPercent(row.high_CBI_coverage_ratio)}。`
    + `${segmentText} clip 风险为“${row.clip_risk_level || "—"}”，station 线性参考质量为“${row.station_reference_quality || "—"}”。`
    + systemText;
}

function syncInputFromSelect() {
  elements.mountainInput.value = elements.mountainSelect.value;
}

function syncSelectFromInput() {
  const typed = (elements.mountainInput.value || "").trim();
  const options = [...elements.mountainSelect.options];
  const match = options.find((option) => option.value === typed);

  if (match) {
    elements.mountainSelect.value = typed;
  }
}

function formatNumber(value, digits = 3) {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return num.toFixed(digits);
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  return `${(num * 100).toFixed(1)}%`;
}

function formatBool(value) {
  if (value === true || value === "True" || value === "true") return "是";
  if (value === false || value === "False" || value === "false") return "否";
  return "—";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(text) {
  elements.statusMessage.textContent = text;
}

function showError(text) {
  elements.errorMessage.hidden = false;
  elements.errorMessage.textContent = text;
}

function clearError() {
  elements.errorMessage.hidden = true;
  elements.errorMessage.textContent = "";
}

elements.mountainSelect.addEventListener("change", syncInputFromSelect);
elements.mountainInput.addEventListener("input", syncSelectFromInput);
elements.queryButton.addEventListener("click", runQuery);

elements.windowColorSelect.addEventListener("change", () => {
  if (state.windowLayer) {
    state.windowLayer.setStyle(windowStyle);
    updateLegend();
  }
});

elements.mapModeSelect.addEventListener("change", runQuery);

initMap();
initCharts();
loadInitialData();