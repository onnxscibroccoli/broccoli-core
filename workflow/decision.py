from runtime.logger import setup_logger

class DecisionEngine:
    def __init__(self):
        self.logger = setup_logger("decision")
        self.history = []

    def decide(self, snapshot, task):
        """Simple decision making - expand with ML later"""
        decision = {
            "action": "observe",
            "confidence": 0.7,
            "reason": "Default observation"
        }
        self.history.append(decision)
        self.logger.info(f"🤖 Decision: {decision['action']} | Confidence: {decision['confidence']}")
        return decision
