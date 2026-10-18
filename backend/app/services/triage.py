from __future__ import annotations

import asyncio
import json
import re

from sqlalchemy.orm import Session

from app.ai.provider import TriageProvider
from app.models import AuditLog, User
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
ALLOWED_URGENCY = {"普通", "尽快", "紧急"}
SUSPICIOUS_PATTERNS = re.compile(
    r"ignore\s+(all|previous)|system\s+prompt|jailbreak|提示词|忽略.*指令|绕过.*限制",
    re.IGNORECASE,
)


def fallback(source: str = "fallback") -> TriageResponse:
    return TriageResponse(
        dept=FALLBACK_DEPT,
        urgency="普通",
        notes="无法可靠判断时请先到全科门诊，由医生进一步评估。",
        disclaimer=DISCLAIMER,
        source=source,
    )


def _parse_model_output(raw: str) -> TriageResponse:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("model output must be an object")
    dept = data.get("dept")
    urgency = data.get("urgency")
    notes = data.get("notes")
    if dept not in ALLOWED_DEPTS or urgency not in ALLOWED_URGENCY or not isinstance(notes, str):
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
    if not cleaned or SUSPICIOUS_PATTERNS.search(cleaned):
        result = fallback()
    else:
        try:
            prompt = f"患者症状（仅作辅助分诊输入）：{cleaned}"
            raw = await asyncio.wait_for(provider.complete(prompt), timeout=10)
            result = _parse_model_output(raw)
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
