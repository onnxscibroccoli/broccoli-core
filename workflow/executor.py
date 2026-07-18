from workflow.task import Task
from providers.grok import GrokProvider

class WorkflowExecutor:
    def __init__(self):
        self.provider = GrokProvider()
        self.provider.initialize()

    def execute(self, task: Task) -> dict:
        print(f"⚙️ Executing: {task.goal}")
        try:
            resp = self.provider.send({"message": task.goal})
            return {"success": True, "content": resp.get("content", "")}
        except:
            return {"success": False, "error": "failed"}
