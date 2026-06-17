from io import BytesIO

import pandas as pd

from audit_assistant.document_processor import analyze_document_text
from audit_assistant.exporter import EXPORT_COLUMNS, suggestions_to_dataframe, to_excel_bytes


def test_contract_text_generates_standard_name_and_folder():
    text = """
    采购合同
    甲方：杭州云帆科技有限公司
    乙方：上海明远供应链有限公司
    合同金额：人民币128000元
    签订日期：2024年3月15日
    合同编号：CG-2024-0315
    """

    result = analyze_document_text("扫描件1.pdf", text)

    assert result.document_type == "采购合同"
    assert result.audit_cycle == "采购与付款循环"
    assert result.counterparty == "上海明远供应链有限公司"
    assert result.amount == 128000
    assert result.date == "2024-03-15"
    assert result.suggested_filename == "2024_采购合同_上海明远供应链有限公司_金额128000.pdf"
    assert result.suggested_folder == "采购与付款循环/合同资料/"
    assert result.confidence >= 0.8


def test_bank_receipt_uses_payer_for_naming():
    text = """
    中国工商银行电子回单
    付款方：浙江星河贸易有限公司
    收款方：杭州云帆科技有限公司
    金额：￥56000.00
    交易日期：2024-05-20
    回单编号：BK20240520001
    """

    result = analyze_document_text("微信图片.jpg", text)

    assert result.document_type == "银行回单"
    assert result.audit_cycle == "货币资金循环"
    assert result.counterparty == "浙江星河贸易有限公司"
    assert result.suggested_filename == "2024_银行回单_浙江星河贸易有限公司_金额56000.jpg"
    assert result.suggested_folder == "货币资金循环/银行回单/"


def test_missing_fields_are_marked_for_manual_review():
    result = analyze_document_text("附件3.png", "合同 文件扫描不清，仅可识别少量文字")

    assert result.document_type == "合同"
    assert result.confidence < 0.8
    assert "需人工复核" in result.review_note
    assert "附件3.png" not in result.suggested_filename


def test_llm_fields_can_override_rule_extraction():
    result = analyze_document_text(
        "unknown.pdf",
        "扫描件文字质量较差",
        llm_fields={
            "document_type": "采购合同",
            "audit_cycle": "采购与付款循环",
            "counterparty": "供应商A",
            "date": "2024-06-01",
            "amount": 90000,
            "document_number": "CG-001",
        },
    )

    assert result.document_type == "采购合同"
    assert result.counterparty == "供应商A"
    assert result.suggested_filename == "2024_采购合同_供应商A_金额90000.pdf"
    assert result.confidence >= 0.8


def test_suggestions_export_columns_and_excel_bytes_are_stable():
    suggestion = analyze_document_text(
        "invoice.png",
        "增值税专用发票 销售方：上海明远供应链有限公司 价税合计：128000元 开票日期：2024-03-16 发票号码：12345678",
    )

    frame = suggestions_to_dataframe([suggestion])
    excel_bytes = to_excel_bytes(frame)

    assert list(frame.columns) == EXPORT_COLUMNS
    assert frame.loc[0, "original_filename"] == "invoice.png"
    assert frame.loc[0, "suggested_folder"] == "采购与付款循环/发票资料/"
    assert excel_bytes.startswith(b"PK")
    loaded = pd.read_excel(BytesIO(excel_bytes))
    assert loaded.loc[0, "suggested_filename"] == suggestion.suggested_filename
