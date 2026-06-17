from __future__ import annotations

from typing import Any

import pandas as pd


FINDING_COLUMNS = [
    "rule_id",
    "rule_name",
    "risk_level",
    "record_index",
    "field",
    "evidence",
    "recommendation",
]

COLUMN_ALIASES = {
    "凭证号": "voucher_no",
    "单据编号": "voucher_no",
    "交易对方": "counterparty",
    "供应商": "counterparty",
    "客户": "counterparty",
    "金额": "amount",
    "发生额": "amount",
    "交易日期": "transaction_date",
    "日期": "transaction_date",
}


def run_excel_detail_checks(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_columns(df)
    findings: list[dict[str, Any]] = []

    duplicate_mask = normalized.duplicated(
        subset=["voucher_no", "counterparty", "amount", "transaction_date"],
        keep=False,
    )

    for index, row in normalized.iterrows():
        amount = row.get("amount")
        counterparty = _text(row.get("counterparty"))
        transaction_date = row.get("transaction_date")

        if pd.notna(amount) and amount < 0:
            findings.append(
                _finding(
                    "E001",
                    "负数金额",
                    "High",
                    index,
                    "amount",
                    f"金额为 {amount}",
                    "复核该笔交易是否为冲销、红字或录入错误。",
                )
            )

        if bool(duplicate_mask.loc[index]):
            findings.append(
                _finding(
                    "E002",
                    "重复明细",
                    "Medium",
                    index,
                    "voucher_no",
                    "凭证号、交易对方、金额、日期完全重复。",
                    "检查是否存在重复导出、重复入账或重复抽样。",
                )
            )

        if not counterparty:
            findings.append(
                _finding(
                    "E003",
                    "交易对方缺失",
                    "Low",
                    index,
                    "counterparty",
                    "交易对方为空。",
                    "补充供应商或客户名称后再归档底稿。",
                )
            )

        if pd.isna(transaction_date):
            findings.append(
                _finding(
                    "E004",
                    "日期格式异常",
                    "Low",
                    index,
                    "transaction_date",
                    "交易日期为空或无法解析。",
                    "核对原始明细账日期列格式。",
                )
            )

    if not findings:
        return pd.DataFrame(columns=FINDING_COLUMNS)
    return pd.DataFrame(findings, columns=FINDING_COLUMNS)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for column in df.columns:
        cleaned = str(column).strip()
        rename_map[column] = COLUMN_ALIASES.get(cleaned, cleaned)

    normalized = df.rename(columns=rename_map).copy()
    for column in ["voucher_no", "counterparty", "amount", "transaction_date"]:
        if column not in normalized.columns:
            normalized[column] = pd.NA

    normalized["amount"] = pd.to_numeric(normalized["amount"], errors="coerce")
    normalized["transaction_date"] = pd.to_datetime(
        normalized["transaction_date"],
        errors="coerce",
    )
    return normalized[["voucher_no", "counterparty", "amount", "transaction_date"]]


def _finding(
    rule_id: str,
    rule_name: str,
    risk_level: str,
    record_index: int,
    field: str,
    evidence: str,
    recommendation: str,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "risk_level": risk_level,
        "record_index": int(record_index),
        "field": field,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def _text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()

