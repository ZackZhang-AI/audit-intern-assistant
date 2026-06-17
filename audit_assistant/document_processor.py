from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, BinaryIO, Mapping

from .models import DocumentSuggestion


UNKNOWN = "待补充"


def analyze_document_text(
    original_filename: str,
    text: str,
    llm_fields: Mapping[str, Any] | None = None,
) -> DocumentSuggestion:
    normalized_text = _normalize_text(text)
    rule_document_type = _classify_document(normalized_text)
    document_type = _field(llm_fields, "document_type") or rule_document_type
    audit_cycle = _field(llm_fields, "audit_cycle") or _audit_cycle_for(document_type, normalized_text)
    counterparty = _field(llm_fields, "counterparty") or _extract_counterparty(document_type, normalized_text)
    date = _field(llm_fields, "date") or _extract_date(normalized_text)
    amount = _amount_field(llm_fields) if llm_fields and "amount" in llm_fields else _extract_amount(normalized_text)
    document_number = _field(llm_fields, "document_number") or _extract_document_number(document_type, normalized_text)
    suggested_folder = _suggest_folder(document_type, audit_cycle)
    suggested_filename = _suggest_filename(
        original_filename=original_filename,
        document_type=document_type,
        counterparty=counterparty,
        date=date,
        amount=amount,
    )
    confidence, review_note = _score_and_note(document_type, counterparty, date, amount)

    return DocumentSuggestion(
        original_filename=original_filename,
        document_type=document_type,
        audit_cycle=audit_cycle,
        counterparty=counterparty,
        date=date,
        amount=amount,
        document_number=document_number,
        suggested_filename=suggested_filename,
        suggested_folder=suggested_folder,
        confidence=confidence,
        review_note=review_note,
        extracted_text=normalized_text,
    )


def extract_text_from_file(file: BinaryIO, filename: str) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if hasattr(file, "seek"):
        file.seek(0)
    data = file.read()

    if suffix == ".txt":
        return _decode_text(data), ""
    if suffix == ".pdf":
        return _extract_pdf_text(data), ""
    if suffix in {".png", ".jpg", ".jpeg"}:
        return _extract_image_text(data), ""

    return "", "暂不支持该文件格式，请上传 PDF、PNG、JPG 或 TXT。"


def analyze_uploaded_file(file: BinaryIO, filename: str, use_llm: bool = False) -> DocumentSuggestion:
    text, warning = extract_text_from_file(file, filename)
    if warning:
        text = warning
    llm_fields = {}
    if use_llm and not warning:
        from .llm_extractor import extract_fields_with_openai

        llm_fields = extract_fields_with_openai(filename, text)
    result = analyze_document_text(filename, text, llm_fields=llm_fields)
    if warning:
        return DocumentSuggestion(
            **{
                **result.to_dict(),
                "confidence": 0.0,
                "review_note": warning,
                "extracted_text": text,
            }
        )
    return result


def _field(fields: Mapping[str, Any] | None, key: str) -> str:
    if not fields:
        return ""
    value = fields.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _amount_field(fields: Mapping[str, Any]) -> int | float | None:
    value = fields.get("amount")
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value).replace(",", ""))
    except InvalidOperation:
        return None
    if decimal_value == decimal_value.to_integral_value():
        return int(decimal_value)
    return float(decimal_value)


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", str(text or "")).strip()


def _classify_document(text: str) -> str:
    if any(keyword in text for keyword in ["银行回单", "电子回单", "付款方", "收款方"]):
        return "银行回单"
    if any(keyword in text for keyword in ["发票", "价税合计", "开票日期", "发票号码"]):
        return "发票"
    if "采购合同" in text:
        return "采购合同"
    if "销售合同" in text:
        return "销售合同"
    if "合同" in text:
        return "合同"
    if any(keyword in text for keyword in ["明细账", "序时账", "凭证号", "科目余额"]):
        return "明细账"
    return "未知资料"


def _audit_cycle_for(document_type: str, text: str) -> str:
    if document_type == "银行回单":
        return "货币资金循环"
    if document_type == "销售合同":
        return "销售与收款循环"
    if document_type in {"采购合同", "合同"}:
        if any(keyword in text for keyword in ["销货", "收入", "客户"]):
            return "销售与收款循环"
        return "采购与付款循环"
    if document_type == "发票":
        return "采购与付款循环"
    if document_type == "明细账":
        return "总账与报表循环"
    return "待人工分类"


def _extract_counterparty(document_type: str, text: str) -> str:
    label_groups = {
        "银行回单": ["付款方", "付款人", "付款账户名称", "对方户名"],
        "发票": ["销售方", "销货方", "购买方", "交易对方"],
        "采购合同": ["乙方", "供应商", "供方", "交易对方"],
        "销售合同": ["甲方", "客户", "需方", "交易对方"],
        "合同": ["乙方", "甲方", "供应商", "客户", "交易对方"],
    }
    labels = label_groups.get(document_type, ["交易对方", "供应商", "客户"])
    for label in labels:
        value = _extract_labeled_value(text, label)
        if value:
            return _clean_party(value)
    return ""


def _extract_date(text: str) -> str:
    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", text)
    if not match:
        return ""
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def _extract_amount(text: str) -> int | float | None:
    patterns = [
        r"(?:合同金额|价税合计|合计金额|交易金额|金额)[:：]?\s*(?:人民币|￥|CNY|RMB)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        r"(?:人民币|￥|CNY|RMB)\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1).replace(",", "")
        try:
            value = Decimal(raw)
        except InvalidOperation:
            continue
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return None


def _extract_document_number(document_type: str, text: str) -> str:
    labels = ["合同编号", "发票号码", "回单编号", "凭证号", "单据编号"]
    for label in labels:
        value = _extract_labeled_value(text, label)
        if value:
            return re.sub(r"\s+", "", value)
    return ""


def _suggest_folder(document_type: str, audit_cycle: str) -> str:
    folder_by_type = {
        "采购合同": "合同资料",
        "销售合同": "合同资料",
        "合同": "合同资料",
        "发票": "发票资料",
        "银行回单": "银行回单",
        "明细账": "明细账",
    }
    folder = folder_by_type.get(document_type, "待人工复核")
    return f"{audit_cycle}/{folder}/"


def _suggest_filename(
    original_filename: str,
    document_type: str,
    counterparty: str,
    date: str,
    amount: int | float | None,
) -> str:
    year = date[:4] if date else "未知年度"
    party = counterparty or "交易对方待补"
    amount_text = _format_amount(amount) if amount is not None else "金额待补"
    suffix = Path(original_filename).suffix.lower() or ".pdf"
    parts = [year, document_type, party, amount_text]
    return "_".join(_safe_filename_part(part) for part in parts) + suffix


def _score_and_note(
    document_type: str,
    counterparty: str,
    date: str,
    amount: int | float | None,
) -> tuple[float, str]:
    checks = [
        document_type != "未知资料",
        bool(counterparty),
        bool(date),
        amount is not None,
    ]
    confidence = round(sum(checks) / len(checks), 2)
    if confidence >= 0.8:
        return confidence, "识别结果较完整，建议抽样复核后采用。"

    missing = []
    if document_type == "未知资料":
        missing.append("文件类型")
    if not counterparty:
        missing.append("交易对方")
    if not date:
        missing.append("日期")
    if amount is None:
        missing.append("金额")
    return confidence, f"需人工复核：{', '.join(missing)} 未识别。"


def _extract_labeled_value(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*[:：]\s*([^\n\r，,；;]+)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _clean_party(value: str) -> str:
    value = re.sub(r"\s+", "", value)
    value = re.split(r"(?:纳税人识别号|账号|开户行|金额|日期)", value)[0]
    return value.strip("：:，,；; ")


def _safe_filename_part(value: object) -> str:
    text = str(value or UNKNOWN).strip()
    text = re.sub(r'[\\/:*?"<>|]', "", text)
    text = re.sub(r"\s+", "", text)
    return text or UNKNOWN


def _format_amount(amount: int | float) -> str:
    if isinstance(amount, float) and not amount.is_integer():
        return f"金额{amount:.2f}".rstrip("0").rstrip(".")
    return f"金额{int(amount)}"


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "PDF 解析依赖 pypdf 未安装，请先安装 requirements.txt。"

    from io import BytesIO

    reader = PdfReader(BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extract_image_text(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "图片 OCR 依赖 pillow/pytesseract 未安装；可先使用 TXT 样例演示识别流程。"

    from io import BytesIO

    image = Image.open(BytesIO(data))
    return pytesseract.image_to_string(image, lang="chi_sim+eng").strip()
