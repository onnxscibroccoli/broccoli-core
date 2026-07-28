from event_bus import EventBus
from workflow.task import Task
from workflow.queue import TaskQueue

class Planner:
    def __init__(self, bus: EventBus, queue: TaskQueue):
        self.bus = bus
        self.queue = queue
        self.bus.subscribe("AccessibilityCaptureReady", self.plan_from_ui)

    def plan_from_ui(self, payload):
        if payload and payload.get("primary_action"):
            task = Task(id="send_message", priority="HIGH", action="tap_send")
            self.queue.enqueue(task)
            self.bus.publish("PlannerTaskCreated", task)
        print("Planner: Task generated from UI")

    def generate_plan(self, goal):
        print(f"Planner: Generating plan for goal: {goal}")
        return [Task(id="goal", priority="NORMAL", action=goal)]
