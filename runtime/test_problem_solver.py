from problem_solver import ProblemSolver

from default_collectors import basic_system_collector
from default_reasoner import generic_reasoner
from default_remediator import generic_remediator

solver = ProblemSolver()

solver.register_collector(basic_system_collector)
solver.register_reasoner(generic_reasoner)
solver.register_remediator(generic_remediator)

diagnosis = solver.solve(
    "Chrome crashes in the background"
)

print("\nIssue:")
print(diagnosis.issue)

print("\nEvidence:")
for e in diagnosis.evidence:
    print(vars(e))

print("\nHypotheses:")
for h in diagnosis.hypotheses:
    print(vars(h))

print("\nRemediations:")
for r in diagnosis.remediations:
    print(r.description)
