# Olist 电商课程项目

正式提交只使用 `提交/Olist课程项目提交材料.zip`。按任务书第九部分，包内有七个一级项目：

1. 数据质量分析报告.docx
2. 数据质量分析报告.pdf
3. 数据分析报告.docx
4. 数据分析报告.pdf
5. 分析代码/（含README、依赖、配置、必要字体和复现入口）
6. 数据说明.md（来源、获取方式和45个字段说明）
7. 分工与贡献说明.md（四人各25%，真实提交与本人确认由组员补齐）

报告采用中蓝色 #28648A 与浅蓝阶，中文 Noto Serif CJK SC，英文数字 Times New Roman。质量报告24页、分析报告26页；已核对本机WPS与PDF页数及章起始页。

## 本机工作文件

- reports/：唯一保留的中蓝版报告、当前图表与汇总证据。
- analysis/、scripts/、sql/、configs/、assets/：当前分析及报告生成源码和依赖资源。
- data/ 与 data.zip：本机原始资料和分析数据库，不进入提交包。
- frontend/、backend/、deliverables/：之前完成的选做展示系统与当前展示输出，留在本机，不混入必交材料。
- docs/、tests/：内部说明和核验代码，不单独作为提交物发送。

## 正式报告复现

取得同批七个SQL文件放入data/raw，安装requirements.txt后运行：

```sh
.venv/bin/python scripts/reproduce_reports.py
```

该入口重算两报告的全部数字与22幅PNG/SVG，原始SQL只读。需要重建Word时安装requirements-documents.txt，并加 `--documents`；PDF重建环境和运行顺序见提交包内分析代码/README.md。

重新生成精简提交包：

```sh
.venv/bin/python scripts/pack_course_delivery.py
```

选做展示仍可用 `启动Web展示.command` 启动。原有 `scripts/reproduce.py --from-raw` 是包含选做展示的完整本机流程。

正式提交的Windows与macOS运行命令、数字/Word/PDF三种复现范围、固定研究设计和可调阈值，统一见 docs/报告复现说明.md。脚本打包时将该文档作为分析代码/README.md。
