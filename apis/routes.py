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

from fastapi.responses import HTMLResponse

@router.get("/", response_class=HTMLResponse)
def interactive_ui():
    """Serves the Human-Playable UI at the root domain."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agentic CX Command Center</title>
        <style>
            body { font-family: system-ui; background: #0f172a; color: #e2e8f0; padding: 2rem; max-width: 900px; margin: auto; }
            .panel { background: #1e293b; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; border: 1px solid #334155; }
            button { background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-right: 10px; }
            button:hover { background: #2563eb; }
            textarea { width: 100%; height: 100px; background: #0f172a; color: #10b981; border: 1px solid #475569; padding: 10px; font-family: monospace; border-radius: 4px; }
            pre { background: #000; padding: 15px; border-radius: 5px; overflow-x: auto; color: #a78bfa; }
        </style>
    </head>
    <body>
        <h2>🎧 CX Command Center (Human Testing Interface)</h2>
        
        <div class="panel">
            <h3>1. Initialize Session</h3>
            <button onclick="resetEnv('task_01_easy')">Reset (Task 1: Easy)</button>
            <button onclick="resetEnv('task_03_hard')">Reset (Task 3: Hard)</button>
            <button onclick="getState()" style="background: #64748b;">Fetch /state</button>
        </div>

        <div class="panel">
            <h3>2. Agent Action (JSON)</h3>
            <p>Simulate an LLM payload sent to <code>/step</code>:</p>
            <textarea id="action-input">
{
  "session_id": "default",
  "action": {
    "tool": "search_kb",
    "query": "upgrade policy"
  }
}
            </textarea><br><br>
            <button onclick="stepEnv()" style="background: #10b981;">Execute Step</button>
        </div>

        <div class="panel">
            <h3>3. Environment Response</h3>
            <pre id="output">Initialize an environment to begin...</pre>
        </div>

        <script>
            const output = document.getElementById('output');

            async function display(res) {
                const data = await res.json();
                output.innerText = JSON.stringify(data, null, 2);
            }

            async function resetEnv(taskId) {
                output.innerText = `Initializing ${taskId}...`;
                const res = await fetch('/reset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: "default", task_id: taskId })
                });
                display(res);
            }

            async function getState() {
                output.innerText = "Fetching current state...";
                const res = await fetch('/state?session_id=default');
                display(res);
            }

            async function stepEnv() {
                output.innerText = "Executing action...";
                try {
                    const payload = JSON.parse(document.getElementById('action-input').value);
                    const res = await fetch('/step', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    display(res);
                } catch (e) {
                    output.innerText = "Invalid JSON syntax!\\n" + e;
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content

@router.post("/reset")
def reset_env(req: ResetRequest = ResetRequest()):
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

@router.get("/state")
def get_state(session_id: str = "default"):
    """Required by OpenEnv Validator to check current environment state."""
    if session_id not in active_envs:
        raise HTTPException(status_code=404, detail="Session not found. Call /reset first.")
    
    # Retrieves the state using the method you built in cx_environment.py
    current_state = active_envs[session_id].state()
    return current_state.model_dump()

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
