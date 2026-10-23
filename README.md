# Olist 巴西电商数据分析与可视化

基于 Olist 历史交易数据，分析订单分布、区域与品类结构、配送时效、评价和客户回访。项目包含数据质量报告、数据分析报告、22 幅分析图，以及可离线使用的交互展示。

样本包含 99,441 笔订单，来自订单、客户、商品明细、产品、卖家、支付和评价七张表。商品金额合计为 BRL 13,591,643.70，不含运费，不代表净收入；研究结论仅适用于本数据集。

## 查看成果

- [数据质量报告](reports/Olist数据质量分析报告_中蓝版.pdf)
- [数据分析报告](reports/Olist数据分析报告_中蓝版.pdf)
- [交互展示](deliverables/olist_visual_report.html)：下载后用浏览器打开，视频、字体和图表资源已内嵌。
- [交互研究图谱](deliverables/analysis/analysis_report.html)：下载后可离线查看。

报告同时提供可编辑的 Word 版本。GitHub 文件预览不执行 HTML，查看交互效果请先下载文件。

## 运行

使用 Python 3.14，在项目根目录执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

浏览器访问 http://127.0.0.1:8780/ 。macOS 也可双击 `启动Web展示.command`。Windows 使用 `.venv\Scripts\python.exe` 替换上面的 Python 路径。

## 复现分析

按[数据说明](docs/数据说明.md)取得七个 SQL 文件并放入 `data/raw/`，然后运行：

```sh
.venv/bin/python scripts/reproduce_reports.py
```

该命令重算报告数字、汇总证据和 22 幅图。需要重建 Word 时，安装 `requirements-documents.txt` 后添加 `--documents`。PDF 导出方法、指标定义和参数说明见[报告复现说明](docs/报告复现说明.md)。

原始 SQL、数据库和评价正文不随仓库分发。订单查询页面 `/workbench` 需要先运行 `sql/import_to_sqlite.py` 和 `analysis/pipeline.py` 生成本地数据库。

## 目录

- `analysis/`：清洗、关联校验、统计分析和绘图。
- `scripts/`：报告生成、展示构建、复现和核验。
- `backend/`、`frontend/`：本地服务与查询页面。
- `reports/`：正式报告、汇总证据和图表。
- `deliverables/`：离线展示文件。
- `tests/`：金额对账、样本口径、报告和接口测试。
- `configs/`、`assets/`：分析参数、地图、字体和图表资源。

数据来源、统计限制和辅助工具使用情况见报告及其附录。中文字体随附开源许可。
