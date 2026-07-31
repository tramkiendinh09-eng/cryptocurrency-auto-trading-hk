from pydantic import BaseModel


class RiskEvaluation(BaseModel):
    passed: bool
    reason: str
    rule_code: str | None = None

