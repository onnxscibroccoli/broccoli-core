from runtime.eventbus import EventBus

from problem_runtime import ProblemRuntime

from knowledge_learning import ProblemLearning

from default_collectors import basic_system_collector
from android_collectors import android_state_collector

from default_reasoner import generic_reasoner
from default_remediator import generic_remediator


bus = EventBus()

runtime = ProblemRuntime(
    bus=bus,
    workflow=None,
    knowledge_graph=ProblemLearning()
)

runtime.register_collector(
    basic_system_collector
)

runtime.register_collector(
    android_state_collector
)

runtime.register_reasoner(
    generic_reasoner
)

runtime.register_remediator(
    generic_remediator
)

bus.publish(
    "USER_GOAL",
    {
        "goal": "Chrome crashes in the background"
    }
)
