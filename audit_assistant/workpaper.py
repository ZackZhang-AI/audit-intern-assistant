from __future__ import annotations

import re


def generate_workpaper_description(topic: str, source_notes: str, audit_cycle: str) -> str:
    topic = topic.strip() or "未命名访谈/底稿事项"
    audit_cycle = audit_cycle.strip() or "待分类循环"
    notes = _normalize_notes(source_notes)
    key_points = _split_points(notes)

    point_lines = "\n".join(f"{index}. {point}" for index, point in enumerate(key_points, start=1))
    if not point_lines:
        point_lines = "1. 原始记录信息不足，需补充访谈纪要或底稿说明。"

    return (
        f"一、访谈主题\n{topic}\n\n"
        f"二、涉及审计循环\n{audit_cycle}\n\n"
        f"三、已了解事项\n{point_lines}\n\n"
        "四、初步审计关注点\n"
        "1. 关注资料来源、整理口径和复核责任是否清晰。\n"
        "2. 关注金额较大或异常资料是否保留复核证据。\n\n"
        "五、后续资料需求\n"
        "需进一步获取原始文件、复核记录、审批依据或系统导出明细，以支持底稿结论。"
    )


def _normalize_notes(source_notes: str) -> str:
    return re.sub(r"\s+", " ", str(source_notes or "")).strip()


def _split_points(notes: str) -> list[str]:
    if not notes:
        return []
    raw_points = re.split(r"[。；;]\s*", notes)
    points = [point.strip() for point in raw_points if point.strip()]
    return points[:5]

