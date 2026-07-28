import json
import os

DB = "knowledge/problem_history.json"


class ProblemLearning:

    def __init__(self):

        os.makedirs("knowledge", exist_ok=True)

        if os.path.exists(DB):
            with open(DB) as f:
                self.db = json.load(f)
        else:
            self.db = {}

    def remember(self, issue, remediation):

        self.db.setdefault(issue, [])

        self.db[issue].append(remediation)

        with open(DB, "w") as f:
            json.dump(
                self.db,
                f,
                indent=2
            )
