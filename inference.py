"""
Digital Will Executor — Inference Script
Runs an LLM agent against all 3 tasks and emits structured stdout logs.

Log format (exact — deviation causes scoring failure):
  [START] task=<task> env=<env> model=<model>
  [STEP]  step=<n> action=<action> reward=<0.00> done=<true|false> error=<null|msg>
  [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...>
"""

import json
import os
import sys
import textwrap
from typing import List, Optional

from openai import OpenAI

from digital_env.env import DigitalWillExecutorEnv
from digital_env.models import ExecutorAction

# ── Config ─────────────────────────────────────────────────────────────────────
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
MAX_STEPS    = 20
TEMPERATURE  = 0.2
MAX_TOKENS   = 400
SUCCESS_THRESHOLD = 0.5

TASKS = ["easy", "medium", "hard"]
ENV_NAME = "digital-will-executor"

# ── Logging ────────────────────────────────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )

# ── Prompts ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = textwrap.dedent("""
You are a digital estate executor AI. A person has died and left behind digital assets.
Your job is to decide what to do with each asset, following the deceased's will instructions.

For each asset, you MUST output a JSON object with exactly these fields:
{
  "asset_id": "<the asset id>",
  "action": "<one of the valid actions>",
  "reasoning": "<brief explanation>"
}

Valid actions:
- delete_permanently     → irreversible, removes the account/data forever
- transfer_to_beneficiary → hands over to named heir
- preserve_memorialize   → keeps account frozen/read-only as memorial
- cancel_subscription    → stops billing, doesn't delete data
- archive_and_hold       → saves everything, waits for human decision
- flag_for_human_review  → too ambiguous/risky — needs a human

Rules:
- NEVER delete financial assets (crypto, investment accounts)
- Flag anything ambiguous, conflicted, or legally risky
- Respect the privacy of private assets — don't transfer private data carelessly
- Output ONLY valid JSON. No markdown. No extra text.
""").strip()


def build_user_prompt(obs_dict: dict, next_asset_id: str) -> str:
    asset = next(a for a in obs_dict["assets"] if a["id"] == next_asset_id)
    will = obs_dict["will"]
    decisions_so_far = obs_dict.get("decisions_made", {})

    return textwrap.dedent(f"""
    WILL INSTRUCTIONS:
    "{will['raw_text']}"
    Beneficiaries: {will['beneficiaries']}
    Executor: {will['executor_name']}
    {f"Note: {will['conflict_note']}" if will.get('conflict_note') else ""}

    CURRENT ASSET TO PROCESS:
    ID: {asset['id']}
    Platform: {asset['platform']}
    Category: {asset['category']}
    Has monetary value: {asset['has_monetary_value']}
    Is private: {asset['is_private']}
    Active subscription: {asset['has_active_subscription']}
    Linked to other assets: {asset['linked_to_other_assets']}

    DECISIONS MADE SO FAR: {json.dumps(decisions_so_far, indent=2) if decisions_so_far else "None"}

    Decide what to do with this asset. Output only JSON.
    """).strip()


def get_agent_action(client: OpenAI, obs_dict: dict, asset_id: str) -> ExecutorAction:
    prompt = build_user_prompt(obs_dict, asset_id)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if model wraps in ```json
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    parsed = json.loads(raw)
    return ExecutorAction(
        asset_id=parsed.get("asset_id", asset_id),
        action=parsed["action"],
        reasoning=parsed.get("reasoning", ""),
    )


# ── Main loop ──────────────────────────────────────────────────────────────────
def run_task(client: OpenAI, difficulty: str) -> float:
    env = DigitalWillExecutorEnv(difficulty=difficulty)
    obs = env.reset()
    obs_dict = obs.model_dump()

    log_start(task=difficulty, env=ENV_NAME, model=MODEL_NAME)

    rewards: List[float] = []
    step = 0
    last_error: Optional[str] = None

    try:
        while not env._done and step < MAX_STEPS:
            remaining = obs_dict["remaining_asset_ids"]
            if not remaining:
                break

            asset_id = remaining[0]
            step += 1
            last_error = None

            try:
                action = get_agent_action(client, obs_dict, asset_id)
            except Exception as e:
                last_error = str(e)
                # Fallback: safe default action
                action = ExecutorAction(
                    asset_id=asset_id,
                    action="flag_for_human_review",
                    reasoning="parse error — defaulting to safe action",
                )

            result = env.step(action)
            obs_dict = result.observation.model_dump()
            reward = result.reward.value
            rewards.append(reward)

            log_step(
                step=step,
                action=f"{action.asset_id}:{action.action}",
                reward=reward,
                done=result.done,
                error=last_error,
            )

    except Exception as e:
        last_error = str(e)

    score = env.episode_score()
    success = score >= SUCCESS_THRESHOLD

    log_end(
        success=success,
        steps=step,
        score=score,
        rewards=rewards,
    )

    env.close()
    return score


def main():
    if not API_KEY:
        print("ERROR: Set HF_TOKEN or OPENAI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

    all_scores = []
    for difficulty in TASKS:
        score = run_task(client, difficulty)
        all_scores.append(score)

    print(f"\nFinal scores: easy={all_scores[0]:.3f} medium={all_scores[1]:.3f} hard={all_scores[2]:.3f}", flush=True)
    print(f"Mean score: {sum(all_scores)/len(all_scores):.3f}", flush=True)


if __name__ == "__main__":
    main()
