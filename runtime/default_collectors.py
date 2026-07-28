from problem_solver import Evidence

def basic_system_collector(issue):

    evidence = []

    evidence.append(
        Evidence(
            source="user",
            key="reported_issue",
            value=issue
        )
    )

    return evidence
