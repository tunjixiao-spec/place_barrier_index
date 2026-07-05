# ============================================================
# 06b_mountain_moving_window_cbi.py
# ============================================================
# 本脚本作用：
#   在原 06_barrier_index_by_communities.py 的基础上，
#   将“整条山脉整体 CBI”扩展为：
#
#   1. 移动窗口 local_CBI
#   2. 地名文化社区分异连续段 community differentiation segment
#   3. 山脉尺度文化分隔强度 mountain_CBI
#
# 重要概念区分：
#   community differentiation segment
#       = 地名文化社区分异连续段
#       = 连续多个窗口中，山脉两侧 community_id 构成存在差异
#       = 这是中间现象识别结果
#
#   mountain_CBI
#       = 山脉尺度文化分隔强度
#       = 综合所有可靠移动窗口 local_CBI、候选窗口比例、高 CBI 窗口比例、
#         社区分异连续段比例等指标
#       = 这是判断山脉是否具有文化分隔作用的主指标
#
# 注意：
#   n_contrast_segments = 0 不代表 mountain_CBI 为 0。
#   它只代表没有识别出满足连续合并条件的“社区分异连续段”。
# ============================================================

import sys
import json
import importlib.util
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString


# ------------------------------------------------------------
# 1. 加载项目根目录与 config.py
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config


# ------------------------------------------------------------
# 2. 动态加载原来的 06 文件
# ------------------------------------------------------------

def load_barrier06_module():
    possible_paths = [
        BASE_DIR / "scripts" / "06_barrier_index_by_communities.py",
        BASE_DIR / "06_barrier_index_by_communities.py",
    ]

    script_path = None

    for p in possible_paths:
        if p.exists():
            script_path = p
            break

    if script_path is None:
        raise FileNotFoundError(
            "没有找到 06_barrier_index_by_communities.py。"
            "请确认它位于 scripts/ 目录或项目根目录。"
        )

    spec = importlib.util.spec_from_file_location("barrier06", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


barrier06 = load_barrier06_module()


# ------------------------------------------------------------
# 3. 从 config.py 读取参数
# ------------------------------------------------------------

CHAR_POINTS_COMMUNITY_GPKG = config.CHAR_POINTS_COMMUNITY_GPKG
MOUNTAIN_SHP = config.MOUNTAIN_SHP
MOUNTAIN_NAMES = config.MOUNTAIN_NAMES
ALBERS_CHINA = config.ALBERS_CHINA

LOCAL_WINDOW_STEP_KM = getattr(config, "LOCAL_WINDOW_STEP_KM", 20)
LOCAL_WINDOW_LENGTH_KM = getattr(config, "LOCAL_WINDOW_LENGTH_KM", 100)
LOCAL_SIDE_WIDTHS_KM = getattr(config, "LOCAL_SIDE_WIDTHS_KM", [50])

# 长山脉如果只用 50 km 侧宽，容易因为某一侧点数不足而把局部强差异误判为“无可靠窗口”。
# 因此 06b 默认增加一组自适应侧宽候选；所有候选窗口都会写入窗口表，
# 山脉尺度主结果再为每条山脉选择一个最适合论文解释的主判读侧宽。
LOCAL_ENABLE_ADAPTIVE_SIDE_WIDTHS = getattr(
    config,
    "LOCAL_ENABLE_ADAPTIVE_SIDE_WIDTHS",
    True
)

LOCAL_ADAPTIVE_SIDE_WIDTHS_KM = getattr(
    config,
    "LOCAL_ADAPTIVE_SIDE_WIDTHS_KM",
    [50, 100, 150, 200]
)

LOCAL_PRIMARY_MIN_RELIABLE_WINDOWS = getattr(
    config,
    "LOCAL_PRIMARY_MIN_RELIABLE_WINDOWS",
    3
)

LOCAL_PRIMARY_MIN_RELIABLE_WINDOW_RATIO = getattr(
    config,
    "LOCAL_PRIMARY_MIN_RELIABLE_WINDOW_RATIO",
    0.10
)

LOCAL_PRIMARY_MIN_RELIABLE_COVERAGE_RATIO = getattr(
    config,
    "LOCAL_PRIMARY_MIN_RELIABLE_COVERAGE_RATIO",
    0.30
)

LOCAL_SIDE_WIDTH_SELECTION_SCORE_TOLERANCE = getattr(
    config,
    "LOCAL_SIDE_WIDTH_SELECTION_SCORE_TOLERANCE",
    0.03
)

LOCAL_USE_ALL_RAW_MOUNTAINS = getattr(
    config,
    "LOCAL_USE_ALL_RAW_MOUNTAINS",
    True
)

# 全量 raw 山脉计算耗时较长，采用断点续算和增量落盘，避免中途终止后结果回退。
LOCAL_RESUME_FROM_EXISTING = getattr(
    config,
    "LOCAL_RESUME_FROM_EXISTING",
    True
)

LOCAL_CHECKPOINT_EVERY_N = getattr(
    config,
    "LOCAL_CHECKPOINT_EVERY_N",
    1
)

LOCAL_MIN_POINTS_EACH_SIDE = getattr(config, "LOCAL_MIN_POINTS_EACH_SIDE", 30)
LOCAL_DOMINANT_SHARE_MIN = getattr(config, "LOCAL_DOMINANT_SHARE_MIN", 0.20)
LOCAL_VALID_MIN_CBI_LEVEL = getattr(config, "LOCAL_VALID_MIN_CBI_LEVEL", 3)
LOCAL_MIN_CONSECUTIVE_WINDOWS = getattr(config, "LOCAL_MIN_CONSECUTIVE_WINDOWS", 2)
LOCAL_MIN_SEGMENT_LENGTH_KM = getattr(config, "LOCAL_MIN_SEGMENT_LENGTH_KM", 40)
LOCAL_TOP3_JACCARD_MIN = getattr(config, "LOCAL_TOP3_JACCARD_MIN", 0.2)

LOCAL_EFFECTIVE_CLIP_OFFSET_M = getattr(
    config,
    "LOCAL_EFFECTIVE_CLIP_OFFSET_M",
    1000
)

LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO = getattr(
    config,
    "LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO",
    0.10
)

TABLE_DIR = config.TABLE_DIR
TABLE_06B_DIR = getattr(
    config,
    "TABLE_06B_DIR",
    TABLE_DIR / "06b_mountain_moving_window_cbi"
)

LOCAL_CBI_WINDOWS_CSV = getattr(
    config,
    "LOCAL_CBI_WINDOWS_CSV",
    TABLE_06B_DIR / "mountain_local_cbi_windows.csv"
)

COMMUNITY_DIFF_SEGMENTS_CSV = getattr(
    config,
    "COMMUNITY_DIFF_SEGMENTS_CSV",
    TABLE_06B_DIR / "mountain_community_differentiation_segments.csv"
)

MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV = getattr(
    config,
    "MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV",
    TABLE_06B_DIR / "mountain_cultural_boundary_strength.csv"
)

MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV = getattr(
    config,
    "MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV",
    TABLE_06B_DIR / "mountain_side_width_summary.csv"
)

MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV = getattr(
    config,
    "MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV",
    TABLE_06B_DIR / "mountain_system_cultural_boundary_strength.csv"
)

# 复合山系映射。单条山脉线仍按 mountain_CBI 评价；
# 横断山这类复合山系另按子山脉可靠证据长度加权汇总。
MOUNTAIN_SYSTEM_GROUPS = getattr(
    config,
    "MOUNTAIN_SYSTEM_GROUPS",
    {
        "横断山系": [
            "高黎贡山",
            "怒山",
            "云岭",
            "沙鲁里山",
            "大雪山",
            "邛崃山",
            "岷山",
            "无量山",
            "哀牢山",
        ]
    }
)

MOUNTAIN_CBI_RUN_METADATA_JSON = getattr(
    config,
    "MOUNTAIN_CBI_RUN_METADATA_JSON",
    TABLE_06B_DIR / "mountain_cbi_run_metadata.json"
)

# 兼容旧配置变量。
# 注意：这些变量只作为旧路径别名使用，不改变本文的新概念命名。
LOCAL_CBI_SEGMENTS_CSV = getattr(config, "LOCAL_CBI_SEGMENTS_CSV", None)
LOCAL_CBI_MOUNTAIN_SUMMARY_CSV = getattr(config, "LOCAL_CBI_MOUNTAIN_SUMMARY_CSV", None)


LOCAL_CBI_WINDOW_CORE_COLUMNS = [
    "boundary_name",
    "boundary_type",
    "side_width_km",
    "window_id",
    "center_station_km",
    "start_station_km",
    "end_station_km",
    "window_length_km",
    "mountain_length_km",
    "n_points_in_max_side_width",
    "point_prefilter_ratio",

    "n_left",
    "n_right",
    "min_side_points",
    "total_side_points",
    "sample_balance",
    "point_reliability_ratio",
    "CBI",
    "small_CBI",
    "big_CBI",

    "top_A",
    "top_B",
    "top_A_share",
    "top_B_share",
    "top3_A",
    "top3_B",

    "reliable_window",
    "dominant_different",
    "dominance_ok",

    "CBI_level_no",
    "CBI_level",
    "CBI_level_method",
    "CBI_quantile_level_no",
    "CBI_quantile_level",
    "CBI_quantile_breaks",
    "CBI_natural_level_no",
    "CBI_natural_level",
    "CBI_natural_breaks",
    "CBI_level_agreement",
    "clip_membership_ok",
    "valid_contrast_window",
    "distribution_contrast_window",
    "local_CBI_hotspot_window",

    "window_membership_change_ratio",
    "added_by_clip_ratio",
    "removed_by_clip_ratio",
    "clip_risk_level",
    "station_reference_quality",
]


COMMUNITY_DIFF_SEGMENT_CORE_COLUMNS = [
    "contrast_segment_id",
    "boundary_name",
    "boundary_type",
    "side_width_km",
    "start_station_km",
    "end_station_km",
    "contrast_segment_length_km",
    "n_windows",

    "segment_local_CBI_mean",
    "segment_local_CBI_max",
    "segment_local_CBI_min",
    "segment_small_CBI_mean",
    "segment_big_CBI_mean",

    "mean_top_A_share",
    "mean_top_B_share",
    "dominant_A_mode",
    "dominant_B_mode",
    "window_ids",
    "mountain_length_km",

    "mean_window_membership_change_ratio",
    "max_window_membership_change_ratio",
    "mean_added_by_clip_ratio",
    "max_added_by_clip_ratio",
    "mean_removed_by_clip_ratio",
    "max_removed_by_clip_ratio",
]


MOUNTAIN_STRENGTH_CORE_COLUMNS = [
    "boundary_name",
    "boundary_type",
    "primary_side_width_km",
    "side_width_selection_score",
    "side_width_selection_reason",
    "side_widths_tested",
    "mountain_length_km",

    "n_local_windows",
    "n_reliable_windows",
    "n_candidate_windows",
    "n_high_CBI_windows",
    "n_valid_contrast_windows",
    "n_contrast_segments",

    "reliable_window_ratio",
    "clip_stable_reliable_window_ratio",
    "reliable_coverage_ratio",
    "candidate_coverage_ratio",
    "high_CBI_coverage_ratio",
    "valid_contrast_coverage_ratio",

    "mean_local_CBI",
    "mean_reliable_local_CBI",
    "max_reliable_local_CBI",
    "p75_reliable_local_CBI",
    "p90_reliable_local_CBI",

    "mean_valid_contrast_local_CBI",
    "max_valid_contrast_local_CBI",

    "side_width_local_signal_score",
    "side_width_local_signal_level",

    "candidate_window_ratio",
    "high_CBI_window_ratio",
    "valid_contrast_window_ratio",

    "contrast_segment_union_length_km",
    "contrast_segment_ratio",
    "mean_contrast_segment_local_CBI",
    "max_contrast_segment_local_CBI",
    "longest_contrast_segment_km",

    "mean_window_membership_change_ratio",
    "max_window_membership_change_ratio",
    "clip_risk_level",
    "station_reference_quality",

    "mountain_CBI",
    "mountain_CBI_level",
    "mountain_CBI_level_method",
    "mountain_CBI_natural_level",
    "mountain_CBI_natural_level_no",
    "mountain_CBI_natural_breaks",
    "mountain_CBI_fixed_level",
    "mountain_CBI_rank",
    "mountain_CBI_confidence",
    "evidence_quality",

    "result_interpretation",
    "segment_interpretation",
    "clip_interpretation",
    "parameter_advice",
]


MOUNTAIN_SYSTEM_STRENGTH_CORE_COLUMNS = [
    "mountain_system_name",
    "system_type",
    "n_sub_mountains_configured",
    "n_sub_mountains_found",
    "sub_mountains_configured",
    "sub_mountains_found",
    "sub_mountains_missing",
    "total_sub_mountain_length_km",
    "evidence_weight_sum",
    "mountain_system_CBI",
    "mountain_system_rank",
    "weighted_local_signal_CBI",
    "system_reliable_coverage_ratio",
    "system_high_CBI_coverage_ratio",
    "system_contrast_segment_ratio",
    "max_sub_mountain_CBI",
    "max_local_signal_CBI",
    "strong_sub_mountain_ratio",
    "mean_mountain_CBI_confidence",
    "system_evidence_quality",
    "system_interpretation",
]


MOUNTAIN_SIDE_WIDTH_CORE_COLUMNS = [
    "boundary_name",
    "boundary_type",
    "side_width_km",
    "selected_primary_width",
    "selection_eligible",
    "side_width_selection_score",
    "side_width_selection_reason",
    "mountain_length_km",

    "n_local_windows",
    "n_reliable_windows",
    "n_candidate_windows",
    "n_high_CBI_windows",
    "n_valid_contrast_windows",
    "n_contrast_segments",

    "reliable_window_ratio",
    "candidate_window_ratio",
    "high_CBI_window_ratio",
    "valid_contrast_window_ratio",
    "clip_stable_reliable_window_ratio",
    "reliable_coverage_ratio",
    "candidate_coverage_ratio",
    "high_CBI_coverage_ratio",
    "valid_contrast_coverage_ratio",

    "mean_reliable_local_CBI",
    "p75_reliable_local_CBI",
    "p90_reliable_local_CBI",
    "max_reliable_local_CBI",
    "local_signal_CBI",
    "local_signal_level",

    "contrast_segment_ratio",
    "mean_window_membership_change_ratio",
    "max_window_membership_change_ratio",
    "clip_risk_level",
    "station_reference_quality",
]


# ------------------------------------------------------------
# 4. 工具函数
# ------------------------------------------------------------

def log(msg):
    print(f"[06b_moving_window_cbi] {msg}")


def parse_top3(value):
    if pd.isna(value):
        return set()

    text = str(value).strip()

    if text == "":
        return set()

    return set(text.split("|"))


def jaccard(a, b):
    a = set(a)
    b = set(b)

    if len(a) == 0 and len(b) == 0:
        return 0.0

    union = a | b
    inter = a & b

    if len(union) == 0:
        return 0.0

    return len(inter) / len(union)


def get_mode(series):
    if len(series) == 0:
        return None

    vc = series.astype(str).value_counts()

    if len(vc) == 0:
        return None

    return vc.index[0]


def safe_mean(df, col):
    if len(df) == 0 or col not in df.columns:
        return np.nan
    return pd.to_numeric(df[col], errors="coerce").mean()


def safe_max(df, col):
    if len(df) == 0 or col not in df.columns:
        return np.nan
    return pd.to_numeric(df[col], errors="coerce").max()


def safe_quantile(df, col, q):
    if len(df) == 0 or col not in df.columns:
        return np.nan
    return pd.to_numeric(df[col], errors="coerce").quantile(q)


def safe_ratio(numerator, denominator):
    if denominator is None or denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def normalize_series(values):
    """
    用最大值归一化，保留相对强弱。
    如果全为空或最大值为 0，则返回 0，避免把无数据误解释为强信号。
    """
    s = pd.to_numeric(values, errors="coerce").fillna(0.0)
    max_value = s.max()

    if max_value > 0:
        return s / max_value

    return pd.Series(0.0, index=s.index)


def get_side_widths_to_run():
    """
    返回本次移动窗口要测试的侧宽。
    LOCAL_SIDE_WIDTHS_KM 是原始主参数；自适应侧宽用于解决长山脉、
    点密度低或山体宽度大时 50 km 单一侧宽过窄的问题。
    """
    widths = list(LOCAL_SIDE_WIDTHS_KM)

    if LOCAL_ENABLE_ADAPTIVE_SIDE_WIDTHS:
        widths.extend(list(LOCAL_ADAPTIVE_SIDE_WIDTHS_KM))

    clean_widths = []

    for width in widths:
        try:
            value = float(width)
        except (TypeError, ValueError):
            continue

        if value <= 0:
            continue

        if value.is_integer():
            value = int(value)

        clean_widths.append(value)

    return sorted(set(clean_widths))


def interval_union_length_km(starts, ends):
    """
    计算多个区间的并集长度，避免重叠 segment 被重复计入长度占比。
    """

    intervals = []

    for s, e in zip(starts, ends):
        if pd.isna(s) or pd.isna(e):
            continue

        s = float(s)
        e = float(e)

        if e <= s:
            continue

        intervals.append((s, e))

    if len(intervals) == 0:
        return 0.0

    intervals = sorted(intervals, key=lambda x: x[0])

    merged = []

    cur_s, cur_e = intervals[0]

    for s, e in intervals[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e

    merged.append((cur_s, cur_e))

    return sum(e - s for s, e in merged)


def window_coverage_km(window_df):
    """
    计算一组移动窗口覆盖的山脉里程并集长度。
    由于移动窗口高度重叠，论文解释中优先使用覆盖长度比例，
    不直接把窗口数量比例当成独立样本比例。
    """
    if window_df is None or len(window_df) == 0:
        return 0.0

    if "start_station_km" not in window_df.columns:
        return 0.0

    if "end_station_km" not in window_df.columns:
        return 0.0

    return interval_union_length_km(
        window_df["start_station_km"],
        window_df["end_station_km"]
    )


def coverage_ratio_from_windows(window_df, mountain_length_km):
    length_km = window_coverage_km(window_df)
    ratio = safe_ratio(length_km, mountain_length_km)
    ratio = max(0.0, min(1.0, ratio))

    return length_km, ratio


def classify_clip_risk(mean_change, max_change):
    """
    根据窗口集合变化比例给出 clip 风险等级。
    这个等级不直接决定 mountain_CBI，而是用于证据质量解释。
    """
    mean_change = float(mean_change or 0)
    max_change = float(max_change or 0)

    if max_change <= LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO:
        return "低"

    if mean_change <= LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO and max_change <= 0.50:
        return "中"

    if mean_change <= 0.25:
        return "偏高"

    return "高"


def classify_station_reference_quality(mean_change, max_change):
    """
    给 station_m 线性参考质量一个可读标签。
    标签用于提示是否需要检查山脉线 geometry、multipart 顺序和最近线段投影。
    """
    clip_risk = classify_clip_risk(mean_change, max_change)

    if clip_risk == "低":
        return "稳定"

    if clip_risk == "中":
        return "基本可用"

    if clip_risk == "偏高":
        return "需复核"

    return "高风险"


def cbi_level_from_score(x):
    """
    固定阈值等级仅作辅助参考，不再作为 mountain_CBI 的主展示等级。
    """
    if x >= 0.75:
        return "强"
    if x >= 0.50:
        return "较强"
    if x >= 0.25:
        return "中等"
    return "弱"


def cbi_level_names(k):
    """
    根据实际可分等级数返回等级名称。
    分位数和自然断点共用这套中文标签，便于横向对照。
    """
    level_names_4 = {
        1: "很弱",
        2: "弱",
        3: "较强",
        4: "强",
    }

    level_names_3 = {
        1: "弱",
        2: "较强",
        3: "强",
    }

    level_names_2 = {
        1: "弱",
        2: "强",
    }

    if k >= 4:
        return level_names_4
    if k == 3:
        return level_names_3
    if k == 2:
        return level_names_2
    return {1: "单一等级"}


def format_breaks_for_output(breaks):
    if breaks is None or len(breaks) == 0:
        return ""
    return "|".join(f"{float(x):.6f}" for x in breaks if pd.notna(x))


def jenks_natural_breaks(values, max_classes=4):
    """
    使用 Jenks natural breaks 计算自然断点。

    说明：
    1. 不调用 mapclassify.NaturalBreaks，避免部分 Windows / Anaconda GIS 环境
       因 sklearn / 原生库触发不可捕获崩溃。
    2. 自然断点只用于等级展示和敏感性对照，不改变 local_CBI / mountain_CBI 数值。
    """
    vals = pd.Series(values).dropna().astype(float)
    vals = vals[np.isfinite(vals)].sort_values().to_numpy()

    if len(vals) == 0:
        return []

    unique_vals = np.unique(vals)
    k = int(min(max_classes, len(unique_vals), len(vals)))

    if k <= 1:
        return [float(vals[0]), float(vals[-1])]

    n = len(vals)
    lower = np.zeros((n + 1, k + 1), dtype=int)
    var = np.full((n + 1, k + 1), np.inf, dtype=float)

    for i in range(1, k + 1):
        lower[1, i] = 1
        var[1, i] = 0.0

    for l in range(2, n + 1):
        s1 = 0.0
        s2 = 0.0
        w = 0.0
        current_var = 0.0

        for m in range(1, l + 1):
            i3 = l - m + 1
            val = vals[i3 - 1]
            s1 += val
            s2 += val * val
            w += 1.0
            current_var = s2 - (s1 * s1) / w
            i4 = i3 - 1

            if i4 == 0:
                continue

            for j in range(2, k + 1):
                candidate_var = current_var + var[i4, j - 1]
                if var[l, j] >= candidate_var:
                    lower[l, j] = i3
                    var[l, j] = candidate_var

        lower[l, 1] = 1
        var[l, 1] = current_var

    breaks = [0.0] * (k + 1)
    breaks[0] = float(vals[0])
    breaks[k] = float(vals[-1])

    count_num = k
    idx = n
    while count_num >= 2:
        split_idx = int(lower[idx, count_num] - 2)
        split_idx = max(0, min(split_idx, n - 1))
        breaks[count_num - 1] = float(vals[split_idx])
        idx = int(lower[idx, count_num] - 1)
        count_num -= 1

    return breaks


def assign_level_by_upper_breaks(value, upper_breaks, k):
    if pd.isna(value) or upper_breaks is None or len(upper_breaks) == 0:
        return 0
    level_no = int(np.searchsorted(upper_breaks, float(value), side="right") + 1)
    return max(1, min(level_no, int(k)))


def filter_points_near_boundary(point_gdf, segment_gdf, max_side_width_m):
    """
    先用最大侧宽 buffer 过滤候选地名点，再进行最近线段匹配。
    这样可以避免全国远距离地名点参与 nearest 诊断，减少 clip 诊断污染。
    """
    if len(point_gdf) == 0 or len(segment_gdf) == 0:
        return point_gdf.copy()

    buffer_series = segment_gdf.geometry.buffer(max_side_width_m)

    try:
        buffer_geom = buffer_series.union_all()
    except AttributeError:
        buffer_geom = buffer_series.unary_union

    try:
        candidate_idx = point_gdf.sindex.query(
            buffer_geom,
            predicate="intersects"
        )
        candidate = point_gdf.iloc[candidate_idx].copy()
    except Exception:
        candidate = point_gdf[point_gdf.geometry.intersects(buffer_geom)].copy()

    return candidate


def write_run_metadata(mountain_strength_df, side_width_summary_df):
    """
    输出运行元数据，保证论文结果可复现。
    """
    MOUNTAIN_CBI_RUN_METADATA_JSON.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "script": "scripts/06b_mountain_moving_window_cbi.py",
        "run_time": datetime.now().isoformat(timespec="seconds"),
        "input_files": {
            "CHAR_POINTS_COMMUNITY_GPKG": str(CHAR_POINTS_COMMUNITY_GPKG),
            "MOUNTAIN_SHP": str(MOUNTAIN_SHP),
        },
        "output_files": {
            "LOCAL_CBI_WINDOWS_CSV": str(LOCAL_CBI_WINDOWS_CSV),
            "COMMUNITY_DIFF_SEGMENTS_CSV": str(COMMUNITY_DIFF_SEGMENTS_CSV),
            "MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV": str(
                MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV
            ),
            "MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV": str(MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV),
            "MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV": str(
                MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV
            ),
        },
        "parameters": {
            "LOCAL_WINDOW_STEP_KM": LOCAL_WINDOW_STEP_KM,
            "LOCAL_WINDOW_LENGTH_KM": LOCAL_WINDOW_LENGTH_KM,
            "LOCAL_SIDE_WIDTHS_KM": list(LOCAL_SIDE_WIDTHS_KM),
            "LOCAL_ENABLE_ADAPTIVE_SIDE_WIDTHS": LOCAL_ENABLE_ADAPTIVE_SIDE_WIDTHS,
            "LOCAL_ADAPTIVE_SIDE_WIDTHS_KM": list(LOCAL_ADAPTIVE_SIDE_WIDTHS_KM),
            "LOCAL_PRIMARY_MIN_RELIABLE_WINDOWS": LOCAL_PRIMARY_MIN_RELIABLE_WINDOWS,
            "LOCAL_PRIMARY_MIN_RELIABLE_WINDOW_RATIO": (
                LOCAL_PRIMARY_MIN_RELIABLE_WINDOW_RATIO
            ),
            "LOCAL_PRIMARY_MIN_RELIABLE_COVERAGE_RATIO": (
                LOCAL_PRIMARY_MIN_RELIABLE_COVERAGE_RATIO
            ),
            "LOCAL_MIN_POINTS_EACH_SIDE": LOCAL_MIN_POINTS_EACH_SIDE,
            "LOCAL_VALID_MIN_CBI_LEVEL": LOCAL_VALID_MIN_CBI_LEVEL,
            "LOCAL_MIN_CONSECUTIVE_WINDOWS": LOCAL_MIN_CONSECUTIVE_WINDOWS,
            "LOCAL_MIN_SEGMENT_LENGTH_KM": LOCAL_MIN_SEGMENT_LENGTH_KM,
            "LOCAL_TOP3_JACCARD_MIN": LOCAL_TOP3_JACCARD_MIN,
            "LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO": (
                LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO
            ),
        },
        "mountain_CBI_formula": (
            "0.30*mean_reliable_local_CBI_norm + "
            "0.25*p90_reliable_local_CBI_norm + "
            "0.20*high_CBI_coverage_ratio + "
            "0.10*candidate_coverage_ratio + "
            "0.10*contrast_segment_ratio + "
            "0.05*reliable_coverage_ratio"
        ),
        "local_signal_CBI_formula": (
            "0.45*mean_reliable_local_CBI_norm + "
            "0.35*p90_reliable_local_CBI_norm + "
            "0.10*high_CBI_window_ratio + "
            "0.10*candidate_window_ratio"
        ),
        "mountains": (
            mountain_strength_df[
                [
                    "boundary_name",
                    "primary_side_width_km",
                    "local_signal_CBI",
                    "local_signal_level",
                    "mountain_CBI",
                    "mountain_CBI_level",
                    "mountain_CBI_level_method",
                    "mountain_CBI_natural_level",
                    "mountain_CBI_fixed_level",
                    "mountain_CBI_rank",
                    "mountain_CBI_confidence",
                    "evidence_quality",
                ]
            ].to_dict(orient="records")
            if mountain_strength_df is not None and len(mountain_strength_df) > 0
            else []
        ),
        "side_width_rows": int(
            len(side_width_summary_df)
            if side_width_summary_df is not None else 0
        ),
    }

    with open(MOUNTAIN_CBI_RUN_METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    log("运行元数据已输出：")
    log(str(MOUNTAIN_CBI_RUN_METADATA_JSON))


def reorder_columns(df, core_columns):
    """
    将论文和检查最常用字段提前，其余诊断字段保留在后面。
    这样既不丢信息，也能让 CSV 首屏更容易读。
    """
    if df is None or len(df.columns) == 0:
        return df

    front = [col for col in core_columns if col in df.columns]
    rest = [col for col in df.columns if col not in front]

    return df[front + rest].copy()


def write_csv_with_legacy_alias(df, output_path, legacy_path=None, label="结果"):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    log(f"{label}已输出：")
    log(str(output_path))

    if legacy_path is None:
        return

    legacy_path = Path(legacy_path)

    if legacy_path == output_path:
        return

    legacy_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        legacy_path,
        index=False,
        encoding="utf-8-sig"
    )

    log(f"{label}已同步写出到旧路径兼容别名：")
    log(str(legacy_path))


def explain_clip(row):
    mean_change = float(row.get("mean_window_membership_change_ratio", 0) or 0)
    max_change = float(row.get("max_window_membership_change_ratio", 0) or 0)
    clip_risk = classify_clip_risk(mean_change, max_change)

    if max_change <= LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO:
        return (
            "mean_window_membership_change_ratio 和 "
            "max_window_membership_change_ratio 均在阈值内，"
            f"clip 对窗口选点影响较小，clip 风险为“{clip_risk}”。"
        )

    return (
        "局部窗口受 clip 影响偏大，建议检查山脉线 geometry 是否破碎、"
        "station_m 线性参考是否合理；放宽 "
        "LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO 更适合作为敏感性分析。"
        f"当前 clip 风险为“{clip_risk}”。"
    )


def explain_parameter_advice(row):
    n_local = int(row.get("n_local_windows", 0) or 0)
    n_reliable = int(row.get("n_reliable_windows", 0) or 0)
    max_change = float(row.get("max_window_membership_change_ratio", 0) or 0)
    reliable_coverage = float(row.get("reliable_coverage_ratio", 0) or 0)
    mountain_cbi = float(row.get("mountain_CBI", 0) or 0)

    if n_local > 0 and n_reliable == 0:
        return (
            "窗口内 A/B 两侧点数不足。建议增大 LOCAL_SIDE_WIDTHS_KM，"
            "例如从 [50] 做到 [100]；或降低 LOCAL_MIN_POINTS_EACH_SIDE；"
            "同时检查山脉线是否过短或位置不准。"
        )

    if mountain_cbi >= 0.50 and reliable_coverage < LOCAL_PRIMARY_MIN_RELIABLE_COVERAGE_RATIO:
        return (
            "已有较强 local_CBI 信号，但可靠覆盖长度不足。建议保留该结果作为"
            "强信号但覆盖不足的证据，同时增加侧宽敏感性分析或降低单侧点数阈值作对照。"
        )

    if max_change > LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO:
        return (
            "优先检查线数据与 station_m 构建；若确需放宽 clip 阈值，"
            "建议作为敏感性分析而不是直接替代正式参数。"
        )

    return "当前参数下已有可靠窗口，可优先解释 mountain_CBI、local_CBI 分布和连续段结果。"



def summarize_mountain_system_cultural_boundary_strength(mountain_strength_df):
    """
    汇总复合山系级 cultural boundary strength。

    适用对象：横断山系这类“多列山脉 + 河谷走廊”的复合山系。
    注意：该函数不改变单条山脉 mountain_CBI，只新增 mountain_system_CBI。
    """
    if mountain_strength_df is None or len(mountain_strength_df) == 0:
        return pd.DataFrame(columns=MOUNTAIN_SYSTEM_STRENGTH_CORE_COLUMNS)

    rows = []
    source = mountain_strength_df.copy()
    source["boundary_name"] = source["boundary_name"].astype(str)

    for system_name, sub_names in MOUNTAIN_SYSTEM_GROUPS.items():
        configured = [str(name) for name in sub_names]
        sub = source[source["boundary_name"].isin(configured)].copy()
        found = sub["boundary_name"].astype(str).tolist()
        missing = [name for name in configured if name not in set(found)]

        if len(sub) == 0:
            rows.append({
                "mountain_system_name": system_name,
                "system_type": "composite_mountain_system",
                "n_sub_mountains_configured": len(configured),
                "n_sub_mountains_found": 0,
                "sub_mountains_configured": "|".join(configured),
                "sub_mountains_found": "",
                "sub_mountains_missing": "|".join(missing),
                "system_evidence_quality": "无可用子山脉证据",
                "system_interpretation": (
                    f"{system_name} 未在当前 mountain_CBI 表中匹配到子山脉，"
                    "无法进行山系级综合评价。"
                ),
            })
            continue

        length = pd.to_numeric(
            sub.get("mountain_length_km", 0),
            errors="coerce"
        ).fillna(0.0)
        reliable = pd.to_numeric(
            sub.get("reliable_coverage_ratio", 0),
            errors="coerce"
        ).fillna(0.0).clip(lower=0.0)
        confidence = pd.to_numeric(
            sub.get("mountain_CBI_confidence", 0),
            errors="coerce"
        ).fillna(0.0).clip(lower=0.0)
        cbi = pd.to_numeric(
            sub.get("mountain_CBI", 0),
            errors="coerce"
        ).fillna(0.0)
        local_signal = pd.to_numeric(
            sub.get("local_signal_CBI", 0),
            errors="coerce"
        ).fillna(0.0)
        high_cover = pd.to_numeric(
            sub.get("high_CBI_coverage_ratio", 0),
            errors="coerce"
        ).fillna(0.0)
        contrast = pd.to_numeric(
            sub.get("contrast_segment_ratio", 0),
            errors="coerce"
        ).fillna(0.0)

        # 可靠证据长度权重：长度越长、可靠覆盖越充分、置信度越高，权重越大。
        evidence_weight = length * reliable * confidence
        weight_sum = float(evidence_weight.sum())
        total_length = float(length.sum())

        if weight_sum > 0:
            system_cbi = float((cbi * evidence_weight).sum() / weight_sum)
            weighted_local_signal = float(
                (local_signal * evidence_weight).sum() / weight_sum
            )
            system_contrast = float((contrast * evidence_weight).sum() / weight_sum)
        else:
            system_cbi = np.nan
            weighted_local_signal = np.nan
            system_contrast = np.nan

        if total_length > 0:
            system_reliable = float((reliable * length).sum() / total_length)
            system_high = float((high_cover * length).sum() / total_length)
        else:
            system_reliable = np.nan
            system_high = np.nan

        strong_mask = sub["mountain_CBI_natural_level"].astype(str).isin(["较强", "强"])
        strong_ratio = float(strong_mask.mean()) if len(sub) else np.nan
        mean_confidence = float(confidence.mean()) if len(sub) else np.nan

        if not np.isfinite(system_cbi):
            evidence_quality = "无可靠加权证据"
        elif system_reliable >= 0.60 and mean_confidence >= 0.75:
            evidence_quality = "山系级证据较可靠"
        elif system_reliable >= 0.35:
            evidence_quality = "山系级证据可用但需谨慎"
        else:
            evidence_quality = "山系级覆盖不足，需谨慎解释"

        interpretation = (
            f"{system_name}按复合山系处理，共配置 {len(configured)} 条子山脉，"
            f"当前匹配 {len(sub)} 条。mountain_system_CBI 采用"
            "子山脉长度×可靠覆盖×置信度加权，表示当前数据下山系尺度"
            "地名文化分隔证据；它不等同于单条“横断山”线的 mountain_CBI。"
        )

        rows.append({
            "mountain_system_name": system_name,
            "system_type": "composite_mountain_system",
            "n_sub_mountains_configured": len(configured),
            "n_sub_mountains_found": len(sub),
            "sub_mountains_configured": "|".join(configured),
            "sub_mountains_found": "|".join(found),
            "sub_mountains_missing": "|".join(missing),
            "total_sub_mountain_length_km": total_length,
            "evidence_weight_sum": weight_sum,
            "mountain_system_CBI": system_cbi,
            "weighted_local_signal_CBI": weighted_local_signal,
            "system_reliable_coverage_ratio": system_reliable,
            "system_high_CBI_coverage_ratio": system_high,
            "system_contrast_segment_ratio": system_contrast,
            "max_sub_mountain_CBI": float(cbi.max()) if len(cbi) else np.nan,
            "max_local_signal_CBI": float(local_signal.max()) if len(local_signal) else np.nan,
            "strong_sub_mountain_ratio": strong_ratio,
            "mean_mountain_CBI_confidence": mean_confidence,
            "system_evidence_quality": evidence_quality,
            "system_interpretation": interpretation,
        })

    out = pd.DataFrame(rows)
    if len(out) == 0:
        return pd.DataFrame(columns=MOUNTAIN_SYSTEM_STRENGTH_CORE_COLUMNS)

    out = out.sort_values(
        ["mountain_system_CBI", "weighted_local_signal_CBI"],
        ascending=[False, False],
        na_position="last"
    ).reset_index(drop=True)
    out["mountain_system_rank"] = range(1, len(out) + 1)
    return reorder_columns(out, MOUNTAIN_SYSTEM_STRENGTH_CORE_COLUMNS)


def add_mountain_interpretation(out):
    """
    根据 mountain_CBI 与连续段结果生成论文解释建议。
    这里不把 n_contrast_segments 作为判断山脉有无文化分隔作用的唯一依据。
    """
    if out is None or len(out) == 0:
        return out

    out = out.copy()

    result_texts = []
    segment_texts = []
    clip_texts = []
    parameter_texts = []

    for _, row in out.iterrows():
        name = row.get("boundary_name", "")
        n_local = int(row.get("n_local_windows", 0) or 0)
        n_reliable = int(row.get("n_reliable_windows", 0) or 0)
        n_segments = int(row.get("n_contrast_segments", 0) or 0)
        mountain_cbi = float(row.get("mountain_CBI", 0) or 0)
        mountain_level = row.get(
            "mountain_CBI_natural_level",
            row.get("mountain_CBI_level", "未评级")
        )
        mountain_rank = row.get("mountain_CBI_rank", "")
        fixed_level = row.get("mountain_CBI_fixed_level", "辅助未评级")
        local_signal = float(row.get("local_signal_CBI", 0) or 0)
        local_signal_level = row.get("local_signal_level", "未评级")
        primary_width = row.get("primary_side_width_km", row.get("side_width_km", ""))
        evidence = row.get("evidence_quality", "未标注")
        reliable_coverage = float(row.get("reliable_coverage_ratio", 0) or 0)
        high_coverage = float(row.get("high_CBI_coverage_ratio", 0) or 0)
        clip_risk = row.get("clip_risk_level", "未评级")

        if n_local <= 0:
            result_text = f"{name} 未形成有效移动窗口，需要先检查山脉线长度与窗口参数。"
        elif n_reliable <= 0:
            result_text = (
                f"{name} 已完成移动窗口检测，但主判读侧宽 {primary_width} km 下没有可靠窗口，"
                "不能把该结果解释为山脉尺度文化分隔强度弱；"
                "应优先调整侧宽、点数阈值或检查山脉线数据。"
            )
        else:
            result_text = (
                f"{name} 的主判读侧宽为 {primary_width} km，"
                f"mountain_CBI 为 {mountain_cbi:.4f}，"
                f"rank 为 {mountain_rank}，自然断点展示等级为“{mountain_level}”，"
                f"固定阈值辅助等级为“{fixed_level}”，证据质量为“{evidence}”，"
                f"local_signal_CBI 为 {local_signal:.4f}（{local_signal_level}），"
                f"可靠覆盖比例为 {reliable_coverage:.3f}，"
                f"高 local_CBI 覆盖比例为 {high_coverage:.3f}，"
                f"clip 风险为“{clip_risk}”。"
                "判断山脉文化分隔强度时，应以移动窗口 local_CBI 分布为主，"
                "优先结合 mean_reliable_local_CBI、p90_reliable_local_CBI、"
                "高 CBI 覆盖比例、候选分异覆盖比例和连续分异段结果。"
            )

        if n_segments > 0:
            segment_text = (
                f"{name} 识别出 {n_segments} 个地名文化社区分异连续段，"
                "说明局部区段存在连续的两侧地名文化社区结构差异，"
                "可作为山脉文化分隔效应的空间证据。"
            )
        elif n_reliable > 0:
            segment_text = (
                f"{name} 未识别出满足连续合并条件的社区分异连续段。"
                "这只说明局部连续分异现象尚未达到合并条件，"
                "仍应结合 mountain_CBI 和可靠窗口 local_CBI 分布解释。"
            )
        else:
            segment_text = (
                f"{name} 暂无可靠窗口，不能讨论社区分异连续段。"
            )

        result_texts.append(result_text)
        segment_texts.append(segment_text)
        clip_texts.append(explain_clip(row))
        parameter_texts.append(explain_parameter_advice(row))

    out["result_interpretation"] = result_texts
    out["segment_interpretation"] = segment_texts
    out["clip_interpretation"] = clip_texts
    out["parameter_advice"] = parameter_texts

    return out


def log_result_advice(mountain_strength_df):
    if mountain_strength_df is None or len(mountain_strength_df) == 0:
        log("山脉尺度汇总为空，无法给出结果解释建议。")
        return

    log("结果解释建议：")

    high_df = mountain_strength_df.sort_values(
        ["mountain_CBI", "mountain_CBI_rank"],
        ascending=[False, True]
    ).head(3)

    high_names = "、".join(high_df["boundary_name"].astype(str).tolist())
    log(f"  mountain_CBI 相对较高的山脉：{high_names}")

    segment_df = mountain_strength_df[
        mountain_strength_df["n_contrast_segments"] > 0
    ].copy()

    if len(segment_df) > 0:
        names = "、".join(segment_df["boundary_name"].astype(str).tolist())
        log(f"  已识别出地名文化社区分异连续段的山脉：{names}")
    else:
        log("  当前没有山脉识别出满足连续合并条件的社区分异连续段。")

    no_segment_but_signal = mountain_strength_df[
        (mountain_strength_df["n_contrast_segments"] == 0)
        & (mountain_strength_df["n_reliable_windows"] > 0)
        & (mountain_strength_df["mountain_CBI"] > 0)
    ].copy()

    if len(no_segment_but_signal) > 0:
        names = "、".join(
            no_segment_but_signal["boundary_name"].astype(str).tolist()
        )
        log(
            "  没有连续段但仍有山脉尺度文化分隔指示意义的山脉："
            f"{names}"
        )

    needs_param_check = mountain_strength_df[
        (mountain_strength_df["n_local_windows"] > 0)
        & (
            (mountain_strength_df["n_reliable_windows"] == 0)
            | (
                mountain_strength_df["max_window_membership_change_ratio"]
                > LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO
            )
        )
    ].copy()

    if len(needs_param_check) > 0:
        names = "、".join(needs_param_check["boundary_name"].astype(str).tolist())
        log(f"  建议优先检查参数或线数据的山脉：{names}")
    else:
        log("  当前汇总结果未显示必须立即调整参数的明显信号。")


# ------------------------------------------------------------
# 5. 把山脉线转成带 station_m 的小线段
# ------------------------------------------------------------

def boundary_to_station_segments(boundary_geom, crs):
    main_vec = barrier06.get_main_direction(boundary_geom)

    records = []
    station_m = 0.0
    part_id = 0

    for line in barrier06.iter_lines(boundary_geom):
        coords = list(line.coords)

        if len(coords) < 2:
            continue

        part_vec = np.array(
            [
                coords[-1][0] - coords[0][0],
                coords[-1][1] - coords[0][1],
            ],
            dtype=float
        )

        if np.dot(part_vec, main_vec) < 0:
            coords = list(reversed(coords))

        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]

            dx = x2 - x1
            dy = y2 - y1

            seg_len = float(np.hypot(dx, dy))

            if seg_len == 0:
                continue

            records.append(
                {
                    "seg_id": len(records),
                    "part_id": part_id,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "seg_len_m": seg_len,
                    "station_start_m": station_m,
                    "station_end_m": station_m + seg_len,
                    "station_mid_m": station_m + seg_len / 2,
                    "geometry": LineString([(x1, y1), (x2, y2)]),
                }
            )

            station_m += seg_len

        part_id += 1

    if len(records) == 0:
        raise ValueError("山脉线无法拆分为有效线段。")

    seg_gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=crs)

    return seg_gdf, station_m


# ------------------------------------------------------------
# 6. 将地名点匹配到最近山脉线段
# ------------------------------------------------------------

def attach_points_to_nearest_segments(point_gdf, segment_gdf):
    unique_points = (
        point_gdf[["source_id", "geometry"]]
        .drop_duplicates("source_id")
        .copy()
    )

    joined = gpd.sjoin_nearest(
        unique_points,
        segment_gdf,
        how="inner",
        distance_col="dist_m"
    )

    joined = (
        joined
        .sort_values(["source_id", "dist_m"])
        .drop_duplicates("source_id")
        .copy()
    )

    joined["px"] = joined.geometry.x
    joined["py"] = joined.geometry.y

    dx = joined["x2"] - joined["x1"]
    dy = joined["y2"] - joined["y1"]

    seg_len2 = dx * dx + dy * dy

    joined["raw_t"] = (
        (joined["px"] - joined["x1"]) * dx
        + (joined["py"] - joined["y1"]) * dy
    ) / seg_len2

    joined["projected_outside_segment"] = (
        (joined["raw_t"] < 0)
        | (joined["raw_t"] > 1)
    )

    joined["clip_direction"] = np.select(
        [
            joined["raw_t"] < 0,
            joined["raw_t"] > 1,
        ],
        [
            "before_start",
            "after_end",
        ],
        default="inside"
    )

    joined["t"] = joined["raw_t"].clip(lower=0, upper=1)

    joined["raw_station_m"] = (
        joined["station_start_m"]
        + joined["raw_t"] * joined["seg_len_m"]
    )

    joined["station_m"] = (
        joined["station_start_m"]
        + joined["t"] * joined["seg_len_m"]
    )

    joined["station_clip_offset_m"] = (
        joined["station_m"]
        - joined["raw_station_m"]
    )

    joined["station_clip_abs_offset_m"] = (
        joined["station_clip_offset_m"]
        .abs()
    )

    joined["effective_clip"] = (
        (joined["projected_outside_segment"] == True)
        & (joined["station_clip_abs_offset_m"] >= LOCAL_EFFECTIVE_CLIP_OFFSET_M)
    )

    joined["cross"] = (
        (joined["x2"] - joined["x1"]) * (joined["py"] - joined["y1"])
        - (joined["y2"] - joined["y1"]) * (joined["px"] - joined["x1"])
    )

    joined["side"] = np.where(joined["cross"] >= 0, "A", "B")

    keep_cols = [
        "source_id",
        "seg_id",
        "dist_m",
        "station_m",
        "side",

        "raw_t",
        "t",
        "projected_outside_segment",
        "clip_direction",
        "raw_station_m",
        "station_clip_offset_m",
        "station_clip_abs_offset_m",
        "effective_clip",
    ]

    return joined[keep_cols].copy()


# ------------------------------------------------------------
# 7. 统计窗口两侧主导 community_id
# ------------------------------------------------------------

def compute_side_profile(band_df, class_col="community_id"):
    out = {}

    unit = band_df.drop_duplicates(["source_id", "side", class_col]).copy()
    unit[class_col] = unit[class_col].astype(str)

    for side in ["A", "B"]:
        sub = unit[unit["side"] == side].copy()

        if len(sub) == 0:
            out[f"top_{side}"] = None
            out[f"top_{side}_share"] = 0.0
            out[f"top3_{side}"] = ""
            out[f"n_{side}_community_pairs"] = 0
            continue

        counts = sub[class_col].value_counts()
        total = counts.sum()

        top_id = counts.index[0]
        top_share = counts.iloc[0] / total if total > 0 else 0.0
        top3 = counts.head(3).index.astype(str).tolist()

        out[f"top_{side}"] = top_id
        out[f"top_{side}_share"] = float(top_share)
        out[f"top3_{side}"] = "|".join(top3)
        out[f"n_{side}_community_pairs"] = int(total)

    return out


def compute_clip_diagnostics(band_df):
    out = {
        "n_source_points": 0,

        "n_clipped_points": 0,
        "clip_point_ratio": 0.0,
        "n_clip_before_start": 0,
        "n_clip_after_end": 0,

        "n_effective_clipped_points": 0,
        "effective_clip_point_ratio": 0.0,

        "mean_station_clip_abs_offset_m": 0.0,
        "max_station_clip_abs_offset_m": 0.0,

        "mean_effective_clip_abs_offset_m": 0.0,
        "max_effective_clip_abs_offset_m": 0.0,

        "mean_raw_t": np.nan,
        "min_raw_t": np.nan,
        "max_raw_t": np.nan,
    }

    required_cols = [
        "source_id",
        "projected_outside_segment",
        "clip_direction",
        "station_clip_abs_offset_m",
        "raw_t",
    ]

    for col in required_cols:
        if col not in band_df.columns:
            return out

    unit = band_df.drop_duplicates("source_id").copy()

    n_total = len(unit)

    if n_total == 0:
        return out

    if "effective_clip" not in unit.columns:
        unit["effective_clip"] = (
            (unit["projected_outside_segment"] == True)
            & (unit["station_clip_abs_offset_m"] >= LOCAL_EFFECTIVE_CLIP_OFFSET_M)
        )

    clipped = unit[unit["projected_outside_segment"] == True].copy()
    effective_clipped = unit[unit["effective_clip"] == True].copy()

    n_clipped = len(clipped)
    n_effective_clipped = len(effective_clipped)

    out["n_source_points"] = int(n_total)

    out["n_clipped_points"] = int(n_clipped)
    out["clip_point_ratio"] = (
        float(n_clipped / n_total) if n_total > 0 else 0.0
    )

    out["n_effective_clipped_points"] = int(n_effective_clipped)
    out["effective_clip_point_ratio"] = (
        float(n_effective_clipped / n_total) if n_total > 0 else 0.0
    )

    out["n_clip_before_start"] = int(
        (unit["clip_direction"] == "before_start").sum()
    )

    out["n_clip_after_end"] = int(
        (unit["clip_direction"] == "after_end").sum()
    )

    if n_clipped > 0:
        out["mean_station_clip_abs_offset_m"] = float(
            clipped["station_clip_abs_offset_m"].mean()
        )
        out["max_station_clip_abs_offset_m"] = float(
            clipped["station_clip_abs_offset_m"].max()
        )

    if n_effective_clipped > 0:
        out["mean_effective_clip_abs_offset_m"] = float(
            effective_clipped["station_clip_abs_offset_m"].mean()
        )
        out["max_effective_clip_abs_offset_m"] = float(
            effective_clipped["station_clip_abs_offset_m"].max()
        )

    out["mean_raw_t"] = float(unit["raw_t"].mean())
    out["min_raw_t"] = float(unit["raw_t"].min())
    out["max_raw_t"] = float(unit["raw_t"].max())

    return out


def compute_window_membership_clip_diagnostics(
    nearest_info,
    sub_info,
    start_m,
    end_m,
    side_width_m
):
    out = {
        "n_station_window_points": 0,
        "n_raw_window_points": 0,
        "n_added_by_clip_to_window": 0,
        "n_removed_by_clip_from_window": 0,
        "window_membership_change_ratio": 0.0,
        "added_by_clip_ratio": 0.0,
        "removed_by_clip_ratio": 0.0,
        "mean_added_clip_abs_offset_m": 0.0,
        "max_added_clip_abs_offset_m": 0.0,
        "mean_removed_clip_abs_offset_m": 0.0,
        "max_removed_clip_abs_offset_m": 0.0,
    }

    required_cols = [
        "source_id",
        "station_m",
        "raw_station_m",
        "dist_m",
        "station_clip_abs_offset_m",
    ]

    for col in required_cols:
        if col not in nearest_info.columns:
            return out

    station_ids = set(
        sub_info["source_id"]
        .drop_duplicates()
        .astype(str)
        .tolist()
    )

    raw_sub_info = nearest_info[
        (nearest_info["raw_station_m"] >= start_m)
        & (nearest_info["raw_station_m"] <= end_m)
        & (nearest_info["dist_m"] <= side_width_m)
    ].copy()

    raw_ids = set(
        raw_sub_info["source_id"]
        .drop_duplicates()
        .astype(str)
        .tolist()
    )

    added_ids = station_ids - raw_ids
    removed_ids = raw_ids - station_ids
    union_ids = station_ids | raw_ids

    n_station = len(station_ids)
    n_raw = len(raw_ids)
    n_added = len(added_ids)
    n_removed = len(removed_ids)
    n_union = len(union_ids)

    out["n_station_window_points"] = int(n_station)
    out["n_raw_window_points"] = int(n_raw)
    out["n_added_by_clip_to_window"] = int(n_added)
    out["n_removed_by_clip_from_window"] = int(n_removed)

    out["window_membership_change_ratio"] = (
        float((n_added + n_removed) / n_union)
        if n_union > 0 else 0.0
    )

    out["added_by_clip_ratio"] = (
        float(n_added / n_station)
        if n_station > 0 else 0.0
    )

    out["removed_by_clip_ratio"] = (
        float(n_removed / n_raw)
        if n_raw > 0 else 0.0
    )

    if n_added > 0:
        added_df = sub_info[
            sub_info["source_id"].astype(str).isin(added_ids)
        ].drop_duplicates("source_id").copy()

        if len(added_df) > 0:
            out["mean_added_clip_abs_offset_m"] = float(
                added_df["station_clip_abs_offset_m"].mean()
            )
            out["max_added_clip_abs_offset_m"] = float(
                added_df["station_clip_abs_offset_m"].max()
            )

    if n_removed > 0:
        removed_df = raw_sub_info[
            raw_sub_info["source_id"].astype(str).isin(removed_ids)
        ].drop_duplicates("source_id").copy()

        if len(removed_df) > 0:
            out["mean_removed_clip_abs_offset_m"] = float(
                removed_df["station_clip_abs_offset_m"].mean()
            )
            out["max_removed_clip_abs_offset_m"] = float(
                removed_df["station_clip_abs_offset_m"].max()
            )

    return out


# ------------------------------------------------------------
# 8. 计算某条山脉的所有移动窗口 local_CBI
# ------------------------------------------------------------

def evaluate_mountain_local_windows(point_gdf, mountain_gdf, boundary_name, name_col):
    log(f"开始计算山脉移动窗口：{boundary_name}")

    boundary_geom = barrier06.get_boundary_geom(
        mountain_gdf,
        boundary_name,
        name_col
    )

    segment_gdf, total_length_m = boundary_to_station_segments(
        boundary_geom,
        mountain_gdf.crs
    )

    total_length_km = total_length_m / 1000

    log(f"  山脉长度约：{total_length_km:.2f} km")
    log(f"  线段数量：{len(segment_gdf)}")

    side_widths_to_run = get_side_widths_to_run()
    max_side_width_m = max(side_widths_to_run) * 1000

    candidate_point_gdf = filter_points_near_boundary(
        point_gdf,
        segment_gdf,
        max_side_width_m
    )

    point_prefilter_ratio = safe_ratio(len(candidate_point_gdf), len(point_gdf))

    log(f"  本次测试侧宽：{side_widths_to_run} km")
    log(
        f"  最大侧宽候选点：{len(candidate_point_gdf)} / {len(point_gdf)} "
        f"({point_prefilter_ratio:.4f})"
    )

    if len(candidate_point_gdf) == 0:
        log("  最大侧宽范围内没有候选地名点，跳过该山脉。")
        return pd.DataFrame()

    nearest_info = attach_points_to_nearest_segments(
        candidate_point_gdf,
        segment_gdf
    )

    if len(nearest_info) > 0:
        n_total_nearest = len(nearest_info)
        n_total_clipped = int(nearest_info["projected_outside_segment"].sum())
        n_total_effective_clipped = int(nearest_info["effective_clip"].sum())

        clip_ratio = (
            n_total_clipped / n_total_nearest
            if n_total_nearest > 0 else 0.0
        )

        effective_clip_ratio = (
            n_total_effective_clipped / n_total_nearest
            if n_total_nearest > 0 else 0.0
        )

        log(
            f"  投影诊断：总点数 {n_total_nearest}，"
            f"原始 clip 点数 {n_total_clipped}，"
            f"原始比例 {clip_ratio:.4f}；"
            f"有效 clip 点数 {n_total_effective_clipped}，"
            f"有效比例 {effective_clip_ratio:.4f}"
        )

    step_m = LOCAL_WINDOW_STEP_KM * 1000
    half_window_m = LOCAL_WINDOW_LENGTH_KM * 1000 / 2

    centers = np.arange(0, total_length_m + step_m, step_m)

    rows = []

    for side_width_km in side_widths_to_run:
        side_width_m = side_width_km * 1000

        for window_id, center_m in enumerate(centers):
            start_m = max(0, center_m - half_window_m)
            end_m = min(total_length_m, center_m + half_window_m)

            sub_info = nearest_info[
                (nearest_info["station_m"] >= start_m)
                & (nearest_info["station_m"] <= end_m)
                & (nearest_info["dist_m"] <= side_width_m)
            ].copy()

            if len(sub_info) == 0:
                continue

            membership_clip_diag = compute_window_membership_clip_diagnostics(
                nearest_info=nearest_info,
                sub_info=sub_info,
                start_m=start_m,
                end_m=end_m,
                side_width_m=side_width_m
            )

            side_info = sub_info[
                [
                    "source_id",
                    "side",
                    "dist_m",
                    "station_m",

                    "raw_t",
                    "t",
                    "projected_outside_segment",
                    "clip_direction",
                    "raw_station_m",
                    "station_clip_offset_m",
                    "station_clip_abs_offset_m",
                    "effective_clip",
                ]
            ].copy()

            band = candidate_point_gdf.merge(
                side_info,
                on="source_id",
                how="inner"
            )

            if len(band) == 0:
                continue

            metrics = barrier06.compute_metrics(band)

            if metrics is None:
                continue

            profile = compute_side_profile(band, class_col="community_id")
            clip_diag = compute_clip_diagnostics(band)

            row = {}
            row.update(metrics)
            row.update(profile)
            row.update(clip_diag)
            row.update(membership_clip_diag)

            row["boundary_name"] = boundary_name
            row["boundary_type"] = "mountain"
            row["side_width_km"] = side_width_km
            row["window_id"] = window_id
            row["center_station_km"] = center_m / 1000
            row["start_station_km"] = start_m / 1000
            row["end_station_km"] = end_m / 1000
            row["window_length_km"] = (end_m - start_m) / 1000
            row["mountain_length_km"] = total_length_km
            row["n_points_in_max_side_width"] = len(candidate_point_gdf)
            row["point_prefilter_ratio"] = point_prefilter_ratio

            n_left = int(row["n_left"])
            n_right = int(row["n_right"])
            min_side_points = min(n_left, n_right)
            total_side_points = n_left + n_right

            row["min_side_points"] = min_side_points
            row["total_side_points"] = total_side_points
            row["sample_balance"] = (
                2 * min_side_points / total_side_points
                if total_side_points > 0 else 0.0
            )
            row["point_reliability_ratio"] = min(
                1.0,
                min_side_points / LOCAL_MIN_POINTS_EACH_SIDE
            )

            row["reliable_window"] = (
                n_left >= LOCAL_MIN_POINTS_EACH_SIDE
                and n_right >= LOCAL_MIN_POINTS_EACH_SIDE
            )

            row["dominant_different"] = (
                row["top_A"] is not None
                and row["top_B"] is not None
                and str(row["top_A"]) != str(row["top_B"])
            )

            row["dominance_ok"] = (
                row["top_A_share"] >= LOCAL_DOMINANT_SHARE_MIN
                and row["top_B_share"] >= LOCAL_DOMINANT_SHARE_MIN
            )

            rows.append(row)

    out_df = pd.DataFrame(rows)

    log(f"  输出窗口数量：{len(out_df)}")

    return out_df


# ------------------------------------------------------------
# 9. 对 local_CBI 做分级，并识别有效社区分异窗口
# ------------------------------------------------------------

def add_local_cbi_levels(window_df):
    df = window_df.copy()

    # CBI_level / CBI_level_no 保持为“分位数稳定基准”的兼容字段。
    # 自然断点结果另写入 CBI_natural_*，用于敏感性对照。
    df["CBI_level_no"] = 0
    df["CBI_level"] = "未评级"
    df["CBI_level_method"] = "quantile_stable_baseline"
    df["CBI_quantile_level_no"] = 0
    df["CBI_quantile_level"] = "未评级"
    df["CBI_quantile_breaks"] = ""
    df["CBI_natural_level_no"] = 0
    df["CBI_natural_level"] = "未评级"
    df["CBI_natural_breaks"] = ""
    df["CBI_level_agreement"] = False
    df["valid_contrast_window"] = False
    df["distribution_contrast_window"] = False
    df["local_CBI_hotspot_window"] = False

    if len(df) == 0:
        log("窗口结果为空，无法进行 CBI 分级。")
        return df

    if "reliable_window" not in df.columns:
        log("缺少 reliable_window 字段，无法进行 CBI 分级。")
        return df

    if "CBI" not in df.columns:
        log("缺少 CBI 字段，无法进行 CBI 分级。")
        return df

    if "dominant_different" not in df.columns:
        df["dominant_different"] = False

    if "dominance_ok" not in df.columns:
        df["dominance_ok"] = False

    if "window_membership_change_ratio" not in df.columns:
        df["window_membership_change_ratio"] = 0.0

    df["window_membership_change_ratio"] = pd.to_numeric(
        df["window_membership_change_ratio"],
        errors="coerce"
    ).fillna(0.0)

    df["clip_membership_ok"] = (
        df["window_membership_change_ratio"]
        <= LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO
    )

    df["clip_risk_level"] = df.apply(
        lambda row: classify_clip_risk(
            row.get("window_membership_change_ratio", 0),
            row.get("window_membership_change_ratio", 0)
        ),
        axis=1
    )

    df["station_reference_quality"] = df.apply(
        lambda row: classify_station_reference_quality(
            row.get("window_membership_change_ratio", 0),
            row.get("window_membership_change_ratio", 0)
        ),
        axis=1
    )

    mask = df["reliable_window"] == True

    values = df.loc[mask, "CBI"].dropna().astype(float).values

    if len(values) == 0:
        log("没有可靠窗口，无法进行 CBI 分级。")
        return df

    unique_values = np.unique(values)

    if len(unique_values) == 1:
        df.loc[mask, "CBI_level_no"] = 1
        df.loc[mask, "CBI_level"] = "单一等级"
        df.loc[mask, "CBI_quantile_level_no"] = 1
        df.loc[mask, "CBI_quantile_level"] = "单一等级"
        df.loc[mask, "CBI_quantile_breaks"] = format_breaks_for_output(unique_values)
        df.loc[mask, "CBI_natural_level_no"] = 1
        df.loc[mask, "CBI_natural_level"] = "单一等级"
        df.loc[mask, "CBI_natural_breaks"] = format_breaks_for_output(unique_values)
        df.loc[mask, "CBI_level_agreement"] = True

        df["valid_contrast_window"] = (
            (df["reliable_window"] == True)
            & (df["dominant_different"] == True)
            & (df["CBI_level_no"] >= LOCAL_VALID_MIN_CBI_LEVEL)
            & (df["clip_membership_ok"] == True)
        )

        df["local_CBI_hotspot_window"] = (
            (df["reliable_window"] == True)
            & (df["CBI_level_no"] >= LOCAL_VALID_MIN_CBI_LEVEL)
        )

        df["distribution_contrast_window"] = (
            (df["local_CBI_hotspot_window"] == True)
            & (df["dominant_different"] == False)
        )

        return df

    k = min(4, len(unique_values))

    # local_CBI 分级口径：
    # 1. 分位数分级作为稳定基准，用于 valid_contrast_window 与连续段识别；
    # 2. 自然断点分级作为敏感性对照，检查高值窗口是否由数据内部分布自然分离。
    # 两者都只改变等级标签，不改变 CBI 数值。
    quantiles = np.linspace(0, 1, k + 1)[1:]
    quantile_bins = np.quantile(values, quantiles)
    natural_breaks = jenks_natural_breaks(values, max_classes=4)
    natural_upper_bins = natural_breaks[1:] if len(natural_breaks) > 1 else natural_breaks
    natural_k = max(1, len(natural_upper_bins))

    log(f"local_CBI 分位数分级阈值：{quantile_bins}")
    log(f"local_CBI 自然断点敏感性阈值：{natural_breaks}")

    quantile_name_map = cbi_level_names(k)
    natural_name_map = cbi_level_names(natural_k)
    quantile_break_text = format_breaks_for_output(quantile_bins)
    natural_break_text = format_breaks_for_output(natural_breaks)

    for idx in df.index:
        if not bool(df.loc[idx, "reliable_window"]):
            continue

        cbi = float(df.loc[idx, "CBI"])

        quantile_level_no = assign_level_by_upper_breaks(cbi, quantile_bins, k)
        natural_level_no = assign_level_by_upper_breaks(
            cbi,
            natural_upper_bins,
            natural_k
        )

        # 兼容字段：CBI_level 仍代表分位数稳定基准。
        df.loc[idx, "CBI_level_no"] = quantile_level_no
        df.loc[idx, "CBI_level"] = quantile_name_map.get(
            quantile_level_no,
            "未评级"
        )

        df.loc[idx, "CBI_quantile_level_no"] = quantile_level_no
        df.loc[idx, "CBI_quantile_level"] = quantile_name_map.get(
            quantile_level_no,
            "未评级"
        )
        df.loc[idx, "CBI_quantile_breaks"] = quantile_break_text

        df.loc[idx, "CBI_natural_level_no"] = natural_level_no
        df.loc[idx, "CBI_natural_level"] = natural_name_map.get(
            natural_level_no,
            "未评级"
        )
        df.loc[idx, "CBI_natural_breaks"] = natural_break_text
        df.loc[idx, "CBI_level_agreement"] = (
            quantile_level_no == natural_level_no
        )

    df["valid_contrast_window"] = (
        (df["reliable_window"] == True)
        & (df["dominant_different"] == True)
        & (df["CBI_level_no"] >= LOCAL_VALID_MIN_CBI_LEVEL)
        & (df["clip_membership_ok"] == True)
    )

    df["local_CBI_hotspot_window"] = (
        (df["reliable_window"] == True)
        & (df["CBI_level_no"] >= LOCAL_VALID_MIN_CBI_LEVEL)
    )

    df["distribution_contrast_window"] = (
        (df["local_CBI_hotspot_window"] == True)
        & (df["dominant_different"] == False)
    )

    df["clip_risk_level"] = df.apply(
        lambda row: classify_clip_risk(
            row.get("window_membership_change_ratio", 0),
            row.get("window_membership_change_ratio", 0)
        ),
        axis=1
    )

    df["station_reference_quality"] = df.apply(
        lambda row: classify_station_reference_quality(
            row.get("window_membership_change_ratio", 0),
            row.get("window_membership_change_ratio", 0)
        ),
        axis=1
    )

    return df


# ------------------------------------------------------------
# 10. 判断相邻窗口是否可以合并为同一社区分异连续段
# ------------------------------------------------------------

def can_merge_windows(prev_row, curr_row):
    station_gap = (
        float(curr_row["center_station_km"])
        - float(prev_row["center_station_km"])
    )

    if station_gap > LOCAL_WINDOW_STEP_KM * 1.6:
        return False

    same_top_A = str(prev_row["top_A"]) == str(curr_row["top_A"])
    same_top_B = str(prev_row["top_B"]) == str(curr_row["top_B"])

    jac_A = jaccard(
        parse_top3(prev_row["top3_A"]),
        parse_top3(curr_row["top3_A"])
    )

    jac_B = jaccard(
        parse_top3(prev_row["top3_B"]),
        parse_top3(curr_row["top3_B"])
    )

    similar_A = same_top_A or jac_A >= LOCAL_TOP3_JACCARD_MIN
    similar_B = same_top_B or jac_B >= LOCAL_TOP3_JACCARD_MIN

    return similar_A or similar_B


# ------------------------------------------------------------
# 11. 合并连续有效窗口，形成地名文化社区分异连续段
# ------------------------------------------------------------

def merge_valid_windows_to_segments(window_df):
    rows = []
    segment_counter = 0

    group_cols = ["boundary_name", "boundary_type", "side_width_km"]

    for group_key, sub in window_df.groupby(group_cols):
        boundary_name, boundary_type, side_width_km = group_key

        sub = sub.sort_values("center_station_km").copy()

        current = []

        def flush_current():
            nonlocal segment_counter

            if len(current) == 0:
                return

            cur_df = pd.DataFrame(current)

            start_km = cur_df["start_station_km"].min()
            end_km = cur_df["end_station_km"].max()
            length_km = end_km - start_km

            if len(cur_df) < LOCAL_MIN_CONSECUTIVE_WINDOWS:
                return

            if length_km < LOCAL_MIN_SEGMENT_LENGTH_KM:
                return

            segment_counter += 1

            row = {
                "contrast_segment_id": segment_counter,
                "boundary_name": boundary_name,
                "boundary_type": boundary_type,
                "side_width_km": side_width_km,
                "start_station_km": start_km,
                "end_station_km": end_km,
                "contrast_segment_length_km": length_km,
                "n_windows": len(cur_df),

                "segment_local_CBI_mean": cur_df["CBI"].mean(),
                "segment_local_CBI_max": cur_df["CBI"].max(),
                "segment_local_CBI_min": cur_df["CBI"].min(),
                "segment_small_CBI_mean": cur_df["small_CBI"].mean(),
                "segment_big_CBI_mean": cur_df["big_CBI"].mean(),

                "mean_top_A_share": cur_df["top_A_share"].mean(),
                "mean_top_B_share": cur_df["top_B_share"].mean(),
                "dominant_A_mode": get_mode(cur_df["top_A"]),
                "dominant_B_mode": get_mode(cur_df["top_B"]),
                "window_ids": ",".join(cur_df["window_id"].astype(str).tolist()),
                "mountain_length_km": cur_df["mountain_length_km"].iloc[0],

                "mean_clip_point_ratio": safe_mean(cur_df, "clip_point_ratio"),
                "max_clip_point_ratio": safe_max(cur_df, "clip_point_ratio"),
                "mean_n_clipped_points": safe_mean(cur_df, "n_clipped_points"),

                "mean_effective_clip_point_ratio": safe_mean(cur_df, "effective_clip_point_ratio"),
                "max_effective_clip_point_ratio": safe_max(cur_df, "effective_clip_point_ratio"),
                "mean_n_effective_clipped_points": safe_mean(cur_df, "n_effective_clipped_points"),

                "mean_window_membership_change_ratio": safe_mean(cur_df, "window_membership_change_ratio"),
                "max_window_membership_change_ratio": safe_max(cur_df, "window_membership_change_ratio"),
                "mean_added_by_clip_ratio": safe_mean(cur_df, "added_by_clip_ratio"),
                "max_added_by_clip_ratio": safe_max(cur_df, "added_by_clip_ratio"),
                "mean_removed_by_clip_ratio": safe_mean(cur_df, "removed_by_clip_ratio"),
                "max_removed_by_clip_ratio": safe_max(cur_df, "removed_by_clip_ratio"),
            }

            rows.append(row)

        for _, row in sub.iterrows():
            if not bool(row.get("valid_contrast_window", False)):
                flush_current()
                current = []
                continue

            if len(current) == 0:
                current.append(row.to_dict())
                continue

            prev_row = current[-1]

            if can_merge_windows(prev_row, row):
                current.append(row.to_dict())
            else:
                flush_current()
                current = [row.to_dict()]

        flush_current()

    if len(rows) == 0:
        return pd.DataFrame(
            columns=[
                "contrast_segment_id",
                "boundary_name",
                "boundary_type",
                "side_width_km",
                "start_station_km",
                "end_station_km",
                "contrast_segment_length_km",
                "n_windows",
                "segment_local_CBI_mean",
                "segment_local_CBI_max",
                "segment_local_CBI_min",
                "segment_small_CBI_mean",
                "segment_big_CBI_mean",
                "mean_top_A_share",
                "mean_top_B_share",
                "dominant_A_mode",
                "dominant_B_mode",
                "window_ids",
                "mountain_length_km",
                "mean_clip_point_ratio",
                "max_clip_point_ratio",
                "mean_n_clipped_points",
                "mean_effective_clip_point_ratio",
                "max_effective_clip_point_ratio",
                "mean_n_effective_clipped_points",
                "mean_window_membership_change_ratio",
                "max_window_membership_change_ratio",
                "mean_added_by_clip_ratio",
                "max_added_by_clip_ratio",
                "mean_removed_by_clip_ratio",
                "max_removed_by_clip_ratio",
            ]
        )

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# 12. 汇总山脉尺度文化分隔强度 mountain_CBI
# ------------------------------------------------------------

def summarize_mountain_cultural_boundary_strength(
    window_df,
    segment_df,
    return_side_width_summary=False
):
    window_df = window_df.copy()

    if "valid_contrast_window" not in window_df.columns:
        window_df["valid_contrast_window"] = False

    if "clip_membership_ok" not in window_df.columns:
        window_df["clip_membership_ok"] = True

    if "CBI_level_no" not in window_df.columns:
        window_df["CBI_level_no"] = 0

    if "side_width_km" not in window_df.columns:
        window_df["side_width_km"] = LOCAL_SIDE_WIDTHS_KM[0]

    window_df["side_width_km"] = pd.to_numeric(
        window_df["side_width_km"],
        errors="coerce"
    ).fillna(LOCAL_SIDE_WIDTHS_KM[0])

    if segment_df is None or "boundary_name" not in segment_df.columns:
        segment_df = pd.DataFrame(
            columns=[
                "contrast_segment_id",
                "boundary_name",
                "side_width_km",
                "start_station_km",
                "end_station_km",
                "contrast_segment_length_km",
                "segment_local_CBI_mean",
                "segment_local_CBI_max",
            ]
        )
    else:
        segment_df = segment_df.copy()

        if "side_width_km" not in segment_df.columns:
            segment_df["side_width_km"] = LOCAL_SIDE_WIDTHS_KM[0]

        segment_df["side_width_km"] = pd.to_numeric(
            segment_df["side_width_km"],
            errors="coerce"
        ).fillna(LOCAL_SIDE_WIDTHS_KM[0])

    rows = []

    for (name, side_width_km), win_sub in window_df.groupby(
        ["boundary_name", "side_width_km"]
    ):
        win_sub = win_sub.copy()

        mountain_length_km = win_sub["mountain_length_km"].iloc[0]

        reliable_windows = win_sub[
            win_sub["reliable_window"] == True
        ].copy()

        candidate_windows = win_sub[
            (win_sub["reliable_window"] == True)
            & (win_sub["dominant_different"] == True)
        ].copy()

        high_cbi_windows = win_sub[
            (win_sub["reliable_window"] == True)
            & (win_sub["CBI_level_no"] >= LOCAL_VALID_MIN_CBI_LEVEL)
        ].copy()

        clip_stable_reliable_windows = win_sub[
            (win_sub["reliable_window"] == True)
            & (win_sub["clip_membership_ok"] == True)
        ].copy()

        valid_contrast_windows = win_sub[
            win_sub["valid_contrast_window"] == True
        ].copy()

        seg_sub = segment_df[
            (segment_df["boundary_name"] == name)
            & (segment_df["side_width_km"] == side_width_km)
        ].copy()

        n_local_windows = len(win_sub)
        n_reliable_windows = len(reliable_windows)
        n_candidate_windows = len(candidate_windows)
        n_high_CBI_windows = len(high_cbi_windows)
        n_valid_contrast_windows = len(valid_contrast_windows)
        n_contrast_segments = len(seg_sub)

        reliable_window_ratio = safe_ratio(
            n_reliable_windows,
            n_local_windows
        )

        mean_local_CBI = safe_mean(win_sub, "CBI")
        mean_reliable_local_CBI = safe_mean(reliable_windows, "CBI")
        max_reliable_local_CBI = safe_max(reliable_windows, "CBI")
        p75_reliable_local_CBI = safe_quantile(reliable_windows, "CBI", 0.75)
        p90_reliable_local_CBI = safe_quantile(reliable_windows, "CBI", 0.90)

        mean_valid_contrast_local_CBI = safe_mean(valid_contrast_windows, "CBI")
        max_valid_contrast_local_CBI = safe_max(valid_contrast_windows, "CBI")

        candidate_window_ratio = (
            n_candidate_windows / n_reliable_windows
            if n_reliable_windows > 0 else 0.0
        )

        high_CBI_window_ratio = (
            n_high_CBI_windows / n_reliable_windows
            if n_reliable_windows > 0 else 0.0
        )

        valid_contrast_window_ratio = (
            n_valid_contrast_windows / n_reliable_windows
            if n_reliable_windows > 0 else 0.0
        )

        clip_stable_reliable_window_ratio = (
            len(clip_stable_reliable_windows) / n_reliable_windows
            if n_reliable_windows > 0 else 0.0
        )

        reliable_coverage_km, reliable_coverage_ratio = coverage_ratio_from_windows(
            reliable_windows,
            mountain_length_km
        )

        candidate_coverage_km, candidate_coverage_ratio = coverage_ratio_from_windows(
            candidate_windows,
            mountain_length_km
        )

        high_CBI_coverage_km, high_CBI_coverage_ratio = coverage_ratio_from_windows(
            high_cbi_windows,
            mountain_length_km
        )

        valid_contrast_coverage_km, valid_contrast_coverage_ratio = (
            coverage_ratio_from_windows(
                valid_contrast_windows,
                mountain_length_km
            )
        )

        if len(seg_sub) > 0:
            contrast_segment_union_length_km = interval_union_length_km(
                seg_sub["start_station_km"],
                seg_sub["end_station_km"]
            )

            contrast_segment_ratio = (
                contrast_segment_union_length_km / mountain_length_km
                if mountain_length_km > 0 else 0.0
            )

            contrast_segment_ratio = max(0.0, min(1.0, contrast_segment_ratio))

            mean_contrast_segment_local_CBI = safe_mean(
                seg_sub,
                "segment_local_CBI_mean"
            )

            max_contrast_segment_local_CBI = safe_max(
                seg_sub,
                "segment_local_CBI_max"
            )

            longest_contrast_segment_km = safe_max(
                seg_sub,
                "contrast_segment_length_km"
            )
        else:
            contrast_segment_union_length_km = 0.0
            contrast_segment_ratio = 0.0
            mean_contrast_segment_local_CBI = np.nan
            max_contrast_segment_local_CBI = np.nan
            longest_contrast_segment_km = 0.0

        mean_window_membership_change_ratio = safe_mean(
            win_sub,
            "window_membership_change_ratio"
        )

        max_window_membership_change_ratio = safe_max(
            win_sub,
            "window_membership_change_ratio"
        )

        row = {
            "boundary_name": name,
            "boundary_type": "mountain",
            "side_width_km": side_width_km,
            "mountain_length_km": mountain_length_km,

            "n_local_windows": n_local_windows,
            "n_reliable_windows": n_reliable_windows,
            "n_candidate_windows": n_candidate_windows,
            "n_high_CBI_windows": n_high_CBI_windows,
            "n_valid_contrast_windows": n_valid_contrast_windows,
            "n_contrast_segments": n_contrast_segments,

            "reliable_window_ratio": reliable_window_ratio,
            "clip_stable_reliable_window_ratio": clip_stable_reliable_window_ratio,
            "reliable_coverage_km": reliable_coverage_km,
            "reliable_coverage_ratio": reliable_coverage_ratio,
            "candidate_coverage_km": candidate_coverage_km,
            "candidate_coverage_ratio": candidate_coverage_ratio,
            "high_CBI_coverage_km": high_CBI_coverage_km,
            "high_CBI_coverage_ratio": high_CBI_coverage_ratio,
            "valid_contrast_coverage_km": valid_contrast_coverage_km,
            "valid_contrast_coverage_ratio": valid_contrast_coverage_ratio,

            "mean_local_CBI": mean_local_CBI,
            "mean_reliable_local_CBI": mean_reliable_local_CBI,
            "max_reliable_local_CBI": max_reliable_local_CBI,
            "p75_reliable_local_CBI": p75_reliable_local_CBI,
            "p90_reliable_local_CBI": p90_reliable_local_CBI,

            "mean_valid_contrast_local_CBI": mean_valid_contrast_local_CBI,
            "max_valid_contrast_local_CBI": max_valid_contrast_local_CBI,

            "candidate_window_ratio": candidate_window_ratio,
            "high_CBI_window_ratio": high_CBI_window_ratio,
            "valid_contrast_window_ratio": valid_contrast_window_ratio,

            "contrast_segment_union_length_km": contrast_segment_union_length_km,
            "contrast_segment_ratio": contrast_segment_ratio,
            "mean_contrast_segment_local_CBI": mean_contrast_segment_local_CBI,
            "max_contrast_segment_local_CBI": max_contrast_segment_local_CBI,
            "longest_contrast_segment_km": longest_contrast_segment_km,

            "mean_window_membership_change_ratio": mean_window_membership_change_ratio,
            "max_window_membership_change_ratio": max_window_membership_change_ratio,
            "clip_risk_level": classify_clip_risk(
                mean_window_membership_change_ratio,
                max_window_membership_change_ratio
            ),
            "station_reference_quality": classify_station_reference_quality(
                mean_window_membership_change_ratio,
                max_window_membership_change_ratio
            ),
        }

        rows.append(row)

    out = pd.DataFrame(rows)

    if len(out) == 0:
        if return_side_width_summary:
            return out, out
        return out

    # --------------------------------------------------------
    # 先在每条山脉内部选择主判读侧宽。
    # 这样长山脉不会因为 50 km 侧宽过窄而被误判为无可靠窗口，
    # 也避免把不同侧宽窗口混在一起计算 mountain_CBI。
    # --------------------------------------------------------

    out["selection_eligible"] = (
        (out["n_reliable_windows"] >= LOCAL_PRIMARY_MIN_RELIABLE_WINDOWS)
        & (
            out["reliable_window_ratio"]
            >= LOCAL_PRIMARY_MIN_RELIABLE_WINDOW_RATIO
        )
        & (
            out["reliable_coverage_ratio"]
            >= LOCAL_PRIMARY_MIN_RELIABLE_COVERAGE_RATIO
        )
    )

    out["mean_reliable_local_CBI_width_norm"] = (
        out
        .groupby("boundary_name")["mean_reliable_local_CBI"]
        .transform(normalize_series)
    )

    out["p90_reliable_local_CBI_width_norm"] = (
        out
        .groupby("boundary_name")["p90_reliable_local_CBI"]
        .transform(normalize_series)
    )

    out["side_width_local_signal_score"] = (
        0.45 * out["mean_reliable_local_CBI_width_norm"].fillna(0.0)
        + 0.35 * out["p90_reliable_local_CBI_width_norm"].fillna(0.0)
        + 0.10 * out["high_CBI_window_ratio"].fillna(0.0)
        + 0.10 * out["candidate_window_ratio"].fillna(0.0)
    )

    out["side_width_local_signal_level"] = out["side_width_local_signal_score"].apply(
        cbi_level_from_score
    )

    out["side_width_selection_score"] = (
        0.30 * out["reliable_coverage_ratio"].fillna(0.0)
        + 0.25 * out["p90_reliable_local_CBI_width_norm"].fillna(0.0)
        + 0.20 * out["mean_reliable_local_CBI_width_norm"].fillna(0.0)
        + 0.10 * out["high_CBI_coverage_ratio"].fillna(0.0)
        + 0.05 * out["candidate_coverage_ratio"].fillna(0.0)
        + 0.05 * out["clip_stable_reliable_window_ratio"].fillna(0.0)
        + 0.05 * out["reliable_window_ratio"].fillna(0.0)
    )

    selected_indices = []

    for name, sub in out.groupby("boundary_name"):
        eligible = sub[sub["selection_eligible"] == True].copy()

        if len(eligible) > 0:
            candidates = eligible
        else:
            candidates = sub

        max_score = candidates["side_width_selection_score"].max()

        near_best = candidates[
            candidates["side_width_selection_score"]
            >= max_score - LOCAL_SIDE_WIDTH_SELECTION_SCORE_TOLERANCE
        ].copy()

        # 若多个侧宽得分接近，优先选择更窄的侧宽。
        # 这可以降低外围点掺入风险，使主判读尺度更保守。
        candidates = near_best.sort_values(
            [
                "side_width_km",
                "side_width_selection_score",
                "reliable_window_ratio",
                "p90_reliable_local_CBI",
                "mean_reliable_local_CBI",
            ],
            ascending=[True, False, False, False, False]
        )

        selected_indices.append(candidates.index[0])

    out["selected_primary_width"] = out.index.isin(selected_indices)

    reasons = []

    for _, row in out.iterrows():
        if not bool(row["selected_primary_width"]):
            reasons.append("非主判读侧宽，保留用于敏感性比较。")
            continue

        if bool(row["selection_eligible"]):
            reasons.append(
                "达到可靠窗口数量、可靠窗口比例和可靠覆盖长度比例下限，"
                "且侧宽选择得分最高，作为该山脉主判读尺度。"
            )
        else:
            reasons.append(
                "未达到正式可靠覆盖下限，但在候选侧宽中证据最完整；"
                "该山脉应标注为诊断性判读，并优先检查参数或线数据。"
            )

    out["side_width_selection_reason"] = reasons

    side_width_summary = out.sort_values(
        ["boundary_name", "side_width_km"]
    ).copy()

    primary = out[out["selected_primary_width"] == True].copy()

    side_widths_tested = (
        out
        .groupby("boundary_name")["side_width_km"]
        .apply(lambda s: "|".join(map(str, sorted(set(s)))))
        .to_dict()
    )

    primary["primary_side_width_km"] = primary["side_width_km"]
    primary["side_widths_tested"] = (
        primary["boundary_name"]
        .map(side_widths_tested)
        .fillna("")
    )

    # --------------------------------------------------------
    # 山脉尺度 cultural boundary strength 综合指数。
    # 它只使用每条山脉的主判读侧宽，并且不依赖 n_contrast_segments 是否为 0。
    # contrast_segment_ratio 是辅助项，不能压倒 local_CBI 的移动窗口证据。
    # --------------------------------------------------------

    for col in [
        "mean_reliable_local_CBI",
        "p90_reliable_local_CBI",
    ]:
        primary[f"{col}_norm"] = normalize_series(primary[col])

    primary["local_signal_CBI"] = (
        0.45 * primary["mean_reliable_local_CBI_norm"].fillna(0.0)
        + 0.35 * primary["p90_reliable_local_CBI_norm"].fillna(0.0)
        + 0.10 * primary["high_CBI_window_ratio"].fillna(0.0)
        + 0.10 * primary["candidate_window_ratio"].fillna(0.0)
    )

    primary["local_signal_level"] = primary["local_signal_CBI"].apply(
        cbi_level_from_score
    )

    primary["mountain_CBI"] = (
        0.30 * primary["mean_reliable_local_CBI_norm"]
        + 0.25 * primary["p90_reliable_local_CBI_norm"]
        + 0.20 * primary["high_CBI_coverage_ratio"].fillna(0.0)
        + 0.10 * primary["candidate_coverage_ratio"].fillna(0.0)
        + 0.10 * primary["contrast_segment_ratio"].fillna(0.0)
        + 0.05 * primary["reliable_coverage_ratio"].fillna(0.0)
    )

    primary["mountain_CBI"] = primary["mountain_CBI"].fillna(0.0)

    primary["mountain_CBI_confidence"] = (
        0.45 * np.minimum(
            1.0,
            primary["reliable_coverage_ratio"].fillna(0.0)
            / max(LOCAL_PRIMARY_MIN_RELIABLE_COVERAGE_RATIO, 0.01)
        )
        + 0.25 * np.minimum(
            1.0,
            primary["reliable_window_ratio"].fillna(0.0)
            / max(LOCAL_PRIMARY_MIN_RELIABLE_WINDOW_RATIO, 0.01)
        )
        + 0.30 * primary["clip_stable_reliable_window_ratio"].fillna(0.0)
    ).clip(lower=0.0, upper=1.0)

    def evidence_quality(row):
        if int(row.get("n_reliable_windows", 0) or 0) == 0:
            return "无可靠窗口"

        if (
            float(row.get("local_signal_CBI", 0) or 0) >= 0.50
            and (
                float(row.get("reliable_coverage_ratio", 0) or 0)
                < LOCAL_PRIMARY_MIN_RELIABLE_COVERAGE_RATIO
            )
        ):
            return "强局部信号但覆盖不足"

        if row.get("clip_risk_level", "") in ["偏高", "高"]:
            return "正式可用但需注意 clip"

        if bool(row.get("selection_eligible", False)):
            if float(row.get("mountain_CBI_confidence", 0) or 0) >= 0.75:
                return "正式可靠"
            return "正式可用但需注意 clip"

        return "诊断性证据"

    primary["evidence_quality"] = primary.apply(evidence_quality, axis=1)

    primary["mountain_CBI_fixed_level"] = primary["mountain_CBI"].apply(
        cbi_level_from_score
    )

    mountain_breaks = jenks_natural_breaks(
        primary["mountain_CBI"],
        max_classes=4
    )
    mountain_upper_bins = (
        mountain_breaks[1:]
        if len(mountain_breaks) > 1
        else mountain_breaks
    )
    mountain_natural_k = max(1, len(mountain_upper_bins))
    mountain_natural_names = cbi_level_names(mountain_natural_k)
    mountain_break_text = format_breaks_for_output(mountain_breaks)

    primary["mountain_CBI_natural_level_no"] = primary["mountain_CBI"].apply(
        lambda x: assign_level_by_upper_breaks(
            x,
            mountain_upper_bins,
            mountain_natural_k
        )
    )
    primary["mountain_CBI_natural_level"] = primary[
        "mountain_CBI_natural_level_no"
    ].apply(lambda x: mountain_natural_names.get(int(x), "未评级"))
    primary["mountain_CBI_natural_breaks"] = mountain_break_text

    # 主展示等级改为自然断点等级；固定阈值等级保存在 mountain_CBI_fixed_level。
    primary["mountain_CBI_level"] = primary["mountain_CBI_natural_level"]
    primary["mountain_CBI_level_method"] = "natural_breaks_main_display"

    log(f"mountain_CBI 自然断点主展示阈值：{mountain_breaks}")

    primary = primary.sort_values(
        ["mountain_CBI", "p90_reliable_local_CBI", "mean_reliable_local_CBI"],
        ascending=[False, False, False]
    )

    primary["mountain_CBI_rank"] = range(1, len(primary) + 1)

    primary = add_mountain_interpretation(primary)

    if return_side_width_summary:
        return primary, side_width_summary

    return primary


# ------------------------------------------------------------
# 13. 断点续算与增量写出
# ------------------------------------------------------------

def load_existing_window_results():
    """
    读取已经写出的移动窗口结果，用于全量 raw 山脉计算时断点续算。

    这里只读取 window 级结果，因为 segment / mountain summary 都可以由
    window_df 重新汇总得到，避免多个中间表之间出现不一致。
    """
    if not LOCAL_RESUME_FROM_EXISTING:
        return pd.DataFrame()

    output_path = Path(LOCAL_CBI_WINDOWS_CSV)

    if not output_path.exists():
        return pd.DataFrame()

    try:
        existing_df = pd.read_csv(output_path, encoding="utf-8-sig")
    except Exception as exc:
        log(f"读取已有 window 结果失败，将从头计算：{exc}")
        return pd.DataFrame()

    if len(existing_df) == 0 or "boundary_name" not in existing_df.columns:
        return pd.DataFrame()

    existing_count = existing_df["boundary_name"].astype(str).nunique()
    log(
        "检测到已有移动窗口结果："
        f"{len(existing_df)} 个窗口，{existing_count} 座山脉，"
        "将跳过已完成山脉继续计算。"
    )

    return existing_df


def build_and_write_outputs(
    all_window_results,
    write_metadata=False,
    write_advice=False,
    checkpoint_label="当前"
):
    """
    根据当前已完成的 window 结果，统一重建并写出四张 06b 表。

    注意：该函数不改变 CBI 公式，只是把当前累计结果及时落盘；
    因此中途停止时，网页导出脚本仍能读取已经完成的山脉。
    """
    if len(all_window_results) == 0:
        log("尚无可写出的 local_CBI 结果。")
        return None, None, None, None, None

    window_df = pd.concat(all_window_results, ignore_index=True)
    window_df = window_df.drop_duplicates().reset_index(drop=True)

    window_df = add_local_cbi_levels(window_df)

    segment_df = merge_valid_windows_to_segments(window_df)

    mountain_strength_df, side_width_summary_df = summarize_mountain_cultural_boundary_strength(
        window_df,
        segment_df,
        return_side_width_summary=True
    )
    mountain_system_strength_df = summarize_mountain_system_cultural_boundary_strength(
        mountain_strength_df
    )

    window_df = reorder_columns(
        window_df,
        LOCAL_CBI_WINDOW_CORE_COLUMNS
    )

    segment_df = reorder_columns(
        segment_df,
        COMMUNITY_DIFF_SEGMENT_CORE_COLUMNS
    )

    mountain_strength_df = reorder_columns(
        mountain_strength_df,
        MOUNTAIN_STRENGTH_CORE_COLUMNS
    )

    side_width_summary_df = reorder_columns(
        side_width_summary_df,
        MOUNTAIN_SIDE_WIDTH_CORE_COLUMNS
    )

    mountain_system_strength_df = reorder_columns(
        mountain_system_strength_df,
        MOUNTAIN_SYSTEM_STRENGTH_CORE_COLUMNS
    )

    TABLE_06B_DIR.mkdir(parents=True, exist_ok=True)

    write_csv_with_legacy_alias(
        window_df,
        LOCAL_CBI_WINDOWS_CSV,
        label=f"{checkpoint_label}移动窗口 local_CBI"
    )

    write_csv_with_legacy_alias(
        segment_df,
        COMMUNITY_DIFF_SEGMENTS_CSV,
        legacy_path=LOCAL_CBI_SEGMENTS_CSV,
        label=f"{checkpoint_label}地名文化社区分异连续段"
    )

    write_csv_with_legacy_alias(
        mountain_strength_df,
        MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV,
        legacy_path=LOCAL_CBI_MOUNTAIN_SUMMARY_CSV,
        label=f"{checkpoint_label}山脉尺度文化分隔强度 mountain_CBI"
    )

    write_csv_with_legacy_alias(
        side_width_summary_df,
        MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV,
        label=f"{checkpoint_label}山脉侧宽候选敏感性汇总"
    )

    write_csv_with_legacy_alias(
        mountain_system_strength_df,
        MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV,
        label=f"{checkpoint_label}复合山系文化分隔强度 mountain_system_CBI"
    )

    if write_metadata:
        write_run_metadata(mountain_strength_df, side_width_summary_df)

    if write_advice:
        log_result_advice(mountain_strength_df)

    log(
        f"{checkpoint_label}写出完成："
        f"{mountain_strength_df['boundary_name'].astype(str).nunique()} 座山脉，"
        f"{len(window_df)} 个窗口。"
    )

    return (
        window_df,
        segment_df,
        mountain_strength_df,
        side_width_summary_df,
        mountain_system_strength_df,
    )


# ------------------------------------------------------------
# 14. 主函数
# ------------------------------------------------------------

def main():
    log("读取带 community_id 的地名点：")
    log(str(CHAR_POINTS_COMMUNITY_GPKG))

    point_gdf = gpd.read_file(CHAR_POINTS_COMMUNITY_GPKG).to_crs(ALBERS_CHINA)

    point_gdf["community_id"] = point_gdf["community_id"].astype(str)
    point_gdf["semantic_type"] = point_gdf["semantic_type"].astype(str)

    log("读取山脉数据：")
    log(str(MOUNTAIN_SHP))

    mountain_gdf = gpd.read_file(MOUNTAIN_SHP).to_crs(ALBERS_CHINA)

    name_col = barrier06.detect_name_column(mountain_gdf)

    if LOCAL_USE_ALL_RAW_MOUNTAINS:
        mountain_names_to_run = (
            mountain_gdf[name_col]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .tolist()
        )
    else:
        mountain_names_to_run = list(MOUNTAIN_NAMES)

    log(f"山脉名称字段：{name_col}")
    log(
        "待计算山脉："
        f"{len(mountain_names_to_run)} 条"
        f"（LOCAL_USE_ALL_RAW_MOUNTAINS={LOCAL_USE_ALL_RAW_MOUNTAINS}）"
    )

    existing_window_df = load_existing_window_results()
    all_window_results = []
    completed_mountains = set()

    if len(existing_window_df) > 0:
        all_window_results.append(existing_window_df)
        completed_mountains = set(
            existing_window_df["boundary_name"]
            .dropna()
            .astype(str)
            .unique()
        )

    pending_mountain_names = [
        mountain_name
        for mountain_name in mountain_names_to_run
        if str(mountain_name) not in completed_mountains
    ]

    log(
        "断点续算状态："
        f"已完成 {len(completed_mountains)} 座，"
        f"待计算 {len(pending_mountain_names)} 座。"
    )

    completed_since_checkpoint = 0

    for mountain_name in pending_mountain_names:
        try:
            win_df = evaluate_mountain_local_windows(
                point_gdf=point_gdf,
                mountain_gdf=mountain_gdf,
                boundary_name=mountain_name,
                name_col=name_col
            )

            if len(win_df) > 0:
                all_window_results.append(win_df)
                completed_since_checkpoint += 1

                if (
                    LOCAL_CHECKPOINT_EVERY_N
                    and completed_since_checkpoint % LOCAL_CHECKPOINT_EVERY_N == 0
                ):
                    build_and_write_outputs(
                        all_window_results,
                        checkpoint_label="断点"
                    )
            else:
                log(f"山脉 {mountain_name} 未形成有效移动窗口，已跳过。")

        except Exception as exc:
            log(f"山脉 {mountain_name} 计算失败：{exc}")

    if len(all_window_results) == 0:
        log("没有得到任何 local_CBI 结果。")
        return

    build_and_write_outputs(
        all_window_results,
        write_metadata=True,
        write_advice=True,
        checkpoint_label="最终"
    )

    log("完成。")


if __name__ == "__main__":
    main()
