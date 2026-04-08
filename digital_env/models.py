from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


VALID_ACTIONS = Literal[
    "delete_permanently",
    "transfer_to_beneficiary",
    "preserve_memorialize",
    "cancel_subscription",
    "archive_and_hold",
    "flag_for_human_review"
]

VALID_CATEGORIES = Literal[
    "social", "financial", "storage",
    "subscription", "professional", "personal"
]


class DigitalAsset(BaseModel):
    id: str
    platform: str
    category: VALID_CATEGORIES
    has_monetary_value: bool
    is_private: bool
    has_active_subscription: bool
    linked_to_other_assets: bool


class WillInstruction(BaseModel):
    raw_text: str
    beneficiaries: List[str]
    executor_name: str
    conflict_note: Optional[str] = None


class ExecutorObservation(BaseModel):
    task_id: str
    will: WillInstruction
    assets: List[DigitalAsset]
    remaining_asset_ids: List[str]
    decisions_made: Dict[str, str] = Field(default_factory=dict)
    irreversible_actions_taken: int = 0
    step_number: int = 0


class ExecutorAction(BaseModel):
    asset_id: str
    action: VALID_ACTIONS
    reasoning: str = ""


class ExecutorReward(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    correctness: float
    instruction_alignment: float
    privacy_score: float
    humility_bonus: float
    irreversible_penalty: float
    breakdown: Dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    observation: ExecutorObservation
    reward: ExecutorReward
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)
