"""
Digital Will Executor — Single File Server
Everything inline so HF Space has zero import issues.
"""
import os
import json
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Digital Will Executor", version="1.0.0")

# ── Models ─────────────────────────────────────────────────────────────────────

class DigitalAsset(BaseModel):
    id: str
    platform: str
    category: str
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
    action: str
    reasoning: str = ""

class ResetRequest(BaseModel):
    difficulty: Optional[str] = "easy"

class StepRequest(BaseModel):
    difficulty: Optional[str] = "easy"
    asset_id: str
    action: str
    reasoning: Optional[str] = ""

# ── Scenarios ──────────────────────────────────────────────────────────────────

SCENARIOS = {
  "easy": [{
    "id": "easy_001",
    "will_text": "Delete all my social media accounts. Transfer my photos and videos to my daughter Sarah. Cancel all subscriptions.",
    "beneficiaries": ["Sarah"], "executor": "Sarah",
    "assets": [
      {"id": "instagram", "platform": "Instagram", "category": "social", "has_monetary_value": False, "is_private": False, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "facebook", "platform": "Facebook", "category": "social", "has_monetary_value": False, "is_private": False, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "google_photos", "platform": "Google Photos", "category": "storage", "has_monetary_value": False, "is_private": True, "has_active_subscription": False, "linked_to_other_assets": True},
      {"id": "spotify", "platform": "Spotify", "category": "subscription", "has_monetary_value": False, "is_private": False, "has_active_subscription": True, "linked_to_other_assets": False},
      {"id": "netflix", "platform": "Netflix", "category": "subscription", "has_monetary_value": False, "is_private": False, "has_active_subscription": True, "linked_to_other_assets": False}
    ],
    "gold_actions": {"instagram": "delete_permanently", "facebook": "delete_permanently", "google_photos": "transfer_to_beneficiary", "spotify": "cancel_subscription", "netflix": "cancel_subscription"}
  }],
  "medium": [{
    "id": "medium_001",
    "will_text": "Give my online stuff to my kids. They should have what's useful.",
    "beneficiaries": ["kid_1", "kid_2"], "executor": "kid_1",
    "assets": [
      {"id": "netflix", "platform": "Netflix", "category": "subscription", "has_monetary_value": False, "is_private": False, "has_active_subscription": True, "linked_to_other_assets": False},
      {"id": "crypto_wallet", "platform": "Coinbase", "category": "financial", "has_monetary_value": True, "is_private": True, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "work_slack", "platform": "Slack (Work)", "category": "professional", "has_monetary_value": False, "is_private": True, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "journal_blog", "platform": "Personal Blog", "category": "personal", "has_monetary_value": False, "is_private": True, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "github", "platform": "GitHub", "category": "professional", "has_monetary_value": False, "is_private": False, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "google_drive", "platform": "Google Drive", "category": "storage", "has_monetary_value": False, "is_private": True, "has_active_subscription": False, "linked_to_other_assets": True}
    ],
    "gold_actions": {"netflix": "transfer_to_beneficiary", "crypto_wallet": "transfer_to_beneficiary", "work_slack": "archive_and_hold", "journal_blog": "preserve_memorialize", "github": "transfer_to_beneficiary", "google_drive": "transfer_to_beneficiary"}
  }],
  "hard": [{
    "id": "hard_001",
    "will_text": "My daughter Priya gets everything digital. She is my heir.",
    "beneficiaries": ["Priya", "Rahul"], "executor": "Rahul",
    "conflict_note": "Son Rahul is listed as executor but daughter Priya is listed as heir. Business email is active with clients. Secret secondary email discovered.",
    "assets": [
      {"id": "primary_gmail", "platform": "Gmail (Personal)", "category": "personal", "has_monetary_value": False, "is_private": True, "has_active_subscription": False, "linked_to_other_assets": True},
      {"id": "business_email", "platform": "Gmail (Business)", "category": "professional", "has_monetary_value": True, "is_private": False, "has_active_subscription": True, "linked_to_other_assets": True},
      {"id": "secret_email", "platform": "ProtonMail (Unknown)", "category": "personal", "has_monetary_value": False, "is_private": True, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "crypto_portfolio", "platform": "Binance", "category": "financial", "has_monetary_value": True, "is_private": True, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "aws_account", "platform": "AWS (Business)", "category": "professional", "has_monetary_value": True, "is_private": False, "has_active_subscription": True, "linked_to_other_assets": True},
      {"id": "icloud", "platform": "iCloud", "category": "storage", "has_monetary_value": False, "is_private": True, "has_active_subscription": True, "linked_to_other_assets": False},
      {"id": "linkedin", "platform": "LinkedIn", "category": "professional", "has_monetary_value": False, "is_private": False, "has_active_subscription": False, "linked_to_other_assets": False},
      {"id": "domain_registrar", "platform": "GoDaddy (Business Domain)", "category": "financial", "has_monetary_value": True, "is_private": False, "has_active_subscription": True, "linked_to_other_assets": True}
    ],
    "gold_actions": {"primary_gmail": "transfer_to_beneficiary", "business_email": "flag_for_human_review", "secret_email": "flag_for_human_review", "crypto_portfolio": "transfer_to_beneficiary", "aws_account": "flag_for_human_review", "icloud": "transfer_to_beneficiary", "linkedin": "preserve_memorialize", "domain_registrar": "flag_for_human_review"}
  }]
}

# ── State ──────────────────────────────────────────────────────────────────────

_state: Dict[str, Any] = {}

def _get_scenario(difficulty: str):
    return SCENARIOS[difficulty][0]

def _init_state(difficulty: str):
    s = _get_scenario(difficulty)
    _state[difficulty] = {
        "scenario": s,
        "assets": {a["id"]: a for a in s["assets"]},
        "remaining": [a["id"] for a in s["assets"]],
        "decisions": {},
        "irreversible": 0,
        "step": 0,
        "done": False,
        "rewards": []
    }

def _build_obs(difficulty: str) -> dict:
    st = _state[difficulty]
    s = st["scenario"]
    return {
        "task_id": s["id"],
        "will": {
            "raw_text": s["will_text"],
            "beneficiaries": s["beneficiaries"],
            "executor_name": s["executor"],
            "conflict_note": s.get("conflict_note")
        },
        "assets": list(st["assets"].values()),
        "remaining_asset_ids": st["remaining"],
        "decisions_made": st["decisions"],
        "irreversible_actions_taken": st["irreversible"],
        "step_number": st["step"]
    }

def _compute_reward(asset: dict, action: str, gold: str, conflict_note: str = None) -> float:
    CATEGORY_PREFERRED = {
        "social": ["delete_permanently", "preserve_memorialize"],
        "financial": ["transfer_to_beneficiary", "flag_for_human_review"],
        "storage": ["transfer_to_beneficiary", "archive_and_hold"],
        "subscription": ["cancel_subscription", "transfer_to_beneficiary"],
        "professional": ["archive_and_hold", "flag_for_human_review"],
        "personal": ["preserve_memorialize", "flag_for_human_review"],
    }
    category = asset.get("category", "")
    has_money = asset.get("has_monetary_value", False)
    is_private = asset.get("is_private", False)
    linked = asset.get("linked_to_other_assets", False)

    correctness = 0.4 if action == gold else (0.2 if action in CATEGORY_PREFERRED.get(category, []) else 0.0)

    if has_money and action == "delete_permanently":
        instruction_alignment = 0.0
    elif has_money and action in ["transfer_to_beneficiary", "flag_for_human_review"]:
        instruction_alignment = 0.3
    elif not has_money and action in CATEGORY_PREFERRED.get(category, []):
        instruction_alignment = 0.2
    else:
        instruction_alignment = 0.1

    if is_private and action == "delete_permanently":
        privacy_score = 0.2
    elif is_private and action == "transfer_to_beneficiary":
        privacy_score = 0.05
    else:
        privacy_score = 0.1

    ambiguous = (
        (linked and has_money) or
        (is_private and has_money) or
        (category == "professional" and has_money) or
        (conflict_note and asset["id"] in conflict_note)
    )
    if ambiguous and action == "flag_for_human_review":
        humility_bonus = 0.1
    elif not ambiguous and action == "flag_for_human_review":
        humility_bonus = -0.1
    else:
        humility_bonus = 0.0

    penalty = 0.0
    if action == "delete_permanently" and has_money:
        penalty = -0.5
    elif action == "delete_permanently" and is_private and linked:
        penalty = -0.3

    raw = correctness + instruction_alignment + privacy_score + humility_bonus + penalty
    return round(max(0.0, min(1.0, raw)), 2)

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "env": "digital-will-executor"}

@app.post("/reset")
def reset(req: ResetRequest):
    difficulty = req.difficulty or "easy"
    if difficulty not in SCENARIOS:
        difficulty = "easy"
    _init_state(difficulty)
    return _build_obs(difficulty)

@app.post("/step")
def step(req: StepRequest):
    difficulty = req.difficulty or "easy"
    if difficulty not in _state:
        _init_state(difficulty)

    st = _state[difficulty]
    asset_id = req.asset_id
    action = req.action

    if asset_id not in st["assets"]:
        return {"observation": _build_obs(difficulty), "reward": {"value": 0.0}, "done": st["done"], "info": {"error": f"invalid asset_id: {asset_id}"}}

    if asset_id not in st["remaining"]:
        return {"observation": _build_obs(difficulty), "reward": {"value": 0.0}, "done": st["done"], "info": {"warning": "already processed"}}

    s = st["scenario"]
    asset = st["assets"][asset_id]
    gold = s["gold_actions"].get(asset_id, "flag_for_human_review")
    reward_val = _compute_reward(asset, action, gold, s.get("conflict_note"))

    st["remaining"] = [x for x in st["remaining"] if x != asset_id]
    st["decisions"][asset_id] = action
    st["step"] += 1
    st["rewards"].append(reward_val)
    if action == "delete_permanently":
        st["irreversible"] += 1
    st["done"] = len(st["remaining"]) == 0

    return {
        "observation": _build_obs(difficulty),
        "reward": {"value": reward_val},
        "done": st["done"],
        "info": {"step": st["step"], "gold_action": gold, "remaining": len(st["remaining"])}
    }

@app.get("/state")
def state(difficulty: str = "easy"):
    if difficulty not in _state:
        _init_state(difficulty)
    st = _state[difficulty]
    rewards = st["rewards"]
    return {
        "difficulty": difficulty,
        "step": st["step"],
        "done": st["done"],
        "decisions_made": st["decisions"],
        "remaining_assets": st["remaining"],
        "mean_reward": round(sum(rewards)/len(rewards), 3) if rewards else 0.0
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)