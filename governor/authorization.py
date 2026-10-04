import json
import os

class AgenticTakeoverGovernor:
    def __init__(self, policy_path="scripts/agent_takeover_policy.json"):
        self.state = "IDLE"
        self.max_financial_limit = 100.0
        if os.path.exists(policy_path):
            try:
                with open(policy_path, "r") as f:
                    data = json.load(f)
                    self.max_financial_limit = data.get("max_spend_usd", 100.0)
            except Exception:
                pass

    def request_takeover(self, spend_amount: float) -> bool:
        if spend_amount > self.max_financial_limit:
            self.state = "DENIED"
            return False
        self.state = "AUTHORIZED"
        return True
