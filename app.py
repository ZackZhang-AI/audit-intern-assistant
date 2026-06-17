from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from audit_assistant.document_processor import analyze_document_text, analyze_uploaded_file
from audit_assistant.excel_checks import run_excel_detail_checks
from audit_assistant.exporter import suggestions_to_dataframe, to_excel_bytes
from audit_assistant.workpaper import generate_workpaper_description


SAMPLE_DOCUMENTS = Path("sample_data/sample_documents.csv")


st.set_page_config(
    page_title="审计资料智能归档与底稿辅助生成系统",
    layout="wide",
)

st.title("审计资料智能归档与底稿辅助生成系统")
st.caption("上传客户资料后生成标准化命名和分类建议；工具只给出建议，不会自动修改或移动原文件。")

tab_archive, tab_excel, tab_workpaper = st.tabs(
    ["资料智能命名归档", "Excel 明细异常检查", "访谈/底稿描述生成"]
)


@st.cache_data
def load_sample_documents() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_DOCUMENTS)


with tab_archive:
    st.subheader("资料智能命名归档")
    st.write("适用于合同、发票、银行回单、明细账截图等审计资料的初步整理。")

    col_upload, col_sample = st.columns([2, 1])
    with col_upload:
        uploaded_files = st.file_uploader(
            "批量上传 PDF、图片或 TXT 样例",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            accept_multiple_files=True,
        )
    with col_sample:
        use_samples = st.toggle("使用内置脱敏样例", value=not uploaded_files)
        use_llm = st.toggle(
            "启用可选 LLM 抽取",
            value=False,
            help="需要设置 OPENAI_API_KEY；未启用时使用本地规则抽取。",
        )

    suggestions = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            suggestions.append(analyze_uploaded_file(uploaded_file, uploaded_file.name, use_llm=use_llm))
    elif use_samples:
        for row in load_sample_documents().to_dict("records"):
            suggestions.append(analyze_document_text(row["original_filename"], row["text"]))

    if not suggestions:
        st.info("请上传文件，或打开内置样例开关查看演示结果。")
    else:
        result_frame = suggestions_to_dataframe(suggestions)

        metrics = st.columns(4)
        metrics[0].metric("处理文件数", len(result_frame))
        metrics[1].metric("需复核", int((result_frame["confidence"] < 0.8).sum()))
        metrics[2].metric("识别类型数", result_frame["document_type"].nunique())
        metrics[3].metric("平均置信度", f"{result_frame['confidence'].mean():.0%}")

        st.dataframe(result_frame, use_container_width=True, hide_index=True)
        st.download_button(
            "导出归档建议 Excel",
            data=to_excel_bytes(result_frame),
            file_name="audit_archive_suggestions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        with st.expander("查看 OCR/文本抽取片段"):
            for suggestion in suggestions:
                st.markdown(f"**{suggestion.original_filename}**")
                st.code(suggestion.extracted_text[:1200] or "未抽取到文本", language="text")


with tab_excel:
    st.subheader("Excel 明细异常检查")
    st.write("扩展模块：对明细账或抽样清单执行基础规则检查，辅助定位负数金额、重复记录、字段缺失和日期异常。")

    excel_file = st.file_uploader(
        "上传 CSV / XLSX / XLS 明细文件",
        type=["csv", "xlsx", "xls"],
        key="excel_file",
    )

    if excel_file is None:
        detail_frame = pd.DataFrame(
            [
                {"voucher_no": "PZ-001", "counterparty": "供应商A", "amount": 128000, "transaction_date": "2024-03-15"},
                {"voucher_no": "PZ-001", "counterparty": "供应商A", "amount": 128000, "transaction_date": "2024-03-15"},
                {"voucher_no": "PZ-002", "counterparty": "", "amount": -500, "transaction_date": "not-a-date"},
            ]
        )
        st.caption("未上传文件时展示内置明细样例。")
    elif excel_file.name.lower().endswith(".csv"):
        detail_frame = pd.read_csv(excel_file)
    else:
        detail_frame = pd.read_excel(excel_file)

    st.dataframe(detail_frame, use_container_width=True, hide_index=True)
    findings = run_excel_detail_checks(detail_frame)
    if findings.empty:
        st.success("未发现当前规则覆盖的异常。")
    else:
        st.warning(f"发现 {len(findings)} 条异常，请结合原始凭证复核。")
        st.dataframe(findings, use_container_width=True, hide_index=True)
        st.download_button(
            "导出异常检查结果 CSV",
            data=findings.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
            file_name="excel_detail_findings.csv",
            mime="text/csv",
            use_container_width=True,
        )


with tab_workpaper:
    st.subheader("访谈/底稿描述结构化生成")
    st.write("扩展模块：把零散访谈记录整理成底稿描述框架，便于后续人工补证和复核。")

    topic = st.text_input("访谈或底稿主题", value="采购合同归档流程访谈")
    audit_cycle = st.selectbox(
        "涉及审计循环",
        ["采购与付款循环", "销售与收款循环", "货币资金循环", "总账与报表循环", "待分类循环"],
    )
    notes = st.text_area(
        "粘贴访谈记录或底稿草稿",
        value="客户财务每月从采购系统导出合同清单，由实习生按供应商和月份整理。金额超过10万元的合同需要主管复核。",
        height=160,
    )

    generated = generate_workpaper_description(topic, notes, audit_cycle)
    st.text_area("结构化底稿描述", value=generated, height=340)
