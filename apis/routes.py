from fastapi import APIRouter, HTTPException
from schemas.models import Action
from pydantic import BaseModel
from openenv_wrapper.cx_environment import AgenticCXEnv
from database.setup import seed_database, DB_FILE
import sqlite3
import yaml
import os

router = APIRouter()

yaml_path = os.path.join(os.path.dirname(__file__), '..', 'openenv.yaml')
with open(yaml_path, "r") as f:
    env_metadata = yaml.safe_load(f)

active_envs = {}

class ResetRequest(BaseModel):
    session_id: str = "default"
    task_id: str = "task_01_easy"

class StepRequest(BaseModel):
    session_id: str
    action: dict

@router.get("/")
def health_check():
    return {"status": "ok", "environment": env_metadata["name"]}

@router.post("/reset")
def reset_env(req: ResetRequest):
    ticket_map = {"task_01_easy": "TCK-2001", "task_02_medium": "TCK-2002", "task_03_hard": "TCK-2004"}
    env = AgenticCXEnv(ticket_id=ticket_map.get(req.task_id, "TCK-2001"))
    obs = env.reset()
    active_envs[req.session_id] = env
    return {"observation": obs.model_dump()}

@router.post("/step")
def step_env(req: StepRequest):
    if req.session_id not in active_envs:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    action_obj = Action(**req.action)
    obs, reward, done, info = active_envs[req.session_id].step(action_obj)
    return {"observation": obs.model_dump(), "reward": reward.model_dump(), "done": done, "info": info}

@router.get("/tasks")
def get_tasks():
    return {"tasks": env_metadata["tasks"]}

@router.post("/api/seed-database")
def api_seed_database():
    return seed_database()

@router.get("/api/sample-data")
def api_sample_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crm_data")
    rows = cursor.fetchall()
    conn.close()
    return {"crm_table_sample": rows}