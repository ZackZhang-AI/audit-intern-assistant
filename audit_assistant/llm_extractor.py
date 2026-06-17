from __future__ import annotations

import json
import os
from typing import Any


JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_type": {"type": "string"},
        "audit_cycle": {"type": "string"},
        "counterparty": {"type": "string"},
        "date": {"type": "string"},
        "amount": {"type": ["number", "null"]},
        "document_number": {"type": "string"},
    },
    "required": [
        "document_type",
        "audit_cycle",
        "counterparty",
        "date",
        "amount",
        "document_number",
    ],
}


def build_extraction_prompt(filename: str, extracted_text: str) -> str:
    return f"""
你是一名审计资料整理助手。请根据 OCR 或文本抽取结果识别资料类型，并抽取可用于文件命名和归档的字段。

文件名：{filename}

请只返回 JSON，不要输出解释性文字。JSON 字段必须包含：
- document_type：采购合同、销售合同、合同、发票、银行回单、明细账、未知资料
- audit_cycle：采购与付款循环、销售与收款循环、货币资金循环、总账与报表循环、待人工分类
- counterparty：交易对方、供应商、客户或付款方名称
- date：YYYY-MM-DD；识别不到则为空字符串
- amount：数字；识别不到则为 null
- document_number：合同编号、发票号码、回单编号或凭证号

文本内容：
{extracted_text[:4000]}
""".strip()


def parse_llm_json(payload: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def extract_fields_with_openai(filename: str, extracted_text: str) -> dict[str, Any]:
    """Optional OpenAI structured extraction. Returns an empty dict when unavailable."""
    if not os.getenv("OPENAI_API_KEY"):
        return {}

    try:
        from openai import OpenAI
    except ImportError:
        return {}

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "你是谨慎的审计资料字段抽取助手，只输出符合 schema 的 JSON。",
            },
            {"role": "user", "content": build_extraction_prompt(filename, extracted_text)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "audit_document_fields",
                "schema": JSON_SCHEMA,
                "strict": True,
            }
        },
    )
    return parse_llm_json(response.output_text)

