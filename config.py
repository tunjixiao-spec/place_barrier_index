from pathlib import Path

# ============================================================
# 1. 项目根目录
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# 2. 项目内部目录
# ============================================================

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

OUTPUT_DIR = BASE_DIR / "output"
TABLE_DIR = OUTPUT_DIR / "tables"
MAP_DIR = OUTPUT_DIR / "maps"
FIGURE_DIR = OUTPUT_DIR / "figures"


# ============================================================
# 2.1 按源码文件分类的输出目录
# ============================================================
# 说明：
# 1. TABLE_DIR / MAP_DIR / FIGURE_DIR 仍然是总目录；
# 2. 具体输出文件按生成它的源码脚本进入对应子目录；
# 3. 这样便于检查每个脚本产生了哪些表、图层和图件。

# 表格输出目录
TABLE_01_DIR = TABLE_DIR / "01_name_cleaning"
TABLE_02_DIR = TABLE_DIR / "02_feature_selection"
TABLE_04_DIR = TABLE_DIR / "04_clq_louvain_communities"
TABLE_05_DIR = TABLE_DIR / "05_detect_feature_patches"
TABLE_06_DIR = TABLE_DIR / "06_barrier_index_by_communities"
TABLE_06B_DIR = TABLE_DIR / "06b_mountain_moving_window_cbi"
TABLE_07_DIR = TABLE_DIR / "07_plot_results"
TABLE_CALCULATE_CLQ_DIR = TABLE_DIR / "calculate_clq_parameters"
TABLE_DIAG_DIR = TABLE_DIR / "diagnostics"

# 地图 / 空间数据输出目录
MAP_04_DIR = MAP_DIR / "04_clq_louvain_communities"
MAP_05_DIR = MAP_DIR / "05_detect_feature_patches"
MAP_06B_DIR = MAP_DIR / "06b_mountain_moving_window_cbi"

# 图表输出目录
FIGURE_04_DIR = FIGURE_DIR / "04_clq_louvain_communities"
FIGURE_06_DIR = FIGURE_DIR / "06_barrier_index_by_communities"
FIGURE_06B_DIR = FIGURE_DIR / "06b_mountain_moving_window_cbi"
FIGURE_07_DIR = FIGURE_DIR / "07_plot_results"


# ============================================================
# 3. 原始村级点数据
# ============================================================

PLACE_SHP = RAW_DIR / "全国村点_wgs84_2023.shp"

NAME_FIELD = "村"
FULL_NAME_FIELD = "全名"
URBAN_RURAL_FIELD = "其他信"


# ============================================================
# 4. 山脉、河流数据
# ============================================================

MOUNTAIN_SHP = RAW_DIR / "mountain_ranges_140.shp"
RIVER_SHP = RAW_DIR / "rivers.shp"

MOUNTAIN_NAMES = ["秦岭", "大庾岭", "太行山", "横断山", "武夷山"]

# 当前论文主分析对象收束为山脉。
# 河流具有阻隔与连通双重作用，暂不纳入核心计算。
# 后续如果要恢复河流分析，可以改回：
# RIVER_NAMES = ["长江", "黄河", "淮河"]
RIVER_NAMES = []


# ============================================================
# 5. 坐标系统
# ============================================================

ALBERS_CHINA = (
    "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 "
    "+lon_0=105 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
)


# ============================================================
# 6. 研究范围
# ============================================================
# all_place_names：
#     主分析模式。
#     保留全部地名点，不默认剔除社区、居委会、居民委员会。
#
# all：
#     与 all_place_names 等价，保留全部记录。
#
# rural_village：
#     仅用于对照实验。
#     保留城乡分类代码以 2 开头或名称含“村”的记录，同时剔除社区、居委会。
#
# admin_village_only：
#     仅用于对照实验。
#     只保留名称含“村”的记录，同时剔除社区、居委会。

ANALYSIS_SCOPE = "all_place_names"


# ============================================================
# 7. 第一阶段：地名清洗、字频统计、通名统计
# ============================================================

CLEAN_NAMES_CSV = TABLE_01_DIR / "clean_names.csv"

# 统计 name_body 中单字频率
CHAR_STATS_CSV = TABLE_02_DIR / "char_stats.csv"

# 统计识别出的地理—文化通名频率
TOPONYM_STATS_CSV = TABLE_02_DIR / "toponym_stats.csv"

# 特征字筛选结果
SELECTED_CHARS_CSV = TABLE_02_DIR / "selected_chars.csv"

# 地理—文化通名筛选结果
SELECTED_TOPONYMS_CSV = TABLE_02_DIR / "selected_toponyms.csv"

# 诊断输出
DEBUG_NAME_BODY_CONTAINS_ADMIN_CSV = TABLE_DIAG_DIR / "debug_name_body_contains_admin_chars.csv"


# ============================================================
# 8. 第二阶段：特征字点集与文化社区
# ============================================================

FEATURE_POINTS_GPKG = MAP_04_DIR / "feature_points.gpkg"

CLQ_PAIRS_CSV = TABLE_04_DIR / "clq_pairs.csv"
STRONG_CLQ_PAIRS_CSV = TABLE_04_DIR / "strong_clq_pairs.csv"

CHAR_COMMUNITIES_CSV = TABLE_04_DIR / "char_communities.csv"
COMMUNITY_SUMMARY_CSV = TABLE_04_DIR / "community_summary.csv"

CHAR_POINTS_COMMUNITY_GPKG = MAP_04_DIR / "char_points_community.gpkg"


# ============================================================
# 9. 第三阶段：斑块识别与空间连续验证
# ============================================================

FEATURE_PATCHES_GPKG = MAP_05_DIR / "feature_patches.gpkg"
FEATURE_POINTS_PATCHED_GPKG = MAP_05_DIR / "feature_points_patched.gpkg"


# ============================================================
# 10. 第四阶段：山川 / 河流分隔指数
# ============================================================

BARRIER_BY_THRESHOLD_CSV = TABLE_06_DIR / "barrier_metrics_by_threshold.csv"
BARRIER_SUMMARY_CSV = TABLE_06_DIR / "barrier_metrics_summary.csv"


# ============================================================
# 11. 山脉、河流字段检查输出
# ============================================================

BOUNDARY_NAME_CHECK_CSV = TABLE_DIAG_DIR / "boundary_name_check.csv"


# ============================================================
# 12. 图表输出
# ============================================================

CBI_RANKING_PNG = FIGURE_07_DIR / "cbi_ranking.png"
CBI_MULTISCALE_PNG = FIGURE_07_DIR / "cbi_multiscale_curve.png"
CLQ_NETWORK_PNG = FIGURE_04_DIR / "clq_network.png"


# ============================================================
# 13. name_body 特征字筛选参数
# ============================================================
# 注意：
# 当前主分析对象是 name_body 中的单字。
# name_body = 剥离行政性通名后的地名主体。
#
# 例：
# 东湖村     -> name_body = 东湖
# 白马寺村   -> name_body = 白马寺
# 李家寨村   -> name_body = 李家寨
# 石桥社区   -> name_body = 石桥

NAME_BODY_CUM_THRESHOLD = 0.65
MIN_NAME_BODY_PLACES = 300

# 低频但有文化意义的特征字白名单
NAME_BODY_WHITE_LIST = "濮骅彝侗苗勐钤昱澧隅仡佬泃瑶赭僳傈裕鮀溱睢瀍"

# 行政性、机构性字不进入 CLQ + Louvain
ADMIN_EXCLUDE_CHARS = "村社区居委会组"


# ============================================================
# 14. 地理—文化通名筛选参数
# ============================================================

TOPONYM_CUM_THRESHOLD = 0.90
MIN_TOPONYM_PLACES = 100

# 低频但地域文化意义强的地理—文化通名白名单
TOPONYM_WHITE_LIST = "夼滘岙冲疃塬崮寮厝咀圩墟砦垸塆"

# 高频但语义歧义较强的通名
AMBIGUOUS_TOPONYMS = "里口头台场店铺厂园林家"


# ============================================================
# 15. 语义大类约束
# ============================================================

CORE_SEMANTIC_TYPES = [
    "民族文化类",
    "民族音译类",
    "水文环境类",
    "山地地貌类",
    "聚落形态类",
    "交通商贸类",
    "宗教建筑类",
    "地域通名类"
]

NON_CORE_SEMANTIC_TYPES = [
    "序数编号类",
    "方位规模类",
    "姓氏人名类",
    "吉祥人文类",
    "行政组织类",
    "高歧义类",
    "其他待定类"
]


# ============================================================
# 16. CLQ 与 Louvain 参数
# ============================================================
# 说明：
# CLQ 参数采用“一次自动校准 + 自动写回 config.py + 后续锁定使用”的机制。
#
# 第一次运行时：
#     如果 CLQ_PARAMS_LOCKED = False，
#     config.py 会调用 calculate_clq_parameters.py 自动计算 CLQ 参数；
#     计算完成后，会把参数自动写回本文件的 CLQ_LOCKED_PARAMS 区域；
#     同时把 CLQ_PARAMS_LOCKED 自动改为 True。
#
# 后续运行时：
#     如果 CLQ_PARAMS_LOCKED = True，
#     所有脚本都会直接使用 CLQ_LOCKED_PARAMS 中已经写回的参数；
#     不再重复调用 calculate_clq_parameters.py；
#     因此 05、06、07 等脚本运行时不会再反复计算 CLQ 参数。
#
# 如果以后重新生成 feature_points.gpkg，或者修改了特征字筛选规则、
# semantic_type 分类、core_for_clq、CLQ 参数校准逻辑，
# 只需要把 CLQ_PARAMS_LOCKED 手动改回 False，
# 再运行一次脚本，它会重新计算并再次自动写回。

CLQ_K_CANDIDATES = [5, 8, 10, 12, 15, 20]
CLQ_CALIBRATION_RANDOM_SEED = 42

CLQ_FEATURE_COUNT_REPORT_CSV = TABLE_CALCULATE_CLQ_DIR / "clq_feature_count_report.csv"
CLQ_K_STABILITY_REPORT_CSV = TABLE_CALCULATE_CLQ_DIR / "clq_k_stability_report.csv"
CLQ_THRESHOLD_REPORT_CSV = TABLE_CALCULATE_CLQ_DIR / "clq_threshold_report.csv"
CLQ_CALIBRATION_PAIRS_CSV = TABLE_CALCULATE_CLQ_DIR / "clq_calibration_pairs_selected_k.csv"

# 是否允许自动校准。
# 一般保持 True，不需要反复手动调整。
# 真正控制是否重新计算的是下面的 CLQ_PARAMS_LOCKED。
CLQ_AUTO_CALIBRATE = True

# 是否把自动校准结果写回 config.py。
# 建议保持 True。
CLQ_AUTO_WRITEBACK = True

# 默认参数。
# 只有在 feature_points.gpkg 不存在，或 CLQ_AUTO_CALIBRATE = False 时才会使用。
CLQ_DEFAULT_PARAMS = {
    "CLQ_K": 10,
    "CLQ_MIN_PLACES": 1,
    "CLQ_MAX_PLACES": 10**12,
    "CLQ_MAX_POINTS_PER_FEATURE": 3000,
    "CLQ_EDGE_THRESHOLD": 1.35,
    "CLQ_RECIPROCAL_MIN": 1.0,
    "CLQ_MIN_PAIR_COUNT": 1,
    "CLQ_MIN_EDGES_PER_GROUP": 0,
    "CLQ_MAX_EDGES_PER_GROUP": 10**12,
    "CLQ_MAX_EDGES_PER_NODE": 10**12
}


# ============================================================
# CLQ 参数锁定区
# ============================================================
# 注意：
# 下面两个标记不要删除：
#     # --- CLQ_LOCKED_PARAMS_START ---
#     # --- CLQ_LOCKED_PARAMS_END ---
# 自动写回函数会根据这两个标记定位并替换中间内容。

# --- CLQ_LOCKED_PARAMS_START ---
CLQ_PARAMS_LOCKED = True

CLQ_LOCKED_PARAMS = {
    "CLQ_K": 8,
    "CLQ_MIN_PLACES": 1,
    "CLQ_MAX_PLACES": 47443,
    "CLQ_MAX_POINTS_PER_FEATURE": 23027,
    "CLQ_EDGE_THRESHOLD": 1.1911884040166774,
    "CLQ_RECIPROCAL_MIN": 1.0,
    "CLQ_MIN_PAIR_COUNT": 13087,
    "CLQ_MIN_EDGES_PER_GROUP": 0,
    "CLQ_MAX_EDGES_PER_GROUP": 78,
    "CLQ_MAX_EDGES_PER_NODE": 12
}
# --- CLQ_LOCKED_PARAMS_END ---


def write_clq_params_back_to_config(params):
    """
    将自动校准得到的 CLQ 参数写回 config.py。

    写回后：
        1. CLQ_PARAMS_LOCKED 会变成 True；
        2. CLQ_LOCKED_PARAMS 会变成当前自动校准得到的参数；
        3. 后续脚本再次 import config.py 时，会直接使用锁定参数；
        4. 不再重复执行 calculate_clq_parameters.py。

    同时会生成一个 config.py.bak 备份文件。
    如果备份文件已经存在，则不会反复覆盖。
    """
    import re
    import pprint

    config_path = Path(__file__).resolve()
    old_text = config_path.read_text(encoding="utf-8")

    # 明确哪些参数应写成 int，哪些应写成 float。
    int_keys = {
        "CLQ_K",
        "CLQ_MIN_PLACES",
        "CLQ_MAX_PLACES",
        "CLQ_MAX_POINTS_PER_FEATURE",
        "CLQ_MIN_PAIR_COUNT",
        "CLQ_MIN_EDGES_PER_GROUP",
        "CLQ_MAX_EDGES_PER_GROUP",
        "CLQ_MAX_EDGES_PER_NODE"
    }

    float_keys = {
        "CLQ_EDGE_THRESHOLD",
        "CLQ_RECIPROCAL_MIN"
    }

    ordered_keys = [
        "CLQ_K",
        "CLQ_MIN_PLACES",
        "CLQ_MAX_PLACES",
        "CLQ_MAX_POINTS_PER_FEATURE",
        "CLQ_EDGE_THRESHOLD",
        "CLQ_RECIPROCAL_MIN",
        "CLQ_MIN_PAIR_COUNT",
        "CLQ_MIN_EDGES_PER_GROUP",
        "CLQ_MAX_EDGES_PER_GROUP",
        "CLQ_MAX_EDGES_PER_NODE"
    ]

    clean_params = {}

    for key in ordered_keys:
        value = params[key]

        if key in int_keys:
            clean_params[key] = int(value)
        elif key in float_keys:
            clean_params[key] = float(value)
        else:
            clean_params[key] = value

    params_text = pprint.pformat(
        clean_params,
        sort_dicts=False,
        width=120
    )

    new_block = (
        "# --- CLQ_LOCKED_PARAMS_START ---\n"
        "CLQ_PARAMS_LOCKED = True\n\n"
        f"CLQ_LOCKED_PARAMS = {params_text}\n"
        "# --- CLQ_LOCKED_PARAMS_END ---"
    )

    pattern = (
        r"# --- CLQ_LOCKED_PARAMS_START ---"
        r".*?"
        r"# --- CLQ_LOCKED_PARAMS_END ---"
    )

    new_text, n_replaced = re.subn(
        pattern,
        new_block,
        old_text,
        flags=re.S
    )

    if n_replaced == 0:
        print("警告：没有找到 CLQ_LOCKED_PARAMS 写回区域，未能写回 config.py。")
        return

    backup_path = config_path.with_suffix(".py.bak")

    if not backup_path.exists():
        backup_path.write_text(old_text, encoding="utf-8")

    config_path.write_text(new_text, encoding="utf-8")

    print("CLQ 参数已自动写回 config.py。")
    print("CLQ_PARAMS_LOCKED 已自动改为 True。")
    print("后续运行将直接使用 CLQ_LOCKED_PARAMS，不再重复校准。")


def load_clq_params_from_python():
    """
    读取或自动校准 CLQ 参数。

    运行逻辑：

    1. 如果 CLQ_PARAMS_LOCKED = True：
        说明 CLQ 参数已经写回 config.py；
        直接返回 CLQ_LOCKED_PARAMS；
        不再调用 calculate_clq_parameters.py。

    2. 如果 CLQ_PARAMS_LOCKED = False：
        说明参数尚未锁定；
        如果 feature_points.gpkg 已存在，
        则调用 calculate_clq_parameters.py 自动校准参数。

    3. 如果 CLQ_AUTO_WRITEBACK = True：
        自动把本次校准结果写回 config.py；
        并把 CLQ_PARAMS_LOCKED 改为 True。
    """
    if CLQ_PARAMS_LOCKED:
        print("使用 config.py 中已锁定的 CLQ 参数。")
        return CLQ_LOCKED_PARAMS.copy()

    if not CLQ_AUTO_CALIBRATE:
        print("CLQ_AUTO_CALIBRATE = False，使用 CLQ_DEFAULT_PARAMS。")
        return CLQ_DEFAULT_PARAMS.copy()

    if not FEATURE_POINTS_GPKG.exists():
        print("警告：尚未找到 feature_points.gpkg，CLQ 参数暂用默认值。")
        return CLQ_DEFAULT_PARAMS.copy()

    print("CLQ 参数尚未锁定，开始自动校准。")

    from calculate_clq_parameters import get_calibrated_clq_params

    params = get_calibrated_clq_params(
        feature_points_path=FEATURE_POINTS_GPKG,
        k_candidates=CLQ_K_CANDIDATES,
        random_seed=CLQ_CALIBRATION_RANDOM_SEED,
        feature_count_report_csv=CLQ_FEATURE_COUNT_REPORT_CSV,
        k_stability_report_csv=CLQ_K_STABILITY_REPORT_CSV,
        threshold_report_csv=CLQ_THRESHOLD_REPORT_CSV,
        calibration_pairs_csv=CLQ_CALIBRATION_PAIRS_CSV
    )

    if CLQ_AUTO_WRITEBACK:
        write_clq_params_back_to_config(params)

    return params


_CLQ_PARAMS = load_clq_params_from_python()

CLQ_K = int(_CLQ_PARAMS["CLQ_K"])

CLQ_MIN_PLACES = int(_CLQ_PARAMS["CLQ_MIN_PLACES"])
CLQ_MAX_PLACES = int(_CLQ_PARAMS["CLQ_MAX_PLACES"])
CLQ_MAX_POINTS_PER_FEATURE = int(_CLQ_PARAMS["CLQ_MAX_POINTS_PER_FEATURE"])

CLQ_EDGE_THRESHOLD = float(_CLQ_PARAMS["CLQ_EDGE_THRESHOLD"])
CLQ_RECIPROCAL_MIN = float(_CLQ_PARAMS["CLQ_RECIPROCAL_MIN"])
CLQ_MIN_PAIR_COUNT = int(_CLQ_PARAMS["CLQ_MIN_PAIR_COUNT"])

CLQ_MIN_EDGES_PER_GROUP = int(_CLQ_PARAMS["CLQ_MIN_EDGES_PER_GROUP"])
CLQ_MAX_EDGES_PER_GROUP = int(_CLQ_PARAMS["CLQ_MAX_EDGES_PER_GROUP"])
CLQ_MAX_EDGES_PER_NODE = int(_CLQ_PARAMS["CLQ_MAX_EDGES_PER_NODE"])

INCLUDE_SINGLETON_COMMUNITIES = True
PLOT_NETWORK_MAX_EDGES = 200

# 说明：
# clq_network_strict.png：
#     使用自然断点自动校准后的正式 CLQ 参数。
#     表示高可信核心共现网络。
#
# clq_network_display.png：
#     使用较宽松的展示参数。
#     只用于展示更丰富的共现关系，不参与 Louvain 社区识别。
#
# community_spatial_distribution.png：
#     根据 char_points_community.gpkg 绘制 community_id 空间分布图。
#     用于展示文化社区在地理空间上的分布。

CLQ_NETWORK_STRICT_PNG = FIGURE_04_DIR / "clq_network_strict.png"
CLQ_NETWORK_DISPLAY_PNG = FIGURE_04_DIR / "clq_network_display.png"

# 为兼容旧文件名，clq_network.png 仍然输出一份高可信 strict 网络图
CLQ_NETWORK_PNG = FIGURE_04_DIR / "clq_network.png"

# 保存 CLQ 边表，方便后续检查为什么图边多或边少
CLQ_EDGES_ALL_CSV = TABLE_04_DIR / "clq_edges_all.csv"
CLQ_EDGES_STRICT_CSV = TABLE_04_DIR / "clq_edges_strict.csv"
CLQ_EDGES_DISPLAY_CSV = TABLE_04_DIR / "clq_edges_display.csv"

# 展示型 CLQ 网络图参数
# 注意：这些参数只用于 clq_network_display.png
# 不参与正式 Louvain 社区划分，不改变 community_id。
CLQ_DISPLAY_EDGE_THRESHOLD = 1.00
CLQ_DISPLAY_RECIPROCAL_MIN = 0.0
CLQ_DISPLAY_MIN_PAIR_COUNT = 30
CLQ_DISPLAY_MAX_EDGES = 1000
CLQ_DISPLAY_MAX_EDGES_PER_NODE = 40

# 文化社区空间分布图输出路径
COMMUNITY_SPATIAL_DISTRIBUTION_PNG = FIGURE_04_DIR / "community_spatial_distribution.png"

# 空间图最多绘制多少点，防止点太多导致图过慢
COMMUNITY_MAP_MAX_POINTS = 120000

# 空间图显示点数最多的多少个社区，其余社区合并为 Other
COMMUNITY_MAP_TOP_N_COMMUNITIES = 20


# ============================================================
# 17. NNI + HDBSCAN 斑块参数
# ============================================================

PATCH_MIN_POINTS = 30
PATCH_MIN_CLUSTER_RATIO = 0.05
PATCH_MAX_POINTS_PER_FEATURE = 30000
PATCH_CORE_ONLY = True


# ============================================================
# 18. 山川分隔评价参数
# ============================================================

THRESHOLDS_KM = [20, 50, 100, 150]
MIN_POINTS_EACH_SIDE = 30

SMALL_CLASS_WEIGHT = 0.7
BIG_CLASS_WEIGHT = 0.3


# ============================================================
# 18.1 山脉移动窗口 local_CBI 与 mountain_CBI 参数
# ============================================================
# 这一部分对应 scripts/06b_mountain_moving_window_cbi.py。
#
# 概念说明：
# 1. local_CBI：
#       移动窗口尺度的地名文化社区差异指数。
#
# 2. valid_contrast_window：
#       有效“地名文化社区分异窗口”。
#       它不是直接等同于文化分隔窗口，而是表示：
#       该窗口内山脉 A/B 两侧地名文化社区结构存在较明显差异。
#
# 3. community differentiation segment：
#       地名文化社区分异连续段。
#       它是连续多个 valid_contrast_window 合并后的局部连续差异段。
#       注意：它不是最终意义上的“文化分隔段”。
#
# 4. mountain_CBI：
#       山脉尺度文化分隔强度综合指数。
#       该指标综合可靠窗口 local_CBI、候选窗口比例、高 CBI 窗口比例、
#       社区分异连续段长度占比等，用于判断一条山脉整体文化分隔作用。
#
# 重要原则：
#     n_contrast_segments = 0 不代表该山脉没有文化分隔作用；
#     它只表示没有识别出满足连续合并条件的社区分异连续段。
#     判断山脉文化分隔强度应优先看 mountain_CBI。


# ------------------------------------------------------------
# 18.1.1 移动窗口尺度参数
# ------------------------------------------------------------

# 沿山脉方向每隔多少 km 设置一个移动窗口中心点
LOCAL_WINDOW_STEP_KM = 20

# 每个移动窗口沿山脉方向的长度
# 100 km 表示窗口中心前后各 50 km
LOCAL_WINDOW_LENGTH_KM = 100

# 山脉两侧宽度，单位 km
# 当前主分析先用 50 km；后续敏感性分析可以改为 [20, 50, 100]
LOCAL_SIDE_WIDTHS_KM = [50]

# 单侧最少地名点数量。
# A/B 两侧都达到该数量，reliable_window 才为 True。
LOCAL_MIN_POINTS_EACH_SIDE = 30


# ------------------------------------------------------------
# 18.1.2 地名文化社区差异窗口判定参数
# ------------------------------------------------------------

# 一侧主导 community_id 的最低占比。
# dominance_ok 只作为解释字段，不作为 mountain_CBI 的硬条件。
# 不宜设太高，因为地名文化社区在局部窗口内通常是混合结构。
LOCAL_DOMINANT_SHARE_MIN = 0.20

# local_CBI 分级后，至少达到第几级才算高 CBI / 有效社区分异窗口。
# 4 级分类时：
#     1 = 很弱
#     2 = 弱
#     3 = 较强
#     4 = 强
#
# 注意：
# 如果设为 3，筛选更严格；
# 如果设为 2，更适合探索山脉整体文化分隔强度。
# 当前为了不漏掉太行山、横断山等山脉的整体分隔作用，建议先用 2。
LOCAL_VALID_MIN_CBI_LEVEL = 2


# ------------------------------------------------------------
# 18.1.3 地名文化社区分异连续段合并参数
# ------------------------------------------------------------

# 至少连续多少个有效社区分异窗口，才能合并为一个社区分异连续段
LOCAL_MIN_CONSECUTIVE_WINDOWS = 2

# 社区分异连续段最小长度，单位 km
LOCAL_MIN_SEGMENT_LENGTH_KM = 40

# 相邻窗口 Top3 community_id 的 Jaccard 相似度阈值
# 当前脚本中相邻窗口只要求 A/B 至少一侧相似，因此这里不宜过高。
LOCAL_TOP3_JACCARD_MIN = 0.2


# ------------------------------------------------------------
# 18.1.4 投影 clip 诊断参数
# ------------------------------------------------------------

# 只有 clip 导致 station_m 改变超过该阈值，才认为是“有效 clip 影响”
# 单位：米
LOCAL_EFFECTIVE_CLIP_OFFSET_M = 1000

# 如果 clip 导致窗口点集合变化比例超过该值，
# 则该窗口不作为有效社区分异窗口。
#
# 0.05 = 严格
# 0.10 = 适中
# 0.15 = 宽松
LOCAL_MAX_WINDOW_MEMBERSHIP_CHANGE_RATIO = 0.10


# ------------------------------------------------------------
# 18.1.5 06b 输出文件
# ------------------------------------------------------------

# 移动窗口 local_CBI 结果。
# 每一行对应一个山脉移动窗口。
LOCAL_CBI_WINDOWS_CSV = TABLE_06B_DIR / "mountain_local_cbi_windows.csv"

# 地名文化社区分异连续段结果。
# 注意：这个不是最终文化分隔段，而是连续社区差异段。
COMMUNITY_DIFF_SEGMENTS_CSV = (
    TABLE_06B_DIR / "mountain_community_differentiation_segments.csv"
)

# 山脉尺度文化分隔强度结果。
# 这个文件才用于判断哪条山脉文化分隔作用更强。
MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV = (
    TABLE_06B_DIR / "mountain_cultural_boundary_strength.csv"
)


# ------------------------------------------------------------
# 18.1.6 兼容旧脚本的输出路径别名
# ------------------------------------------------------------
# 旧版 06b 脚本曾使用下面两个变量名。
# 为了避免其他脚本或旧代码引用时报错，这里保留别名。
# 新论文解释中应优先使用：
#     COMMUNITY_DIFF_SEGMENTS_CSV
#     MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV

LOCAL_CBI_SEGMENTS_CSV = COMMUNITY_DIFF_SEGMENTS_CSV
LOCAL_CBI_MOUNTAIN_SUMMARY_CSV = MOUNTAIN_CULTURAL_BOUNDARY_STRENGTH_CSV


# ============================================================
# 19. 社区解释备用输出
# ============================================================

COMMUNITY_LABEL_TEMPLATE_CSV = TABLE_04_DIR / "community_label_template.csv"
CHAR_POINTS_COMMUNITY_LABELED_GPKG = MAP_04_DIR / "char_points_community_labeled.gpkg"
CHAR_POINTS_FOR_BARRIER_GPKG = MAP_04_DIR / "char_points_for_barrier.gpkg"


# ============================================================
# 20. ArcGIS 兼容导出
# ============================================================

ARCGIS_EXPORT_DIR = MAP_DIR / "arcgis_export"


# ============================================================
# 21. 自动创建文件夹
# ============================================================

for p in [
    RAW_DIR,
    OUTPUT_DIR,
    TABLE_DIR,
    MAP_DIR,
    FIGURE_DIR,

    TABLE_01_DIR,
    TABLE_02_DIR,
    TABLE_04_DIR,
    TABLE_05_DIR,
    TABLE_06_DIR,
    TABLE_06B_DIR,
    TABLE_07_DIR,
    TABLE_CALCULATE_CLQ_DIR,
    TABLE_DIAG_DIR,

    MAP_04_DIR,
    MAP_05_DIR,
    MAP_06B_DIR,

    FIGURE_04_DIR,
    FIGURE_06_DIR,
    FIGURE_06B_DIR,
    FIGURE_07_DIR,

    ARCGIS_EXPORT_DIR,
]:
    p.mkdir(parents=True, exist_ok=True)