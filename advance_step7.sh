#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

echo "=== Step 7: Persistent Daemon + Production Wrapper ==="

cat > service.sh <<'SERVICE'
#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core
echo "🚀 Starting Broccoli Core as service..."
while true; do
  PYTHONPATH=. python3 runtime/main.py
  echo "Service crashed - restarting in 5s..."
  sleep 5
done
SERVICE

cat > runtime/main.py <<'PY'
import sys
sys.path.insert(0, '.')

from runtime.services.daemon import Daemon
from drivers.accessibility.driver import AccessibilityDriver
from workflow.task import Task
from workflow.queue import TaskQueue
from workflow.executor import WorkflowExecutor
from runtime.plugin_loader import load_plugins

def main():
    print("🚀 Broccoli Core Production Service - Step 7\n")
    
    plugins = load_plugins()
    print(f"✅ Loaded {len(plugins)} plugins")

    acc = AccessibilityDriver()
    print("✅ Accessibility ready")

    queue = TaskQueue()
    executor = WorkflowExecutor()

    tasks = [
        Task(goal="Production health check", priority="HIGH"),
        Task(goal="Run accessibility test", priority="NORMAL")
    ]

    for t in tasks:
        queue.enqueue(t)

    while True:
        task = queue.dequeue()
        if not task: break
        result = executor.execute(task)
        queue.complete(task, result)

    print(f"\n🎯 All systems operational - {len(queue.completed)} tasks validated")

    daemon = Daemon()
    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()
        print("\n✅ Service shutdown complete.")

if __name__ == "__main__":
    main()
PY

chmod +x service.sh run.sh advance_step7.sh
echo "✅ Step 7 Complete - Persistent Service Ready"
echo "Usage:"
echo "  ./run.sh          # Normal run"
echo "  ./service.sh      # Persistent background service"
echo ""
echo "Phase 2 Implementation Finished!"
