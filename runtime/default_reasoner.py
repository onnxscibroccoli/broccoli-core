from problem_solver import Hypothesis

def generic_reasoner(diagnosis):

    issue = diagnosis.issue.lower()

    hypotheses = []

    if "crash" in issue:
        hypotheses.append(
            Hypothesis(
                "Application crash",
                0.60,
                "User explicitly mentioned crashing."
            )
        )

    if "background" in issue:
        hypotheses.append(
            Hypothesis(
                "Background execution restriction",
                0.75,
                "Android commonly restricts background apps."
            )
        )

    if not hypotheses:
        hypotheses.append(
            Hypothesis(
                "Unknown issue",
                0.20,
                "Insufficient evidence."
            )
        )

    return hypotheses
