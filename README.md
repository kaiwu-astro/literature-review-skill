# Systematic Literature Review（相关性驱动版）— 用户使用指南

本 README 面向**使用者**：如何触发并正确使用 `systematic-literature-review` skill。执行指令与硬性规范在 `SKILL.md`；默认参数在 `config.yaml`。

> 天文/天体物理推荐检索源：**NASA ADS + arXiv (astro-ph)**，并可与 OpenAlex/Crossref 联用。

## 快速开始

(可选：在终端中设置环境变量 `ADS_API_TOKEN=your_nasa_ads_api_token` ，来启用ADS检索，否则会使用OpenAlex)

### 最小可用
```
请用 systematic-literature-review 做主题"Fast radio bursts: origins and mechanisms"的文献综述，基础级，近五年英文。
```

### 指定输出范围
```
请做"Transformer 在金融风控中的应用"综述，旗舰级，正文 12000-14000 字，参考文献 100-130 篇。
```

### 明确写作风格
```
请做"癌症免疫检查点抑制剂疗效预测生物标志物"的综述，旗舰级，字数范围默认，写作风格偏 Nature Reviews，子主题由你自动决定。
```

### 校验不够时的有机扩写
```
请在 {子主题名} 段内有机扩写，保持原主张和引用不变，只补充 2–3 条具体证据/数字/反例与衔接句；本段目标约 {目标字数} 字，当前不足 {差额} 字。原文如下：{原段落全文}
```

### 按预算写作（含无引用段落）
```
请读取 runs/{safe_topic}/.systematic-literature-review/artifacts/word_budget_final.csv，引用段按每篇文献的“综/述”字数预算写，无引用段（文献ID为空，如摘要/结论/展望）按该行预算控制长度；可合并引用但需贴近预算总字数。
```

### 多语言

```
请用 systematic-literature-review 做"Transformer in NLP"的德语综述，标准级。
```

### 更多例子
查看 [examples/](examples/) 目录，包含本 skill 实际生成的专家级综述示例，可参考输出格式和质量标准。

## 档位选择指南

| 档位 | 字数范围 | 参考文献数 | 典型场景 | PDF 页数 | 别名 |
|------|---------|-----------|---------|---------|------|
| **Premium（旗舰级）** | 10000–15000 | 80–150 | • *Annual Review of Astronomy and Astrophysics* 级别综述<br>• *Nature Astronomy* 级别综述<br>• 专著式综述 | 16–25 页 | 旗舰级、顶刊级、高级 |
| **Standard（标准级）** | 6000–10000 | 50–90 | • 学位论文 Related Work<br>• 普通期刊综述<br>• NSFC 标书立项依据<br>• 项目提案 | 10–16 页 | 标准级、常规 |
| **Basic（基础级）** | 3000–6000 | 30–60 | • 快速调研<br>• 课程作业<br>• 会议论文 Related Work<br>• 入门了解领域 | 5–10 页 | 快速级、基础级、入门 |


## 设计理念
- AI 自定检索词 → 去重 → 标题/摘要 1–10 分相关性与子主题自动分组 → 高分优先选文 → **自动生成"综/述"字数预算（70% 引用段 + 30% 无引用段，3 次采样均值，空 ID 行支持无引用大纲）** → 资深领域专家自由写作。
- 档位仅影响默认字数/参考范围（可覆盖），支持三档：**Premium（旗舰级）**、**Standard（标准级）**、**Basic（基础级）**。
- 强制导出 PDF/Word；硬校验：必需章节、字数 min/max、参考文献数 min/max、\cite 与 bib 对齐；可选校验字数预算覆盖率/总和。
- **最高原则**：AI 不得偷懒或短视地为了速度做错误事；不确定必须说明；最终润色仅做衔接与结构调整，不得改动文献题目/摘要所含事实/数字。
- **稳健性**：恢复状态时校验 `papers` 路径；Bib 自动转义 `&`、补充缺失字段并大小写无关去重 key；模板/`.bst` 缺失会自动回退同步。
- **多语言支持**：支持将综述翻译为多种语言（en/zh/ja/de/fr/es），自动修复 LaTeX 渲染错误，保留引用和结构不变。详见[多语言支持](#多语言支持)。


# 开发者
## 运行与校验
- 自动流程：`python scripts/pipeline_runner.py --topic "主题" --work-dir runs/主题`  
  阶段：`0_setup → 0.5_subtopics（写作前由 AI 给出并记录） → 1_search → 2_dedupe → 3_score → 4_select → 4.5_word_budget → 5_write → 6_validate（含有机扩写与可选预算校验） → 7_export`
- 校验：`validate_counts.py`（字数/引用 min/max）、`validate_review_tex.py`（必需章节 + cite/bib 对齐）
- 导出：`compile_latex_with_bibtex.py {topic}_review.tex {topic}_review.pdf`；`convert_latex_to_word.py ...`；如需自定义模板可在 `config.yaml.latex.template_path_override` 或 CLI `--template` 指定路径（缺失会回退到内置模板并同步 `.bst`）。

## 关键文件
- `SKILL.md`：工作流、输入输出、最高原则与硬校验
- `config.yaml`：档位字数/参考范围、高分优先比例、搜索默认参数
- `scripts/score_relevance.py`：子主题自动分组 + 1–10 分
- `scripts/select_references.py`：按高分优先比例和目标数量选文，生成 Bib
- `scripts/plan_word_budget.py`：三次采样生成字数预算 run1/2/3 + final（含无引用空 ID 行）
- `scripts/validate_word_budget.py`：可选校验预算列/覆盖率/总和
- `scripts/update_working_conditions_data_extraction.py`：记录 score/subtopic 到数据抽取表

## 测试（离线）

本仓库已引入 `pytest` 作为正式测试框架，并采用分层目录：

- `tests/unit/`：纯函数/规则测试
- `tests/cli/`：CLI 参数与退出码契约测试
- `tests/integration/`：离线脚本链路联调测试
- `tests/fixtures/`：固定测试输入样本

建议本地最小回归命令：

```bash
python3 -m py_compile scripts/*.py
pytest -q tests/unit tests/cli
```
