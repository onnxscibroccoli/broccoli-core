from problem_solver import Remediation

def generic_remediator(diagnosis):

    plans = []

    for hypothesis in diagnosis.hypotheses:

        def action(name=hypothesis.name):
            print(f"[Broccoli] Executing remediation: {name}")
            return True

        plans.append(
            Remediation(
                description=hypothesis.name,
                action=action
            )
        )

    return plans
