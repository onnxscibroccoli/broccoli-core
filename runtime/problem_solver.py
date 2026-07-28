"""
Broccoli Core - Organic Problem Solver

Pipeline:
User Issue
    ↓
Observe
    ↓
Collect Evidence
    ↓
Generate Hypotheses
    ↓
Rank by Confidence
    ↓
Plan Remediation
    ↓
Execute
    ↓
Verify
    ↓
Learn

Provider-agnostic.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List
import time


@dataclass
class Evidence:
    source: str
    key: str
    value: object
    confidence: float = 1.0


@dataclass
class Hypothesis:
    name: str
    confidence: float
    rationale: str


@dataclass
class Remediation:
    description: str
    action: Callable[[], bool]


@dataclass
class Diagnosis:
    issue: str
    timestamp: float = field(default_factory=time.time)
    evidence: List[Evidence] = field(default_factory=list)
    hypotheses: List[Hypothesis] = field(default_factory=list)
    remediations: List[Remediation] = field(default_factory=list)


class ProblemSolver:

    def __init__(self):
        self.collectors = []
        self.reasoners = []
        self.remediators = []

    def register_collector(self, fn):
        self.collectors.append(fn)

    def register_reasoner(self, fn):
        self.reasoners.append(fn)

    def register_remediator(self, fn):
        self.remediators.append(fn)

    def solve(self, issue: str):

        diagnosis = Diagnosis(issue)

        for collector in self.collectors:
            diagnosis.evidence.extend(collector(issue))

        for reasoner in self.reasoners:
            diagnosis.hypotheses.extend(reasoner(diagnosis))

        diagnosis.hypotheses.sort(
            key=lambda h: h.confidence,
            reverse=True
        )

        for remediator in self.remediators:
            diagnosis.remediations.extend(remediator(diagnosis))

        return diagnosis
