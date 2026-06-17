from audit_assistant.workpaper import generate_workpaper_description


def test_generate_workpaper_description_structures_interview_notes():
    result = generate_workpaper_description(
        topic="采购合同归档流程访谈",
        source_notes="客户财务每月从采购系统导出合同清单，由实习生按供应商和月份整理。金额超过10万元的合同需要主管复核。",
        audit_cycle="采购与付款循环",
    )

    assert "一、访谈主题" in result
    assert "采购合同归档流程访谈" in result
    assert "采购与付款循环" in result
    assert "金额超过10万元" in result
    assert "需进一步获取" in result
