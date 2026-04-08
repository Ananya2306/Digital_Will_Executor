"""
FastAPI server exposing the OpenEnv interface.
Endpoints: POST /reset, POST /step, GET /state, GET /health
"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from digital_env.env import DigitalWillExecutorEnv
from digital_env.models import ExecutorAction

app = FastAPI(
    title="Digital Will Executor",
    description="OpenEnv environment — AI digital estate executor",
    version="1.0.0",
)

# One env instance per server (stateful)
_envs: dict[str, DigitalWillExecutorEnv] = {}


def get_env(difficulty: str = "easy") -> DigitalWillExecutorEnv:
    if difficulty not in _envs:
        _envs[difficulty] = DigitalWillExecutorEnv(difficulty=difficulty)
    return _envs[difficulty]


class ResetRequest(BaseModel):
    difficulty: Optional[str] = "easy"


class StepRequest(BaseModel):
    difficulty: Optional[str] = "easy"
    asset_id: str
    action: str
    reasoning: Optional[str] = ""


@app.get("/health")
def health():
    return {"status": "ok", "env": "digital-will-executor"}


@app.post("/reset")
def reset(req: ResetRequest):
    env = get_env(req.difficulty)
    obs = env.reset()
    return obs.model_dump()


@app.post("/step")
def step(req: StepRequest):
    env = get_env(req.difficulty)
    try:
        action = ExecutorAction(
            asset_id=req.asset_id,
            action=req.action,
            reasoning=req.reasoning or "",
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    result = env.step(action)
    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward.model_dump(),
        "done": result.done,
        "info": result.info,
    }


@app.get("/state")
def state(difficulty: str = "easy"):
    env = get_env(difficulty)
    return env.state()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
