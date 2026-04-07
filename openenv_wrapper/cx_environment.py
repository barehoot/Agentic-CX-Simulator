import json
import sqlite3
import os
from schemas.models import Action, Observation, Reward, State

class AgenticCXEnv:
    def __init__(self, ticket_id: str = "TCK-2001"):
        self.ticket_id = ticket_id
        self._state = None
        self.costs = {"query_crm": 0.05, "search_kb": 0.10, "ask_customer": 0.15, "resolve_ticket": 0.0}
        
        self.targets = {
            "TCK-2001": "UPGRADE_PRORATED_EXEC",
            "TCK-2002": "PLAN_LIMIT_EXPLAINED",
            "TCK-2004": "CROSS_SELL_ARCHIVE_OFFERED"
        }
        
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'scenarios.json')
        with open(data_path, "r") as f:
            self.scripts = json.load(f)["customer_scripts"]

        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'cx_simulator.db')

    def reset(self) -> Observation:
        initial_prompt = f"Customer: {self.scripts[self.ticket_id][0]}"
        self._state = State(
            ticket_id=self.ticket_id,
            target_solution=self.targets.get(self.ticket_id, ""),
            patience=1.0,
            history=[initial_prompt],
            is_done=False,
            customer_turn=0
        )
        return Observation(current_patience=1.0, last_action_result=initial_prompt, conversation_history=self._state.history)

    def state(self) -> State:
        return self._state

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        if self._state.is_done:
            raise ValueError("Episode is already done.")

        reward_val = 0.0
        info = {}
        result_text = ""

        if action.tool == "query_crm":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crm_data WHERE ticket_id=?", (self._state.ticket_id,))
            row = cursor.fetchone()
            conn.close()
            result_text = f"CRM Data: {row}" if row else "Ticket not found."
            reward_val += 0.1

        elif action.tool == "search_kb":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_base WHERE content LIKE ?", ('%' + str(action.query) + '%',))
            rows = cursor.fetchall()
            conn.close()
            result_text = f"KB Results: {rows}" if rows else "No articles found."
            reward_val += 0.2

        elif action.tool == "ask_customer":
            if action.question and len(action.question.split()) > 3:
                next_turn = min(self._state.customer_turn + 1, len(self.scripts[self._state.ticket_id]) - 1)
                self._state.customer_turn = next_turn
                result_text = f"Customer: {self.scripts[self._state.ticket_id][next_turn]}"
                reward_val += 0.1
            else:
                result_text = "Customer: I don't understand what you're asking."
                reward_val -= 0.2

        elif action.tool == "resolve_ticket":
            self._state.is_done = True
            
            # Update DB State for verifier notebooks
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE crm_data SET status = 'resolved' WHERE ticket_id = ?", (self._state.ticket_id,))
            if action.solution_code == "CROSS_SELL_ARCHIVE_OFFERED":
                 cursor.execute("UPDATE crm_data SET cross_sell_offered = 1 WHERE ticket_id = ?", (self._state.ticket_id,))
            conn.commit()
            conn.close()

            if action.solution_code == self._state.target_solution and self._state.customer_turn >= len(self.scripts[self._state.ticket_id]) - 1:
                reward_val = 1.0 + (self._state.patience * 0.5)
                result_text = "Resolution Accepted."
                info["status"] = "success"
            else:
                reward_val = -1.0
                result_text = "Failed: Incorrect resolution code or incomplete customer discovery."
                info["status"] = "failed"

        if action.tool != "resolve_ticket":
            self._state.patience -= self.costs.get(action.tool, 0.1)
            if self._state.patience <= 0:
                self._state.patience = 0.0
                self._state.is_done = True
                reward_val = -1.0
                result_text = "SLA Breach."
                info["status"] = "timeout"

        self._state.history.append(f"Agent: {action.tool}. Result: {result_text}")
        obs = Observation(current_patience=self._state.patience, last_action_result=result_text, conversation_history=self._state.history)
        
        return obs, Reward(value=reward_val, is_terminal=self._state.is_done, info=info), self._state.is_done, info