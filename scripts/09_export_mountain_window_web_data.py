"""
09_export_mountain_window_web_data.py
-------------------------------------
将 06b 山脉移动窗口 CBI 结果导出为 GitHub Pages 可直接读取的静态数据。

本脚本只做数据格式转换，不重新计算 CBI，不启动 Flask / FastAPI。
网页端读取这些 JSON / GeoJSON 后，即可查询山脉 mountain_CBI，
并在地图上可视化不同移动窗口和地名文化社区分异连续段。
"""

import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


try:
    import numpy as np
    import pandas as pd
    import geopandas as gpd
    from shapely.geometry import LineString, MultiLineString
    from shapely.ops import linemerge, unary_union
except ImportError as exc:
    raise SystemExit(
        "缺少导出网页数据所需依赖。请使用 placename 环境运行：\n"
        "python scripts/09_export_mountain_window_web_data.py\n"
        f"原始错误：{exc}"
    )


try:
    import config
except Exception as exc:
    raise SystemExit(f"无法读取 config.py：{exc}")


def load_06b_module():
    script_path = BASE_DIR / "scripts" / "06b_mountain_moving_window_cbi.py"
    if not script_path.exists():
        raise FileNotFoundError(f"未找到 06b 脚本：{script_path}")

    spec = importlib.util.spec_from_file_location("mountain06b", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mountain06b = load_06b_module()


RAW_DIR = getattr(config, "RAW_DIR", BASE_DIR / "data" / "raw")
OUTPUT_DIR = getattr(config, "OUTPUT_DIR", BASE_DIR / "output")
TABLE_DIR = getattr(config, "TABLE_DIR", OUTPUT_DIR / "tables")
TABLE_06B_DIR = getattr(
    config,
    "TABLE_06B_DIR",
    TABLE_DIR / "06b_mountain_moving_window_cbi"
)

MOUNTAIN_SHP = Path(getattr(config, "MOUNTAIN_SHP", RAW_DIR / "mountain_ranges_140.shp"))
CHAR_POINTS_COMMUNITY_GPKG = Path(
    getattr(
        config,
        "CHAR_POINTS_COMMUNITY_GPKG",
        OUTPUT_DIR / "maps" / "04_clq_louvain_communities" / "char_points_community.gpkg"
    )
)
MOUNTAIN_NAMES = list(getattr(config, "MOUNTAIN_NAMES", []))
ALBERS_CHINA = getattr(config, "ALBERS_CHINA", mountain06b.ALBERS_CHINA)

LOCAL_CBI_WINDOWS_CSV = Path(
    getattr(config, "LOCAL_CBI_WINDOWS_CSV", TABLE_06B_DIR / "mountain_local_cbi_windows.csv")
)
COMMUNITY_DIFF_SEGMENTS_CSV = Path(
    getattr(
        config,
        "COMMUNITY_DIFF_SEGMENTS_CSV",
        TABLE_06B_DIR / "mountain_community_differentiation_segments.csv"
    )
)
MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV = Path(
    getattr(
        config,
        "MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV",
        TABLE_06B_DIR / "mountain_cultural_boundary_strength.csv"
    )
)
MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV = Path(
    getattr(
        config,
        "MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV",
        TABLE_06B_DIR / "mountain_side_width_summary.csv"
    )
)
MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV = Path(
    getattr(
        config,
        "MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV",
        TABLE_06B_DIR / "mountain_system_cultural_boundary_strength.csv"
    )
)

WEB_DIR = BASE_DIR / "web"
WEB_DATA_DIR = WEB_DIR / "data" / "mountain_windows"
WEB_BOUNDARY_DIR = WEB_DATA_DIR / "boundaries"
WEB_WINDOW_DIR = WEB_DATA_DIR / "windows"
WEB_SEGMENT_DIR = WEB_DATA_DIR / "segments"
WEB_POINT_DIR = WEB_DATA_DIR / "points"

BOUNDARY_SIMPLIFY_METERS = 1200
WINDOW_GEOMETRY_SIMPLIFY_METERS = 400
DEFAULT_POINT_SIDE_WIDTH_KM = 50
MAX_PLACE_POINTS_PER_MOUNTAIN = 5000
RANDOM_STATE = 42


def log(message):
    print(f"[09_export_mountain_window_web_data] {message}")


def sanitize_filename(name):
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", str(name)).strip()
    return cleaned.replace(" ", "_")


def ensure_dirs():
    for path in [WEB_DATA_DIR, WEB_BOUNDARY_DIR, WEB_WINDOW_DIR, WEB_SEGMENT_DIR, WEB_POINT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def detect_name_column(gdf):
    candidates = [
        "Name",
        "name",
        "NAME",
        "名称",
        "山脉名",
        "NAME_CHN",
        "中文名",
    ]
    for col in candidates:
        if col in gdf.columns:
            return col
    raise ValueError(f"没有找到山脉名称字段。当前字段：{list(gdf.columns)}")


def normalize_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    text = str(value)
    if text in ["True", "False"]:
        return text == "True"
    return value


def dataframe_to_records(df):
    rows = []
    for row in df.to_dict(orient="records"):
        rows.append({key: normalize_value(val) for key, val in row.items()})
    return rows


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"写出 JSON：{path}")


def read_csv_required(path, label):
    if not path.exists():
        raise FileNotFoundError(
            f"缺少 {label}：{path}\n"
            "请先运行 scripts/06b_mountain_moving_window_cbi.py"
        )
    return pd.read_csv(path, encoding="utf-8-sig")


def get_boundary_geom(mountain_gdf, mountain_name, name_col):
    sub = mountain_gdf[mountain_gdf[name_col].astype(str) == str(mountain_name)].copy()
    if len(sub) == 0:
        raise ValueError(f"山脉线数据中没有找到：{mountain_name}")

    geom = unary_union(sub.geometry)
    try:
        geom = linemerge(geom)
    except Exception:
        pass
    return geom


def export_boundary_geojson(mountain_gdf, mountain_name, name_col, file_name):
    geom = get_boundary_geom(mountain_gdf, mountain_name, name_col)
    geom = geom.simplify(BOUNDARY_SIMPLIFY_METERS, preserve_topology=True)

    gdf = gpd.GeoDataFrame(
        [{"boundary_name": mountain_name, "boundary_type": "mountain", "geometry": geom}],
        geometry="geometry",
        crs=mountain_gdf.crs
    ).to_crs("EPSG:4326")

    out_path = WEB_BOUNDARY_DIR / f"{file_name}.geojson"
    gdf.to_file(out_path, driver="GeoJSON", encoding="utf-8")
    log(f"写出山脉线 GeoJSON：{out_path}")
    return f"mountain_windows/boundaries/{file_name}.geojson"


def interpolate_on_segment(seg, station_m):
    seg_start = float(seg["station_start_m"])
    seg_len = float(seg["seg_len_m"])
    if seg_len <= 0:
        return None

    t = (float(station_m) - seg_start) / seg_len
    t = max(0.0, min(1.0, t))

    x = float(seg["x1"]) + (float(seg["x2"]) - float(seg["x1"])) * t
    y = float(seg["y1"]) + (float(seg["y2"]) - float(seg["y1"])) * t
    return x, y


def station_interval_to_geometry(segment_gdf, start_km, end_km):
    start_m = float(start_km) * 1000
    end_m = float(end_km) * 1000
    if end_m <= start_m:
        return None

    pieces = []

    for _, seg in segment_gdf.iterrows():
        seg_start = float(seg["station_start_m"])
        seg_end = float(seg["station_end_m"])

        overlap_start = max(start_m, seg_start)
        overlap_end = min(end_m, seg_end)

        if overlap_end <= overlap_start:
            continue

        p1 = interpolate_on_segment(seg, overlap_start)
        p2 = interpolate_on_segment(seg, overlap_end)
        if p1 is None or p2 is None or p1 == p2:
            continue

        pieces.append(LineString([p1, p2]))

    if not pieces:
        return None

    if len(pieces) == 1:
        return pieces[0]

    return MultiLineString(pieces)


def build_interval_geojson(rows, segment_gdf, property_columns, output_path):
    features = []

    for _, row in rows.iterrows():
        geom = station_interval_to_geometry(
            segment_gdf,
            row["start_station_km"],
            row["end_station_km"]
        )
        if geom is None or geom.is_empty:
            continue

        geom = geom.simplify(WINDOW_GEOMETRY_SIMPLIFY_METERS, preserve_topology=True)

        props = {
            col: normalize_value(row[col])
            for col in property_columns
            if col in row.index
        }
        features.append({**props, "geometry": geom})

    if not features:
        empty = gpd.GeoDataFrame(columns=property_columns + ["geometry"], geometry="geometry", crs=segment_gdf.crs)
        empty.to_crs("EPSG:4326").to_file(output_path, driver="GeoJSON", encoding="utf-8")
        return 0

    gdf = gpd.GeoDataFrame(features, geometry="geometry", crs=segment_gdf.crs).to_crs("EPSG:4326")
    gdf.to_file(output_path, driver="GeoJSON", encoding="utf-8")
    return len(gdf)


def export_empty_geojson(output_path, crs="EPSG:4326"):
    empty = gpd.GeoDataFrame(
        [{"geometry": None}],
        geometry="geometry",
        crs=crs
    ).iloc[0:0]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    empty.to_file(output_path, driver="GeoJSON", encoding="utf-8")


def export_place_points_geojson(point_gdf, segment_gdf, mountain_name, side_width_km, file_name):
    """
    导出某条山脉两侧地名点。
    这里不重新计算 CBI，只为网页展示提供点位、侧别、距离和特征字信息。
    """
    output_path = WEB_POINT_DIR / f"{file_name}.geojson"
    side_width_m = float(side_width_km) * 1000

    candidate_points = mountain06b.filter_points_near_boundary(
        point_gdf,
        segment_gdf,
        side_width_m
    )

    if len(candidate_points) == 0:
        export_empty_geojson(output_path)
        return f"mountain_windows/points/{file_name}.geojson", 0

    nearest_info = mountain06b.attach_points_to_nearest_segments(
        candidate_points,
        segment_gdf
    )

    nearest_info = nearest_info[nearest_info["dist_m"] <= side_width_m].copy()

    if len(nearest_info) == 0:
        export_empty_geojson(output_path)
        return f"mountain_windows/points/{file_name}.geojson", 0

    keep_side_cols = [
        "source_id",
        "side",
        "dist_m",
        "station_m",
        "raw_station_m",
        "station_clip_abs_offset_m",
        "clip_direction",
        "effective_clip",
    ]

    side_info = nearest_info[keep_side_cols].copy()
    export_df = candidate_points.merge(side_info, on="source_id", how="inner")
    export_df["boundary_name"] = mountain_name
    export_df["side_width_km"] = float(side_width_km)

    # 网页弹窗需要 small_feature / big_feature；原始数据中对应 feature_id / semantic_type。
    export_df["small_feature"] = export_df.get("feature_id", "")
    export_df["big_feature"] = export_df.get("semantic_type", "")

    keep_cols = [
        "boundary_name",
        "side_width_km",
        "source_id",
        "full_name",
        "raw_name",
        "clean_name",
        "name_body",
        "part",
        "char",
        "feature_id",
        "small_feature",
        "big_feature",
        "semantic_type",
        "community_id",
        "community_features",
        "side",
        "dist_m",
        "station_m",
        "raw_station_m",
        "station_clip_abs_offset_m",
        "clip_direction",
        "effective_clip",
        "geometry",
    ]

    keep_cols = [col for col in keep_cols if col in export_df.columns]
    export_df = export_df[keep_cols].copy()

    if len(export_df) > MAX_PLACE_POINTS_PER_MOUNTAIN:
        export_df = export_df.sample(
            n=MAX_PLACE_POINTS_PER_MOUNTAIN,
            random_state=RANDOM_STATE
        ).copy()

    export_gdf = gpd.GeoDataFrame(
        export_df,
        geometry="geometry",
        crs=point_gdf.crs
    ).to_crs("EPSG:4326")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_gdf.to_file(output_path, driver="GeoJSON", encoding="utf-8")

    return f"mountain_windows/points/{file_name}.geojson", len(export_gdf)


def export_mountain_window_data():
    ensure_dirs()

    summary_df = read_csv_required(
        MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV,
        "mountain_cultural_boundary_strength.csv"
    )
    window_df = read_csv_required(LOCAL_CBI_WINDOWS_CSV, "mountain_local_cbi_windows.csv")
    segment_df = read_csv_required(
        COMMUNITY_DIFF_SEGMENTS_CSV,
        "mountain_community_differentiation_segments.csv"
    )

    if MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV.exists():
        side_width_df = pd.read_csv(MOUNTAIN_SIDE_WIDTH_SUMMARY_CSV, encoding="utf-8-sig")
    else:
        side_width_df = pd.DataFrame()

    if MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV.exists():
        mountain_system_df = pd.read_csv(
            MOUNTAIN_SYSTEM_CULTURAL_BOUNDARY_STRENGTH_CSV,
            encoding="utf-8-sig"
        )
    else:
        mountain_system_df = pd.DataFrame()

    mountain_gdf = gpd.read_file(MOUNTAIN_SHP)
    if mountain_gdf.crs is None:
        mountain_gdf = mountain_gdf.set_crs("EPSG:4326", allow_override=True)
    mountain_gdf = mountain_gdf.to_crs(ALBERS_CHINA)
    name_col = detect_name_column(mountain_gdf)

    if not CHAR_POINTS_COMMUNITY_GPKG.exists():
        raise FileNotFoundError(
            f"缺少地名点数据：{CHAR_POINTS_COMMUNITY_GPKG}\n"
            "请先完成 04_clq_louvain_communities.py。"
        )

    point_gdf = gpd.read_file(CHAR_POINTS_COMMUNITY_GPKG)
    if point_gdf.crs is None:
        point_gdf = point_gdf.set_crs("EPSG:4326", allow_override=True)
    point_gdf = point_gdf.to_crs(ALBERS_CHINA)

    raw_mountain_names = (
        mountain_gdf[name_col]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    # 用户要求 raw 山脉 shp 中所有山脉都能查询。
    # 因此索引以 shp 全量名称为准；有 06b 指标的显示 CBI，
    # 没有的通常是样本不足或未形成有效移动窗口，而不是网页端漏算。
    mountain_names_to_export = raw_mountain_names

    mountain_index = []

    window_props = [
        "boundary_name",
        "side_width_km",
        "window_id",
        "center_station_km",
        "start_station_km",
        "end_station_km",
        "window_length_km",
        "mountain_length_km",
        "CBI",
        "small_CBI",
        "big_CBI",
        "CBI_level",
        "CBI_level_no",
        "CBI_level_method",
        "CBI_quantile_level",
        "CBI_quantile_level_no",
        "CBI_quantile_breaks",
        "CBI_natural_level",
        "CBI_natural_level_no",
        "CBI_natural_breaks",
        "CBI_level_agreement",
        "reliable_window",
        "valid_contrast_window",
        "local_CBI_hotspot_window",
        "distribution_contrast_window",
        "n_left",
        "n_right",
        "sample_balance",
        "top_A",
        "top_B",
        "window_membership_change_ratio",
        "clip_risk_level",
        "station_reference_quality",
    ]

    segment_props = [
        "contrast_segment_id",
        "boundary_name",
        "side_width_km",
        "start_station_km",
        "end_station_km",
        "contrast_segment_length_km",
        "n_windows",
        "segment_local_CBI_mean",
        "segment_local_CBI_max",
        "segment_small_CBI_mean",
        "segment_big_CBI_mean",
        "dominant_A_mode",
        "dominant_B_mode",
        "mean_window_membership_change_ratio",
    ]

    for mountain_name in mountain_names_to_export:
        summary_row = summary_df[summary_df["boundary_name"].astype(str) == str(mountain_name)]
        has_cbi = len(summary_row) > 0

        if has_cbi:
            summary_record = summary_row.iloc[0].to_dict()
            primary_width = normalize_value(summary_record.get("primary_side_width_km"))
            if primary_width is None:
                primary_width = normalize_value(summary_record.get("side_width_km"))
        else:
            summary_record = {}
            primary_width = DEFAULT_POINT_SIDE_WIDTH_KM

        primary_width = float(primary_width)
        file_name = sanitize_filename(mountain_name)

        try:
            boundary_geom = get_boundary_geom(mountain_gdf, mountain_name, name_col)
            segment_gdf, _ = mountain06b.boundary_to_station_segments(
                boundary_geom,
                mountain_gdf.crs
            )
        except Exception as exc:
            log(f"跳过 {mountain_name}：无法构建 station 线段。原因：{exc}")
            continue

        boundary_file = export_boundary_geojson(mountain_gdf, mountain_name, name_col, file_name)

        if has_cbi:
            mountain_windows = window_df[
                (window_df["boundary_name"].astype(str) == str(mountain_name))
                & (pd.to_numeric(window_df["side_width_km"], errors="coerce") == primary_width)
            ].copy()
        else:
            mountain_windows = pd.DataFrame(columns=window_props)

        mountain_windows = mountain_windows.sort_values("center_station_km")

        window_file_path = WEB_WINDOW_DIR / f"{file_name}.geojson"
        n_windows = build_interval_geojson(
            mountain_windows,
            segment_gdf,
            window_props,
            window_file_path
        )

        if has_cbi:
            mountain_segments = segment_df[
                (segment_df["boundary_name"].astype(str) == str(mountain_name))
                & (pd.to_numeric(segment_df["side_width_km"], errors="coerce") == primary_width)
            ].copy()
        else:
            mountain_segments = pd.DataFrame(columns=segment_props)

        mountain_segments = mountain_segments.sort_values("start_station_km")

        segment_file_path = WEB_SEGMENT_DIR / f"{file_name}.geojson"
        n_segments = build_interval_geojson(
            mountain_segments,
            segment_gdf,
            segment_props,
            segment_file_path
        )

        point_file, n_points = export_place_points_geojson(
            point_gdf=point_gdf,
            segment_gdf=segment_gdf,
            mountain_name=mountain_name,
            side_width_km=primary_width,
            file_name=file_name
        )

        mountain_index.append(
            {
                "boundary_name": mountain_name,
                "boundary_type": "mountain",
                "has_cbi": bool(has_cbi),
                "cbi_status": "computed" if has_cbi else "no_valid_window",
                "primary_side_width_km": primary_width,
                "boundary_file": boundary_file,
                "window_file": f"mountain_windows/windows/{file_name}.geojson",
                "segment_file": f"mountain_windows/segments/{file_name}.geojson",
                "point_file": point_file,
                "n_windows": int(n_windows),
                "n_segments": int(n_segments),
                "n_place_points": int(n_points),
            }
        )

        log(
            f"{mountain_name} 导出完成：主侧宽 {primary_width:g} km，"
            f"窗口 {n_windows} 个，连续段 {n_segments} 个，地名点 {n_points} 个，"
            f"has_cbi={has_cbi}。"
        )

    summary_records = dataframe_to_records(summary_df)
    side_width_records = dataframe_to_records(side_width_df) if len(side_width_df) else []
    mountain_system_records = (
        dataframe_to_records(mountain_system_df)
        if len(mountain_system_df) else []
    )
    window_records = dataframe_to_records(window_df)
    segment_records = dataframe_to_records(segment_df)

    write_json(WEB_DATA_DIR / "mountain_summary.json", summary_records)
    write_json(WEB_DATA_DIR / "mountain_side_width_summary.json", side_width_records)
    write_json(WEB_DATA_DIR / "mountain_system_summary.json", mountain_system_records)
    write_json(WEB_DATA_DIR / "mountain_windows_table.json", window_records)
    write_json(WEB_DATA_DIR / "mountain_segments_table.json", segment_records)
    write_json(
        WEB_DATA_DIR / "mountain_window_index.json",
        {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "description": "06b mountain moving-window CBI static data for GitHub Pages.",
            "mountains": mountain_index,
            "formula": {
                "mountain_CBI": (
                    "0.30*mean_reliable_local_CBI_norm + "
                    "0.25*p90_reliable_local_CBI_norm + "
                    "0.20*high_CBI_coverage_ratio + "
                    "0.10*candidate_coverage_ratio + "
                    "0.10*contrast_segment_ratio + "
                    "0.05*reliable_coverage_ratio"
                ),
                "local_signal_CBI": (
                    "0.45*mean_reliable_local_CBI_norm + "
                    "0.35*p90_reliable_local_CBI_norm + "
                    "0.10*high_CBI_window_ratio + "
                    "0.10*candidate_window_ratio"
                ),
            },
        }
    )

    log("全部 06b 网页静态数据导出完成。")


if __name__ == "__main__":
    export_mountain_window_data()
