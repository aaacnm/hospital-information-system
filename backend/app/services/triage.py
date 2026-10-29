from __future__ import annotations

import asyncio
import json
import re

from sqlalchemy.orm import Session

from app.ai.provider import TriageProvider
from app.models import AuditLog, Department, User
from app.schemas.triage import TriageResponse

DISCLAIMER = "本建议由 AI 生成，仅供参考，请以医生诊断为准"
FALLBACK_DEPT = "全科门诊"
ALLOWED_DEPTS = {
    "全科门诊",
    "内科",
    "外科",
    "消化内科",
    "呼吸内科",
    "儿科",
    "妇产科",
    "皮肤科",
}
ALLOWED_URGENCY = {"普通", "尽快", "急诊"}
PRIVATE_INPUT = re.compile(
    r"(?<!\d)(?:1[3-9]\d{9}|\d{17}[\dXx])(?!\d)|(?:姓名|身份证|手机号|电话)\s*[:：]?"
)
SUSPICIOUS_PATTERNS = re.compile(
    r"ignore\s+(all|previous)|system\s+prompt|jailbreak|提示词|忽略.*指令|绕过.*限制",
    re.IGNORECASE,
)


def fallback(source: str = "fallback") -> TriageResponse:
    return TriageResponse(
        dept=FALLBACK_DEPT,
        urgency="待人工评估",
        notes="服务暂不可用，无法评估紧急程度。请联系分诊人员；胸痛、呼吸困难、意识异常等请立即寻求急救。",
        disclaimer=DISCLAIMER,
        source=source,
    )


def _parse_model_output(raw: str, departments: set[str] | None = None) -> TriageResponse:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("model output must be an object")
    dept = data.get("dept")
    urgency = data.get("urgency")
    notes = data.get("notes")
    if (
        dept not in (departments if departments is not None else ALLOWED_DEPTS)
        or urgency not in ALLOWED_URGENCY
        or not isinstance(notes, str)
    ):
        raise ValueError("model output does not match the triage contract")
    notes = notes.strip()[:500]
    if not notes:
        raise ValueError("notes cannot be empty")
    return TriageResponse(
        dept=dept,
        urgency=urgency,
        notes=notes,
        disclaimer=DISCLAIMER,
        source="llm",
    )


async def triage(
    db: Session, user: User, symptoms: str, provider: TriageProvider
) -> TriageResponse:
    cleaned = symptoms.strip()
    if not cleaned or SUSPICIOUS_PATTERNS.search(cleaned) or PRIVATE_INPUT.search(cleaned):
        result = fallback()
    else:
        departments = {
            row[0]
            for row in db.query(Department.name)
            .filter(Department.status == "active")
            .limit(100)
            .all()
        }
        # Release the read transaction before waiting on the remote provider.
        db.commit()
        try:
            prompt = (
                f"仅允许以下科室：{','.join(sorted(departments))}。"
                f"患者症状（仅作辅助分诊输入）：{cleaned}"
            )
            raw = await asyncio.wait_for(provider.complete(prompt), timeout=10)
            result = _parse_model_output(raw, departments)
        except Exception:
            result = fallback()
    db.add(
        AuditLog(
            user_id=user.id,
            action="triage.request",
            resource_type="triage",
            resource_id="anonymous",
            after_json=json.dumps(
                {"source": result.source, "dept": result.dept}, ensure_ascii=False
            ),
        )
    )
    db.commit()
    return result
