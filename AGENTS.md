# literature-review-skill - 项目指令

本项目是一个面向系统文献综述生成的 Skill 仓库。核心形态不是通用 Python 包，而是：

- 根目录 `SKILL.md` 定义 AI 执行工作流
- `scripts/` 提供检索、去重、评分、选文、校验、导出等脚本
- `config.yaml` 提供档位、检索、缓存、写作和校验配置
- `examples/` 保存实际产物示例
- `references/` 保存提示词、写作规范和补充说明

代理在本仓库中工作时，默认目标应是：维护 Skill 说明、修复或增强流水线脚本、改进配置与文档一致性，而不是引入额外框架或重构成新工程形态。

## 默认语言

除非用户明确要求其他语言，始终使用简体中文交流、注释和文档说明。

## 任务判断

遇到以下请求时，优先按对应方式处理：

- 用户要“写系统综述 / 文献综述 / related work / 文献调研”：
  这是本仓库核心用途，应遵循根目录 [SKILL.md](/Users/wukai/source_codes/literature-review-skill/SKILL.md) 的工作流和约束。
- 用户要“修改流水线/修复脚本/调整配置”：
  直接在 `scripts/`、`config.yaml`、`README.md`、`SKILL.md` 中最小化修改。
- 用户要“评估论文、生成审稿意见、总结论文”：
  优先使用本环境已安装的相关 skill，并让输出风格与本仓库的学术场景一致。
- 用户只是问“这个仓库怎么用”：
  优先引用 [README.md](/Users/wukai/source_codes/literature-review-skill/README.md) 与 [SKILL.md](/Users/wukai/source_codes/literature-review-skill/SKILL.md)，不要重复制造第二套使用说明。

## 核心目录

- [SKILL.md](/Users/wukai/source_codes/literature-review-skill/SKILL.md)：AI 执行规范、阶段流程、输出契约
- [README.md](/Users/wukai/source_codes/literature-review-skill/README.md)：面向用户的使用指南
- [config.yaml](/Users/wukai/source_codes/literature-review-skill/config.yaml)：单一配置入口
- [scripts/](/Users/wukai/source_codes/literature-review-skill/scripts)：流水线脚本
- [references/](/Users/wukai/source_codes/literature-review-skill/references)：提示词、校验标准、写作参考
- [examples/](/Users/wukai/source_codes/literature-review-skill/examples)：真实输出示例
- [latex-template/](/Users/wukai/source_codes/literature-review-skill/latex-template)：LaTeX 模板与 `.bst`

## 工作方式

### 1. 先读配置和现有流程，再改代码

本仓库很多行为受 `config.yaml` 驱动。修改脚本前，先确认：

- 该行为是否已有配置项
- 该脚本是否已被 `pipeline_runner.py` 或 `run_pipeline.py` 调用
- 该改动是否会影响 `examples/` 中既有输出格式

如果可以通过配置解决，不要硬编码新分支。

### 2. 保持流水线阶段语义稳定

主流程以 [scripts/pipeline_runner.py](/Users/wukai/source_codes/literature-review-skill/scripts/pipeline_runner.py) 为中心，关键阶段包括：

- `0_setup`
- `1_search`
- `2_dedupe`
- `3_score`
- `4_select`
- `4.5_word_budget`
- `5_write`
- `6_validate`
- `7_export`

修改时尽量保持：

- 阶段名称稳定
- 输出文件名和目录结构稳定
- 中断恢复语义稳定

除非用户明确要求，否则不要随意改 run 目录产物命名。

### 3. 区分“仓库文件”和“运行产物”

通常应修改仓库源码与文档，不应顺手编辑某次运行产物。

优先修改：

- `scripts/*.py`
- `config.yaml`
- `README.md`
- `SKILL.md`
- `references/*.md`

谨慎修改：

- `examples/` 下示例文件，除非用户要求更新示例
- `runs/` 或用户指定工作目录下的生成文件，这些通常是执行结果，不是源码

## 常用命令

### 环境与基础检查

```bash
python3 --version
python3 -m py_compile scripts/*.py
```

### 运行主流水线

```bash
python3 scripts/pipeline_runner.py --topic "主题" --work-dir runs/主题
```

### 常见单项脚本

```bash
python3 scripts/validate_review_tex.py --help
python3 scripts/validate_counts.py --help
python3 scripts/plan_word_budget.py --help
python3 scripts/compile_latex_with_bibtex.py --help
python3 scripts/convert_latex_to_word.py --help
```

如果只是修改单个脚本，优先做与该脚本直接相关的最小验证，不要每次都跑完整流水线。

## 修改原则

- 优先最小改动，避免无关重构。
- 优先复用现有脚本和工具函数，不重复造轮子。
- 新增配置时，必须同步更新 `README.md` 或 `SKILL.md` 中对应说明。
- 新增脚本时，命名风格保持现有仓库一致：小写加下划线。
- 保持 UTF-8 文本兼容，但无必要不要引入花哨 Unicode。
- 涉及 BibTeX、LaTeX、引用 key、文件名时，优先保持现有兼容策略，不要想当然“清理”格式。

## 文档约束

`README.md` 与 `SKILL.md` 分工明确：

- `README.md` 面向用户，解释怎么触发、怎么使用、有哪些示例
- `SKILL.md` 面向代理，解释该怎么执行、遵守哪些硬约束

修改文档时不要混写：

- 不要把大量版本历史塞进 `SKILL.md`
- 不要把 AI 内部执行细节过度堆进 `README.md`

## 验证要求

完成修改后，至少做下列之一，并在回复中说明实际执行了什么：

- 对改动脚本执行 `python3 -m py_compile`
- 对目标脚本运行 `--help`
- 对相关模块做一次最小输入验证
- 若涉及完整流程，再运行一次对应 pipeline 命令

如果因为环境缺少外部依赖、API 密钥或 LaTeX 工具链而无法验证，需要明确说明阻塞点。

## 禁止事项

- 不要把这个仓库重构成 Web 服务、包管理项目或前后端项目，除非用户明确要求。
- 不要在未确认的情况下批量改写 `examples/` 产物。
- 不要修改输出契约后不更新文档。
- 不要为了“更现代”而替换现有稳定脚本接口。
- 不要把 AI 流程元信息写进综述正文；正文应只讨论学术内容，这一点需与 [SKILL.md](/Users/wukai/source_codes/literature-review-skill/SKILL.md) 保持一致。

## 回复风格

向用户汇报时优先说明：

- 改了什么
- 为什么这样改
- 验证做到哪一步
- 是否存在未验证风险

保持简洁、直接、可执行。
