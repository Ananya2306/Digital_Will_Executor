"""
Grader — Easy Task
Score: fraction of assets assigned the gold-standard action.
Fully deterministic, reproducible.
"""
from digital_env.env import DigitalWillExecutorEnv
from digital_env.models import ExecutorAction
from digital_env.utils import get_scenario


def grade_easy(decisions: dict, gold_actions: dict) -> float:
    correct = sum(
        1 for asset_id, action in decisions.items()
        if gold_actions.get(asset_id) == action
    )
    total = len(gold_actions)
    return round(correct / total, 3) if total > 0 else 0.0


def run_grader(agent_decisions: dict) -> float:
    scenario = get_scenario("easy", 0)
    return grade_easy(agent_decisions, scenario["gold_actions"])


if __name__ == "__main__":
    # Sanity check — perfect agent
    scenario = get_scenario("easy", 0)
    perfect = scenario["gold_actions"]
    score = grade_easy(perfect, scenario["gold_actions"])
    print(f"Perfect agent score: {score}")  # should be 1.0

    # Random agent
    random_decisions = {k: "archive_and_hold" for k in scenario["gold_actions"]}
    score = grade_easy(random_decisions, scenario["gold_actions"])
    print(f"Random agent score: {score}")   # should be < 1.0
