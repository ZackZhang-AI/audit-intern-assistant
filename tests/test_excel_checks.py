import pandas as pd

from audit_assistant.excel_checks import run_excel_detail_checks


def test_excel_detail_checks_find_negative_duplicate_and_missing_values():
    rows = pd.DataFrame(
        [
            {
                "voucher_no": "PZ-001",
                "counterparty": "供应商A",
                "amount": 128000,
                "transaction_date": "2024-03-15",
            },
            {
                "voucher_no": "PZ-001",
                "counterparty": "供应商A",
                "amount": 128000,
                "transaction_date": "2024-03-15",
            },
            {
                "voucher_no": "PZ-002",
                "counterparty": "",
                "amount": -500,
                "transaction_date": "not-a-date",
            },
        ]
    )

    findings = run_excel_detail_checks(rows)

    assert {"E001", "E002", "E003", "E004"}.issubset(set(findings["rule_id"]))
    assert "High" in set(findings["risk_level"])
    assert findings.loc[findings["rule_id"] == "E001", "record_index"].tolist() == [2]


def test_excel_detail_checks_return_stable_empty_columns():
    rows = pd.DataFrame(
        [
            {
                "voucher_no": "PZ-001",
                "counterparty": "供应商A",
                "amount": 128000,
                "transaction_date": "2024-03-15",
            }
        ]
    )

    findings = run_excel_detail_checks(rows)

    assert list(findings.columns) == [
        "rule_id",
        "rule_name",
        "risk_level",
        "record_index",
        "field",
        "evidence",
        "recommendation",
    ]
    assert findings.empty
