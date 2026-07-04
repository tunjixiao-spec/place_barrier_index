# 山脉移动窗口 CBI 静态查询系统

这是一个可以部署到 GitHub Pages 的纯静态网页系统。

它不会运行 Flask、FastAPI、GeoPandas 或任何 Python 后端。网页只读取已经导出的 `JSON / GeoJSON` 文件，在浏览器中完成山脉名称查询、CBI 指标展示和地图可视化。

## 1. 先生成 06b 分析结果

在项目根目录运行：

```bash
python scripts/06b_mountain_moving_window_cbi.py
```

如果你使用 `placename` 环境，可以运行：

```bash
C:\Anaconda3\envs\placename\python.exe scripts\06b_mountain_moving_window_cbi.py
```

这一步会生成：

```text
output/tables/06b_mountain_moving_window_cbi/mountain_local_cbi_windows.csv
output/tables/06b_mountain_moving_window_cbi/mountain_community_differentiation_segments.csv
output/tables/06b_mountain_moving_window_cbi/mountain_cultural_boundary_strength.csv
output/tables/06b_mountain_moving_window_cbi/mountain_side_width_summary.csv
```

## 2. 导出 GitHub Pages 静态数据

继续在项目根目录运行：

```bash
python scripts/09_export_mountain_window_web_data.py
```

或：

```bash
C:\Anaconda3\envs\placename\python.exe scripts\09_export_mountain_window_web_data.py
```

脚本会把 06b 结果转换成网页可直接读取的数据：

```text
web/data/mountain_windows/mountain_window_index.json
web/data/mountain_windows/mountain_summary.json
web/data/mountain_windows/mountain_side_width_summary.json
web/data/mountain_windows/mountain_windows_table.json
web/data/mountain_windows/mountain_segments_table.json
web/data/mountain_windows/boundaries/{山脉名}.geojson
web/data/mountain_windows/windows/{山脉名}.geojson
web/data/mountain_windows/segments/{山脉名}.geojson
```

## 3. 本地预览

不要直接双击 `index.html`，因为浏览器可能禁止 `file://` 读取 JSON。

推荐在 `web/` 目录启动静态服务器：

```bash
cd web
python -m http.server 8000
```

然后访问：

```text
http://localhost:8000
```

## 4. 网页功能

用户可以在页面中手动输入山脉名称。系统会索引 `data/raw/mountain_ranges_140.shp` 中的全部唯一山脉名称。

当前 raw shp 中 140 条记录会按名称合并为若干唯一山脉；网页按唯一山脉名查询。

示例：

```text
秦岭
横断山
武夷山
太行山
大庾岭
```

点击查询后，网页会显示：

- `mountain_CBI`
- `mountain_CBI_level`
- `local_signal_CBI`
- `primary_side_width_km`
- `reliable_coverage_ratio`
- `high_CBI_coverage_ratio`
- `contrast_segment_ratio`
- `evidence_quality`

如果某条山脉已经运行过 06b，则网页会返回 CBI 指标和移动窗口 CBI 可视化。

如果某条山脉存在于 raw 山脉 shp，但由于两侧样本不足或可靠窗口不足而没有形成有效 06b 窗口，则网页仍会显示：

- 山脉线；
- 山脉两侧地名点；
- 地名点弹窗；
- “样本不足 / 无有效窗口”的提示。

网页不会强行给这类山脉填一个 `mountain_CBI` 数值，以免把低证据区域误读为可靠文化分隔。

地图会显示：

- 山脉线；
- 不同移动窗口的 CBI 彩色线段；
- 地名文化社区分异连续段；
- 该山脉侧宽范围内的地名特征点；
- 点击窗口可查看该窗口的 `CBI`、`small_CBI`、`big_CBI`、点数、clip 风险；
- 点击连续段可查看 `segment_local_CBI_mean` 和主导社区。
- 点击地名点可查看 `raw_name`、`clean_name`、`name_body`、`char`、`small_feature`、`big_feature`、`community_id`、`side` 和 `dist_m`。

图表会显示：

- 沿山脉 station 的 local_CBI 曲线；
- small_CBI / big_CBI 对比；
- 不同侧宽的敏感性结果；
- 分异连续段 CBI 对比。

## 5. GitHub Pages 部署

本项目已经配置了 GitHub Actions：

```text
.github/workflows/deploy-pages.yml
```

该工作流会把 `web/` 目录作为 GitHub Pages 的发布目录。这样不需要把 `web/` 复制到 `docs/`，也不需要购买服务器。

在 PyCharm 中推荐这样操作：

1. 打开项目根目录 `place_barrier_index`；
2. 确认已经运行 06b 和 09，且 `web/data/mountain_windows/` 已经生成；
3. 在 PyCharm 左侧 Git 工具窗口中勾选这些内容：
   - `.github/workflows/deploy-pages.yml`
   - `web/`
   - `scripts/06b_mountain_moving_window_cbi.py`
   - `scripts/09_export_mountain_window_web_data.py`
4. Commit 信息可写：

```text
Add GitHub Pages static CBI viewer
```

5. 点击 Commit and Push。

如果使用命令行，则是：

```bash
git add .github/workflows/deploy-pages.yml scripts/06b_mountain_moving_window_cbi.py scripts/09_export_mountain_window_web_data.py web
git commit -m "Add GitHub Pages static CBI viewer"
git push
```

然后进入 GitHub 仓库：

```text
Settings -> Pages
```

在 `Build and deployment` 中：

```text
Source -> GitHub Actions
```

保存后，进入：

```text
Actions -> Deploy static web to GitHub Pages
```

等待工作流变成绿色成功状态。部署完成后，回到：

```text
Settings -> Pages
```

点击 `Visit site` 即可打开网页。

注意：GitHub 官方的“从分支发布”通常只能选择仓库根目录 `/` 或 `/docs`，不能直接选择 `/web`。因此本项目采用 GitHub Actions 发布 `web/` 目录。

第一次部署可能需要几分钟。如果页面仍是旧内容，可以等待 1-10 分钟后强制刷新浏览器。

## 6. 不需要服务器

这个系统是纯静态网站：

- 不需要购买服务器；
- 不需要申请域名；
- 不需要 Flask；
- 不需要 FastAPI；
- 不需要数据库；
- 不需要让本地电脑一直开着。

GitHub Pages 只负责托管静态文件。浏览器负责读取 JSON / GeoJSON 并完成查询和可视化。

## 7. 限制说明

GitHub Pages 不能实时运行 GeoPandas，也不能重新计算 CBI。

正确流程是：

```text
Python 项目中完成分析
    -> 运行 06b 生成结果 CSV
    -> 运行 09 导出 JSON / GeoJSON
    -> GitHub Pages 展示和查询
```

如果数据或参数更新，需要重新运行 06b 和 09，然后把新的 `web/data/` 推送到 GitHub。
