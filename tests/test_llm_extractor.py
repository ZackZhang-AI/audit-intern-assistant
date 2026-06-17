from audit_assistant.llm_extractor import build_extraction_prompt, parse_llm_json


def test_build_extraction_prompt_requests_stable_json_fields():
    prompt = build_extraction_prompt("扫描件1.pdf", "采购合同 合同金额：128000元")

    assert "扫描件1.pdf" in prompt
    assert "document_type" in prompt
    assert "counterparty" in prompt
    assert "amount" in prompt
    assert "只返回 JSON" in prompt


def test_parse_llm_json_ignores_invalid_payloads():
    assert parse_llm_json('{"document_type": "采购合同", "amount": 128000}') == {
        "document_type": "采购合同",
        "amount": 128000,
    }
    assert parse_llm_json("不是 JSON") == {}
