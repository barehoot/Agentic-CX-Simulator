import os
import time
import requests
import json
from typing import List, Optional
from openai import OpenAI

# ==========================================
# 1. CONFIGURATION
# ==========================================
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)

ENV_URL = "http://localhost:7860"
BENCHMARK = "agentic-cx-simulator"

SYSTEM_PROMPT = """
You are an autonomous AI customer support agent.
Your goal is to resolve customer tickets efficiently without breaching the SLA.

You MUST respond with ONLY a valid JSON object. Do not include markdown formatting.

AVAILABLE TOOLS:
1. {"tool": "query_crm"} 
2. {"tool": "search_kb", "query": "<your search terms>"} 
3. {"tool": "ask_customer", "question": "<your question>"} 
4. {"tool": "resolve_ticket", "solution_code": "<EXACT_CODE>"} 
"""

# ==========================================
# 2. OFFICIAL HACKATHON LOGGING FUNCTIONS
# ==========================================
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

# ==========================================
# 3. THE INFERENCE LOOP
# ==========================================
def evaluate_task(task_id: str) -> float:
    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)
    
    session_id = f"eval_{task_id}"
    
    try:
        res = requests.post(f"{ENV_URL}/reset", json={"session_id": session_id, "task_id": task_id})
        res.raise_for_status()
        current_obs = res.json()["observation"]
    except Exception as e:
        log_end(success=False, steps=0, score=0.0, rewards=[])
        return 0.0

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    done = False
    step_count = 0
    max_steps = 15
    rewards: List[float] = []
    
    while not done and step_count < max_steps:
        step_count += 1
        messages.append({"role": "user", "content": f"Observation: {json.dumps(current_obs)}"})

        # --- LLM CALL ---
        error_msg = None
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            llm_reply = response.choices[0].message.content
            action_dict = json.loads(llm_reply)
        except Exception as e:
            error_msg = f"LLM Error: {str(e)}"
            action_dict = {"tool": "ask_customer", "question": "Could you clarify?"}
            llm_reply = json.dumps(action_dict)

        messages.append({"role": "assistant", "content": llm_reply})

        # --- STEP ENVIRONMENT ---
        step_res = requests.post(f"{ENV_URL}/step", json={"session_id": session_id, "action": action_dict})
        step_data = step_res.json()

        current_obs = step_data["observation"]
        done = step_data["done"]
        
        # Parse reward
        reward_obj = step_data["reward"]
        step_reward = reward_obj["value"] if isinstance(reward_obj, dict) else float(reward_obj)
        rewards.append(step_reward)
        
        # Flatten action to a single line for the logger
        action_str = json.dumps(action_dict).replace("\n", "").replace("\r", "")
        
        # Log exactly as the judge expects
        log_step(step=step_count, action=action_str, reward=step_reward, done=done, error=error_msg)
        
        time.sleep(0.5)

        # Calculate final normalized score strictly within (0.0, 1.0)
        max_possible_reward = 2.0 
        raw_total = sum(rewards)
    
        # First, get the raw ratio
        raw_normalized = raw_total / max_possible_reward
    
        # CRITICAL FIX: Clamp the score strictly between 0.01 and 0.99
        # This guarantees the score never hits exactly 0.0 or 1.0
        normalized_score = max(0.01, min(raw_normalized, 0.99))
    
    success = normalized_score > 0.5

    log_end(success=success, steps=step_count, score=normalized_score, rewards=rewards)
    return normalized_score

# ==========================================
# 4. EXECUTE
# ==========================================
if __name__ == "__main__":
    time.sleep(2) # Wait for FastAPI to start
    tasks = ["task_01_easy", "task_02_medium", "task_03_hard"]
    for task in tasks:
        evaluate_task(task)