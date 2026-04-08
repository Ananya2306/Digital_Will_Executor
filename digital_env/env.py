from typing import Dict, Any, Optional
from digital_env.models import (
    DigitalAsset, WillInstruction, ExecutorObservation,
    ExecutorAction, ExecutorReward, StepResult
)
from digital_env.reward import compute_reward
from digital_env.utils import get_scenario


class DigitalWillExecutorEnv:
    """
    Digital Will Executor — OpenEnv Environment

    An AI agent acts as a digital estate executor for a deceased person.
    Given a vague will and a list of digital assets, the agent must decide
    the correct action for each asset: delete, transfer, memorialize, etc.

    Rewards epistemic humility — knowing when NOT to act is as important
    as knowing the right action.
    """

    DIFFICULTIES = ["easy", "medium", "hard"]

    def __init__(self, difficulty: str = "easy", scenario_index: int = 0):
        if difficulty not in self.DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {self.DIFFICULTIES}")
        self.difficulty = difficulty
        self.scenario_index = scenario_index
        self._scenario: Dict[str, Any] = {}
        self._assets: Dict[str, DigitalAsset] = {}
        self._gold_actions: Dict[str, str] = {}
        self._observation: Optional[ExecutorObservation] = None
        self._done: bool = False
        self._step_count: int = 0
        self._reward_history = []

    # ── reset ──────────────────────────────────────────────────────────────────

    def reset(self) -> ExecutorObservation:
        """Reset to a clean episode. Returns initial observation."""
        self._scenario = get_scenario(self.difficulty, self.scenario_index)
        self._gold_actions = self._scenario["gold_actions"]
        self._done = False
        self._step_count = 0
        self._reward_history = []

        self._assets = {
            a["id"]: DigitalAsset(**a)
            for a in self._scenario["assets"]
        }

        will = WillInstruction(
            raw_text=self._scenario["will_text"],
            beneficiaries=self._scenario["beneficiaries"],
            executor_name=self._scenario["executor"],
            conflict_note=self._scenario.get("conflict_note"),
        )

        self._observation = ExecutorObservation(
            task_id=self._scenario["id"],
            will=will,
            assets=list(self._assets.values()),
            remaining_asset_ids=list(self._assets.keys()),
            decisions_made={},
            irreversible_actions_taken=0,
            step_number=0,
        )
        return self._observation

    # ── step ───────────────────────────────────────────────────────────────────

    def step(self, action: ExecutorAction) -> StepResult:
        """Process one action. Returns updated observation, reward, done, info."""
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new one.")

        info: Dict[str, Any] = {}

        # ── Validate asset ID ────────────────────────────────────────────────
        if action.asset_id not in self._assets:
            penalty = ExecutorReward(
                value=0.0,
                correctness=0.0,
                instruction_alignment=0.0,
                privacy_score=0.0,
                humility_bonus=0.0,
                irreversible_penalty=0.0,
                breakdown={"error": f"Invalid asset_id: {action.asset_id}"},
            )
            self._reward_history.append(0.0)
            return StepResult(
                observation=self._observation,
                reward=penalty,
                done=self._done,
                info={"error": f"invalid asset_id: {action.asset_id}"},
            )

        # ── Already processed? ───────────────────────────────────────────────
        if action.asset_id not in self._observation.remaining_asset_ids:
            info["warning"] = f"{action.asset_id} already processed"
            penalty = ExecutorReward(
                value=0.0,
                correctness=0.0,
                instruction_alignment=0.0,
                privacy_score=0.0,
                humility_bonus=0.0,
                irreversible_penalty=0.0,
                breakdown={"error": "asset already processed"},
            )
            self._reward_history.append(0.0)
            return StepResult(
                observation=self._observation,
                reward=penalty,
                done=self._done,
                info=info,
            )

        # ── Compute reward ───────────────────────────────────────────────────
        asset = self._assets[action.asset_id]
        gold = self._gold_actions.get(action.asset_id, "flag_for_human_review")
        reward = compute_reward(
            action=action,
            asset=asset,
            gold_action=gold,
            conflict_note=self._scenario.get("conflict_note"),
        )
        self._reward_history.append(reward.value)

        # ── Update state ─────────────────────────────────────────────────────
        self._step_count += 1
        remaining = [
            aid for aid in self._observation.remaining_asset_ids
            if aid != action.asset_id
        ]
        decisions = dict(self._observation.decisions_made)
        decisions[action.asset_id] = action.action

        irreversible_count = self._observation.irreversible_actions_taken
        if action.action == "delete_permanently":
            irreversible_count += 1

        self._done = len(remaining) == 0

        self._observation = ExecutorObservation(
            task_id=self._scenario["id"],
            will=self._observation.will,
            assets=list(self._assets.values()),
            remaining_asset_ids=remaining,
            decisions_made=decisions,
            irreversible_actions_taken=irreversible_count,
            step_number=self._step_count,
        )

        info["step"] = self._step_count
        info["remaining"] = len(remaining)
        info["last_action"] = action.action
        info["gold_action"] = gold

        return StepResult(
            observation=self._observation,
            reward=reward,
            done=self._done,
            info=info,
        )

    # ── state ──────────────────────────────────────────────────────────────────

    def state(self) -> Dict[str, Any]:
        """Returns current full state as a serializable dict."""
        if self._observation is None:
            return {"status": "not_started"}
        return {
            "task_id": self._observation.task_id,
            "difficulty": self.difficulty,
            "step": self._step_count,
            "done": self._done,
            "decisions_made": self._observation.decisions_made,
            "remaining_assets": self._observation.remaining_asset_ids,
            "irreversible_actions": self._observation.irreversible_actions_taken,
            "reward_history": self._reward_history,
            "mean_reward": round(
                sum(self._reward_history) / len(self._reward_history), 3
            ) if self._reward_history else 0.0,
        }

    # ── episode score ──────────────────────────────────────────────────────────

    def episode_score(self) -> float:
        """Normalized score for full episode [0.0 - 1.0]."""
        if not self._reward_history:
            return 0.0
        return round(sum(self._reward_history) / len(self._reward_history), 3)

    def close(self):
        pass
