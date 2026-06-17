# 审计资料智能归档与底稿辅助生成系统

这是一个面向审计实习场景的本地提效工具。项目聚焦客户资料文件名混乱、资料分类不统一、底稿描述整理耗时的问题，支持上传资料后生成标准化命名、分类路径和人工复核提示。

## 项目亮点

- 用 Streamlit 搭建可演示的审计资料整理工作台。
- 支持合同、发票、银行回单、明细账等资料的内容识别和字段抽取。
- 根据审计循环生成标准化命名和归档路径建议。
- 保留人工复核环节，不直接修改或移动原始文件，更贴合审计资料整理流程。
- 提供 Excel 明细异常检查和访谈/底稿描述结构化生成两个扩展模块。

## 功能模块

### 1. 审计资料智能命名与归档

支持批量上传 PDF、PNG、JPG、TXT 文件，从文本或 OCR 结果中抽取：

- 文件类型
- 审计循环
- 交易对方
- 日期
- 金额
- 合同编号、发票号码、回单编号等单据编号

输出示例：

```text
原文件：扫描件1.pdf
建议命名：2024_采购合同_上海明远供应链有限公司_金额128000.pdf
分类路径：采购与付款循环/合同资料/
```

系统会生成置信度和复核提示，识别不完整时标记“需人工复核”。

### 2. Excel 明细异常检查

用于对明细账或抽样清单进行基础规则检查，目前覆盖：

- 负数金额
- 重复明细
- 交易对方缺失
- 日期格式异常

检查结果包含规则编号、风险等级、异常证据和复核建议。

### 3. 访谈/底稿描述结构化生成

将零散访谈记录整理为底稿描述框架，输出：

- 访谈主题
- 涉及审计循环
- 已了解事项
- 初步审计关注点
- 后续资料需求

## 技术栈

- Python
- Streamlit
- pandas / openpyxl
- pypdf
- pytesseract / pillow
- OpenAI SDK，可选
- pytest

## 快速开始

```bash
pip install -r requirements.txt
streamlit run app.py
```

打开页面后，可以直接使用内置脱敏样例演示，也可以上传自己的测试文件。

## OCR 说明

- TXT 和内置样例不依赖 OCR，适合稳定演示。
- PDF 文本抽取依赖 `pypdf`。
- 图片 OCR 依赖 `pillow`、`pytesseract` 和本机 Tesseract OCR 引擎。
- 如果本机没有安装 Tesseract，图片上传仍会给出人工复核提示，不会导致页面崩溃。

## 可选 LLM 抽取

默认演示路径使用本地规则抽取，保证无网络和无 API key 时也能运行。若需要启用大模型结构化抽取，可以设置环境变量：

```bash
set OPENAI_API_KEY=你的密钥
set OPENAI_MODEL=gpt-4.1-mini
streamlit run app.py
```

页面中打开“启用可选 LLM 抽取”后，工具会将 OCR 文本发送给模型，并要求模型返回固定 JSON 字段；本地规则仍作为兜底。

## 输出字段

归档建议表包含：

```text
original_filename, document_type, audit_cycle, counterparty,
date, amount, document_number, suggested_filename,
suggested_folder, confidence, review_note
```

## 项目结构

```text
.
├── app.py
├── audit_assistant/
│   ├── document_processor.py
│   ├── excel_checks.py
│   ├── exporter.py
│   ├── llm_extractor.py
│   ├── models.py
│   └── workpaper.py
├── sample_data/
│   └── sample_documents.csv
├── tests/
│   ├── test_document_processor.py
│   ├── test_excel_checks.py
│   ├── test_llm_extractor.py
│   └── test_workpaper.py
├── requirements.txt
└── README.md
```

## 测试

```bash
python -m pytest -q
```

测试覆盖：

- 合同资料字段抽取与命名规则
- 银行回单分类与命名规则
- 字段缺失时的人工复核提示
- 可选 LLM 提示词与 JSON 解析
- 归档建议 Excel 导出
- Excel 明细异常检查
- 访谈/底稿描述结构化生成

## 简历写法

针对审计实习中客户资料命名混乱、归档效率低的问题，设计并实现审计资料智能归档与底稿辅助生成系统，支持合同、发票、银行回单等文件的内容识别、字段抽取和标准化命名建议。

基于 Python、OCR 与 LLM 结构化抽取构建资料整理流程，自动提取交易对方、金额、日期、文件类型等关键信息，并按审计循环生成分类路径；同时设计 Excel 明细异常检查和底稿描述生成模块，辅助提升审计资料整理、检索和底稿编写效率。
