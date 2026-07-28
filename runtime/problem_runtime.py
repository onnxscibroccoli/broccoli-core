"""
Broccoli Core
Runtime integration for the Organic Problem Solver.

Pipeline:

User Goal
    ↓
Collectors
    ↓
Reasoners
    ↓
Planner
    ↓
Workflow Engine
    ↓
Verification
    ↓
Knowledge Graph
"""

import logging

from problem_solver import ProblemSolver

logger = logging.getLogger("problem_runtime")


class ProblemRuntime:

    def __init__(self,
                 bus,
                 workflow=None,
                 knowledge_graph=None):

        self.bus = bus
        self.workflow = workflow
        self.knowledge_graph = knowledge_graph

        self.solver = ProblemSolver()

        self.bus.subscribe(
            "USER_GOAL",
            self._on_goal
        )

    def register_collector(self, fn):
        self.solver.register_collector(fn)

    def register_reasoner(self, fn):
        self.solver.register_reasoner(fn)

    def register_remediator(self, fn):
        self.solver.register_remediator(fn)

    def _on_goal(self, event):

        issue = event.get("goal") or event.get("issue")

        if not issue:
            return

        logger.info(f"[ProblemSolver] {issue}")

        diagnosis = self.solver.solve(issue)

        self.bus.publish(
            "DIAGNOSIS_READY",
            diagnosis
        )

        for remediation in diagnosis.remediations:

            self.bus.publish(
                "REMEDIATION_STARTED",
                {
                    "issue": issue,
                    "description": remediation.description
                }
            )

            success = remediation.action()

            self.bus.publish(
                "REMEDIATION_FINISHED",
                {
                    "issue": issue,
                    "description": remediation.description,
                    "success": success
                }
            )

            if success:
                if self.knowledge_graph and hasattr(self.knowledge_graph, "remember"):

                    self.knowledge_graph.remember(
                        issue,
                        remediation.description
                    )

                break
