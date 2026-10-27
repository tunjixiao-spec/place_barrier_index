const DATA_ROOT = "./data/mountain_windows";

const DATA_PATHS = {
  index: `${DATA_ROOT}/mountain_window_index.json`,
  summary: `${DATA_ROOT}/mountain_summary.json`,
  sideWidth: `${DATA_ROOT}/mountain_side_width_summary.json`,
  systemSummary: `${DATA_ROOT}/mountain_system_summary.json`,
  windowsTable: `${DATA_ROOT}/mountain_windows_table.json`,
  segmentsTable: `${DATA_ROOT}/mountain_segments_table.json`,
};

const WINDOW_CBI_NATURAL_CLASS_COUNT = 4;
const WINDOW_CBI_COLORS = ["#b7c7d6", "#6aaed6", "#f2b84b", "#8b1e2d"];
const WINDOW_CBI_LEVEL_LABELS = ["很弱", "弱", "较强", "强"];

const MOUNTAIN_CBI_NATURAL_CLASS_COUNT = 4;
const MOUNTAIN_CBI_COLORS = ["#cfd8e3", "#6ea7d3", "#e5ae38", "#9e2238"];
const MOUNTAIN_CBI_LEVEL_LABELS = ["很弱", "弱", "较强", "强"];

const state = {
  index: null,
  summaryRows: [],
  sideWidthRows: [],
  mountainSystemRows: [],
  windowRows: [],
  segmentRows: [],

  windowCbiNaturalBreaks: [],
  windowCbiBreakSourceCount: 0,

  mountainCbiNaturalBreaks: [],
  mountainCbiBreakSourceCount: 0,

  geoCache: new Map(),

  map: null,
  boundaryLayer: null,
  windowLayer: null,
  segmentLayer: null,
  pointLayer: null,

  systemMap: null,
  systemLayers: [],

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
    if (state.map) state.map.invalidateSize();
    if (state.systemMap) state.systemMap.invalidateSize();
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
    computeMountainCbiNaturalBreaks();
    ensureSupplementPanels();
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
  return (state.index?.mountains || []).find((row) => String(row.boundary_name) === String(name)) || null;
}

function getSummaryRow(name) {
  return state.summaryRows.find((row) => String(row.boundary_name) === String(name)) || null;
}

function splitPipeList(value) {
  if (!value || value === null) return [];
  return String(value)
    .split(/[|、,，;；/]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function getMountainSystemRow(name) {
  return state.mountainSystemRows.find((row) => {
    const systemName = row.mountain_system_name || "";
    const found = splitPipeList(row.sub_mountains_found);
    const configured = splitPipeList(row.sub_mountains_configured);

    return String(systemName) === String(name)
      || found.includes(name)
      || configured.includes(name)
      || (name === "横断山" && systemName === "横断山系");
  }) || null;
}

function getSystemMemberNames(systemRow) {
  if (!systemRow) return [];

  const found = splitPipeList(systemRow.sub_mountains_found);
  if (found.length > 0) return found;

  return splitPipeList(systemRow.sub_mountains_configured);
}

function getSystemMemberRows(systemRow) {
  const names = getSystemMemberNames(systemRow);

  return names.map((name) => {
    return {
      name,
      meta: findMountainMeta(name),
      summary: getSummaryRow(name),
    };
  });
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
}

function computeMountainCbiNaturalBreaks() {
  const values = state.summaryRows
    .map((row) => Number(row.mountain_CBI))
    .filter((value) => Number.isFinite(value))
    .sort((a, b) => a - b);

  state.mountainCbiBreakSourceCount = values.length;

  if (values.length === 0) {
    state.mountainCbiNaturalBreaks = [];
    return;
  }

  const firstBreakText = state.summaryRows
    .map((row) => row.mountain_CBI_natural_breaks)
    .find((value) => value && String(value).includes("|"));

  if (firstBreakText) {
    const parsed = String(firstBreakText)
      .split("|")
      .map((x) => Number(x))
      .filter((x) => Number.isFinite(x));

    if (parsed.length >= 2) {
      state.mountainCbiNaturalBreaks = parsed;
      return;
    }
  }

  state.mountainCbiNaturalBreaks = jenksNaturalBreaks(values, MOUNTAIN_CBI_NATURAL_CLASS_COUNT);
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

function classifyByBreaks(value, breaks, labels, colors) {
  const x = Number(value);

  if (!Number.isFinite(x) || !breaks || breaks.length < 2) {
    return {
      levelNo: 0,
      level: "未评级",
      color: "#b7c7d6",
      range: "未评级",
    };
  }

  const upperBreaks = breaks.slice(1);
  let idx = upperBreaks.length - 1;

  for (let i = 0; i < upperBreaks.length; i += 1) {
    if (x <= upperBreaks[i]) {
      idx = i;
      break;
    }
  }

  const left = breaks[idx];
  const right = breaks[idx + 1];
  const label = labels[idx] || `第 ${idx + 1} 类`;
  const color = colors[Math.min(idx, colors.length - 1)];

  const range = idx === 0
    ? `${formatNumber(left)}-${formatNumber(right)}`
    : `>${formatNumber(left)}-${formatNumber(right)}`;

  return {
    levelNo: idx + 1,
    level: label,
    color,
    range,
  };
}

function classifyWindowCbi(value) {
  return classifyByBreaks(
    value,
    state.windowCbiNaturalBreaks,
    WINDOW_CBI_LEVEL_LABELS,
    WINDOW_CBI_COLORS
  );
}

function classifyMountainCbi(value) {
  return classifyByBreaks(
    value,
    state.mountainCbiNaturalBreaks,
    MOUNTAIN_CBI_LEVEL_LABELS,
    MOUNTAIN_CBI_COLORS
  );
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
    renderMetricReadingGuide(mountainName);
    await renderMountainSystemView(mountainName);
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
    return classifyWindowCbi(value).color;
  }

  return "#6aaed6";
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

function buildMountainCbiLegendRows() {
  const breaks = state.mountainCbiNaturalBreaks;

  if (!breaks || breaks.length < 2) {
    return [["自然断点未生成", "#b7c7d6"]];
  }

  const rows = [];

  for (let i = 0; i < breaks.length - 1; i += 1) {
    const left = formatNumber(breaks[i]);
    const right = formatNumber(breaks[i + 1]);
    const level = MOUNTAIN_CBI_LEVEL_LABELS[i] || `第 ${i + 1} 类`;
    const prefix = i === 0 ? `${left}-${right}` : `>${left}-${right}`;

    rows.push([
      `${level} ${prefix}`,
      MOUNTAIN_CBI_COLORS[Math.min(i, MOUNTAIN_CBI_COLORS.length - 1)],
    ]);
  }

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

function renderMetricReadingGuide(name) {
  const box = document.getElementById("metricReadingGuide");
  if (!box) return;

  const row = getSummaryRow(name);
  const systemRow = getMountainSystemRow(name);
  const mountainClass = classifyMountainCbi(row?.mountain_CBI);
  const systemClass = classifyMountainCbi(systemRow?.mountain_system_CBI);

  box.innerHTML = `
    <div class="guide-title">指标阅读说明</div>
    <div>
      <strong>mountain_CBI</strong>：单条线性山脉的综合分隔指数，是山脉尺度主指标。
      当前山脉 mountain_CBI=${formatNumber(row?.mountain_CBI)}，按线性山脉自然断点为“${mountainClass.level}”。<br>
      <strong>local_signal_CBI</strong>：局部强信号指标。它高，不代表整条山脉都强，只说明部分窗口差异明显。<br>
      <strong>reliable_coverage_ratio</strong>：可靠窗口覆盖比例。覆盖低时，不能把局部高值直接解释成整体强分隔。<br>
      <strong>high_CBI_coverage_ratio</strong>：高 local_CBI 窗口覆盖比例，用来判断强差异是否持续出现。<br>
      <strong>contrast_segment_ratio</strong>：地名文化社区分异连续段覆盖比例。为 0 不代表没有分隔作用，只代表未识别出满足合并条件的连续段。<br>
      <strong>evidence_quality</strong>：结果证据质量。若显示“需注意 clip”，说明结果可以用，但论文里要说明线性参考风险。
    </div>
    <ul>
      <li>地图颜色显示的是窗口尺度 local_CBI，不等于 mountain_CBI 山脉整体等级。</li>
      <li>整体判断建议按 mountain_CBI、rank、coverage、segment 和 evidence_quality 综合解释。</li>
      <li>${systemRow ? `当前山脉属于 ${systemRow.mountain_system_name}，山系 mountain_system_CBI=${formatNumber(systemRow.mountain_system_CBI)}，按同一套线性山脉自然断点为“${systemClass.level}”。` : "当前山脉暂未匹配到复合山系结果。"}</li>
    </ul>
  `;
}

/* ============================================================
   山系补充视图
============================================================ */

function ensureSupplementPanels() {
  const metricSection = metricElements.mountainCbi?.closest("section");
  const mainGrid = document.querySelector(".main-grid");

  if (!document.getElementById("metricReadingGuide") && metricSection) {
    const guide = document.createElement("div");
    guide.id = "metricReadingGuide";
    guide.className = "metric-reading-guide";
    guide.innerHTML = `
      <div class="guide-title">指标阅读说明</div>
      <div>查询山脉后，这里会解释 mountain_CBI、local_signal_CBI、覆盖比例和证据质量。</div>
    `;
    metricSection.appendChild(guide);
  }

  if (!document.getElementById("mountainSystemSection") && mainGrid) {
    const section = document.createElement("section");
    section.id = "mountainSystemSection";
    section.className = "panel panel-section";
    section.innerHTML = `
      <div class="section-header">
        <h2>山系补充视图</h2>
        <p class="section-subtitle">
          当当前山脉属于更大的复合山系时，这里补充展示该山系的整体分隔作用，以及山系内部各线性山脉之间的差异。
        </p>
      </div>

      <div id="mountainSystemMetricGrid" class="system-metric-grid">
        <div class="empty-note">请选择山脉后查看山系综合评价。</div>
      </div>

      <div id="mountainSystemGuide" class="mountain-system-guide">
        山系视图用于避免把“单条山脉线结果”误读为“整个山系结果”。
      </div>

      <div class="two-col-layout">
        <div class="map-panel">
          <div class="panel-title-row">
            <h3>山系可视化视图</h3>
            <span id="mountainSystemMapMeta" class="panel-meta">等待查询</span>
          </div>

          <div id="mountainSystemMap" class="map-box"></div>

          <div id="mountainSystemLegend" class="legend-box">
            <div class="legend-title">山系视图图例</div>
            <div>等待查询。</div>
          </div>
        </div>

        <div class="explain-panel">
          <h3>山系自动解释</h3>
          <div id="mountainSystemExplain" class="auto-explain-box">
            请选择或输入山脉名称，然后点击“查询 CBI”。
          </div>
        </div>
      </div>
    `;

    mainGrid.parentElement.insertBefore(section, mainGrid);
  }
}

async function renderMountainSystemView(name) {
  ensureSupplementPanels();

  const section = document.getElementById("mountainSystemSection");
  const metricGrid = document.getElementById("mountainSystemMetricGrid");
  const guideBox = document.getElementById("mountainSystemGuide");
  const explainBox = document.getElementById("mountainSystemExplain");
  const mapMeta = document.getElementById("mountainSystemMapMeta");
  const legendBox = document.getElementById("mountainSystemLegend");

  const systemRow = getMountainSystemRow(name);

  if (!systemRow) {
    if (section) section.style.display = "block";
    if (metricGrid) {
      metricGrid.innerHTML = `<div class="empty-note">当前山脉未匹配到复合山系结果，因此不生成山系补充视图。</div>`;
    }
    if (guideBox) {
      guideBox.innerHTML = "该山脉当前按单条线性山脉结果解释即可。";
    }
    if (explainBox) {
      explainBox.innerHTML = "暂无山系级 mountain_system_CBI。";
    }
    if (mapMeta) {
      mapMeta.textContent = "无山系数据";
    }
    if (legendBox) {
      legendBox.innerHTML = `<div class="legend-title">山系视图图例</div><div>无山系数据。</div>`;
    }
    clearSystemMap();
    return;
  }

  const members = getSystemMemberRows(systemRow);
  const currentSummary = getSummaryRow(name);

  renderMountainSystemMetrics(name, currentSummary, systemRow, members);
  renderMountainSystemGuide(name, systemRow);
  renderMountainSystemLegend();
  renderMountainSystemExplanation(name, currentSummary, systemRow, members);

  await renderMountainSystemMap(name, systemRow, members);

  if (mapMeta) {
    mapMeta.textContent = `${systemRow.mountain_system_name} | 成员 ${members.length} 条 | 颜色按线性山脉 mountain_CBI 自然断点`;
  }
}

function renderMountainSystemMetrics(name, currentSummary, systemRow, members) {
  const grid = document.getElementById("mountainSystemMetricGrid");
  if (!grid) return;

  const currentClass = classifyMountainCbi(currentSummary?.mountain_CBI);
  const systemClass = classifyMountainCbi(systemRow.mountain_system_CBI);

  grid.innerHTML = `
    ${systemMetricCard("mountain_system_name", systemRow.mountain_system_name || "—", "当前山脉所属复合山系")}
    ${systemMetricCard("mountain_system_CBI", formatNumber(systemRow.mountain_system_CBI), `按线性山脉自然断点：${systemClass.level}`)}
    ${systemMetricCard("weighted_local_signal_CBI", formatNumber(systemRow.weighted_local_signal_CBI), "山系加权局部信号")}
    ${systemMetricCard("system_reliable_coverage_ratio", formatPercent(systemRow.system_reliable_coverage_ratio), "山系级可靠覆盖比例")}
    ${systemMetricCard("system_high_CBI_coverage_ratio", formatPercent(systemRow.system_high_CBI_coverage_ratio), "山系级高 CBI 覆盖比例")}
    ${systemMetricCard("system_contrast_segment_ratio", formatPercent(systemRow.system_contrast_segment_ratio), "山系级连续分异段覆盖")}
    ${systemMetricCard("system_evidence_quality", systemRow.system_evidence_quality || "—", "山系证据质量")}
    ${systemMetricCard("member_count", members.length || "—", "纳入山系视图的线性山脉数量")}
    ${systemMetricCard("line_vs_system", `${currentClass.level} → ${systemClass.level}`, `${name}: ${formatNumber(currentSummary?.mountain_CBI)}；山系: ${formatNumber(systemRow.mountain_system_CBI)}`)}
  `;
}

function systemMetricCard(label, value, subText) {
  return `
    <div class="system-metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${escapeHtml(value ?? "—")}</div>
      <div class="metric-sub">${escapeHtml(subText || "")}</div>
    </div>
  `;
}

function renderMountainSystemGuide(name, systemRow) {
  const box = document.getElementById("mountainSystemGuide");
  if (!box) return;

  const breaksText = state.mountainCbiNaturalBreaks
    .map((x) => formatNumber(x))
    .join(" | ");

  box.innerHTML = `
    <strong>山系视图如何阅读：</strong>
    当前查询山脉 <strong>${escapeHtml(name)}</strong> 属于
    <strong>${escapeHtml(systemRow.mountain_system_name || "—")}</strong>。
    这里的地图不是把 mountain_system_CBI 直接涂到整条山系上，而是把山系内部每一条线性山脉的
    <strong>mountain_CBI</strong> 单独着色。
    颜色阈值沿用全部线性山脉 mountain_CBI 的 Jenks 自然断点：
    <strong>${escapeHtml(breaksText || "未生成")}</strong>。
    这样可以同时看出“山系整体强不强”和“山系内部哪些子山脉更强”。
  `;
}

function renderMountainSystemLegend() {
  const box = document.getElementById("mountainSystemLegend");
  if (!box) return;

  const rows = buildMountainCbiLegendRows();

  box.innerHTML = `
    <div class="legend-title">山系视图图例</div>
    <div class="legend-row">
      ${rows.map(([label, color]) => `
        <span class="legend-item">
          <span class="legend-swatch" style="background:${color};"></span>
          <span>${escapeHtml(label)}</span>
        </span>
      `).join("")}
    </div>
    <div class="legend-note">
      说明：颜色对应山系内部各线性山脉的 mountain_CBI，阈值来自全部线性山脉自然断点，n=${state.mountainCbiBreakSourceCount}。
    </div>
  `;
}

function renderMountainSystemExplanation(name, currentSummary, systemRow, members) {
  const box = document.getElementById("mountainSystemExplain");
  if (!box) return;

  const currentClass = classifyMountainCbi(currentSummary?.mountain_CBI);
  const systemClass = classifyMountainCbi(systemRow.mountain_system_CBI);

  const memberStats = members.map((m) => {
    const cls = classifyMountainCbi(m.summary?.mountain_CBI);
    return {
      name: m.name,
      cbi: Number(m.summary?.mountain_CBI),
      level: cls.level,
      evidence: m.summary?.evidence_quality || "—",
    };
  });

  const strongMembers = memberStats.filter((m) => ["较强", "强"].includes(m.level));
  const weakMembers = memberStats.filter((m) => ["很弱", "弱"].includes(m.level));

  const strongest = memberStats
    .filter((m) => Number.isFinite(m.cbi))
    .sort((a, b) => b.cbi - a.cbi)
    .slice(0, 3);

  const strongestText = strongest.length
    ? strongest.map((m) => `${m.name}(${formatNumber(m.cbi)}, ${m.level})`).join("、")
    : "暂无可比较成员";

  let structureText = "山系内部呈现混合型分异格局。";
  if (strongMembers.length > 0 && weakMembers.length > 0) {
    structureText = "山系内部同时存在较强成员和较弱成员，说明该复合山系内部文化分隔作用不均衡。";
  } else if (strongMembers.length > 0 && weakMembers.length === 0) {
    structureText = "山系内部多数成员达到较强及以上等级，说明该复合山系整体文化分隔作用较突出。";
  } else if (strongMembers.length === 0 && weakMembers.length > 0) {
    structureText = "山系内部成员多数处于较低等级，说明当前数据和模型下山系整体分隔证据偏弱。";
  }

  box.innerHTML = `
    <strong>${escapeHtml(name)}</strong> 的单条线性山脉 mountain_CBI 为
    <strong>${formatNumber(currentSummary?.mountain_CBI)}</strong>，
    按线性山脉自然断点等级为“<strong>${escapeHtml(currentClass.level)}</strong>”，
    证据质量为“<strong>${escapeHtml(currentSummary?.evidence_quality || "—")}</strong>”。<br><br>

    其所属 <strong>${escapeHtml(systemRow.mountain_system_name || "—")}</strong>
    的 mountain_system_CBI 为
    <strong>${formatNumber(systemRow.mountain_system_CBI)}</strong>，
    按同一套线性山脉自然断点等级为“<strong>${escapeHtml(systemClass.level)}</strong>”，
    山系证据质量为“<strong>${escapeHtml(systemRow.system_evidence_quality || "—")}</strong>”。<br><br>

    ${escapeHtml(structureText)} 当前山系成员中 CBI 较高的线性山脉包括：
    <strong>${escapeHtml(strongestText)}</strong>。<br><br>

    <strong>解释原则：</strong>
    单条“${escapeHtml(name)}”线的 mountain_CBI 不能直接代表完整山系。
    当单线结果受 clip 风险、样本覆盖或线数据完整性影响时，应结合山系成员视图和 mountain_system_CBI 综合解释。
  `;
}

function clearSystemMap() {
  if (state.systemMap) {
    state.systemMap.remove();
    state.systemMap = null;
    state.systemLayers = [];
  }

  const mapBox = document.getElementById("mountainSystemMap");
  if (mapBox) {
    mapBox.innerHTML = "";
  }
}

async function renderMountainSystemMap(currentName, systemRow, members) {
  const mapBox = document.getElementById("mountainSystemMap");
  if (!mapBox) return;

  clearSystemMap();

  if (!members.length) {
    mapBox.innerHTML = `<div class="empty-note">该山系没有可视化成员。</div>`;
    return;
  }

  const map = L.map("mountainSystemMap", {
    zoomControl: true,
    preferCanvas: true,
  }).setView([35.6, 104.5], 4);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap',
  }).addTo(map);

  const layers = [];

  for (const member of members) {
    if (!member.meta || !member.meta.boundary_file) continue;

    try {
      const geojson = await loadGeoJson(member.meta.boundary_file);
      const cls = classifyMountainCbi(member.summary?.mountain_CBI);
      const isCurrent = String(member.name) === String(currentName);

      const layer = L.geoJSON(geojson, {
        style: {
          color: cls.color,
          weight: isCurrent ? 6 : 4,
          opacity: isCurrent ? 1.0 : 0.82,
          dashArray: isCurrent ? null : "8 5",
        },
        onEachFeature: (feature, lyr) => {
          lyr.bindPopup(`
            <div class="popup-card">
              <strong>${escapeHtml(member.name)}</strong>
              <div>mountain_CBI：${formatNumber(member.summary?.mountain_CBI)}</div>
              <div>自然断点等级：${escapeHtml(cls.level)}</div>
              <div>rank：${escapeHtml(member.summary?.mountain_CBI_rank || "—")}</div>
              <div>evidence_quality：${escapeHtml(member.summary?.evidence_quality || "—")}</div>
              <div>reliable_coverage：${formatPercent(member.summary?.reliable_coverage_ratio)}</div>
              <div>high_CBI_coverage：${formatPercent(member.summary?.high_CBI_coverage_ratio)}</div>
            </div>
          `);
        },
      }).addTo(map);

      layers.push(layer);
    } catch (error) {
      console.warn(`山系成员 ${member.name} GeoJSON 加载失败：`, error);
    }
  }

  state.systemMap = map;
  state.systemLayers = layers;

  if (layers.length > 0) {
    const group = L.featureGroup(layers);
    const bounds = group.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.16));
    }
  }

  setTimeout(() => {
    map.invalidateSize();
  }, 200);
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

/* ============================================================
   自动解释
============================================================ */

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
  const systemClass = classifyMountainCbi(systemRow?.mountain_system_CBI);

  const systemText = systemRow
    ? ` 复合山系补充评价：${systemRow.mountain_system_name} 的 mountain_system_CBI 为 ${formatNumber(systemRow.mountain_system_CBI)}，`
      + `按线性山脉自然断点等级为“${systemClass.level}”，`
      + `山系级证据质量为“${systemRow.system_evidence_quality || "—"}”，`
      + `可靠覆盖为 ${formatPercent(systemRow.system_reliable_coverage_ratio)}。`
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

/* ============================================================
   表单与工具函数
============================================================ */

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
  return String(value ?? "")
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

/* ============================================================
   事件绑定
============================================================ */

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
