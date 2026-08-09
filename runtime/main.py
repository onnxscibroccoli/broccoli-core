from __future__ import annotations

import time

from runtime.bootstrap import build_runtime_stack

# How often (in ticks) to run a full recovery scan.
# Event-driven recovery still happens immediately on GOAL_FAILED.
RECOVERY_SCAN_EVERY = 10


def main():
    runtime = build_runtime_stack()

    config = runtime["config"]
    logger = runtime["logger"]
    state = runtime["state"]
    metrics = runtime["metrics"]
    scheduler = runtime["scheduler"]
    health = runtime["health"]
    lifecycle = runtime["lifecycle"]
    workflow_executor = runtime["workflow_executor"]
    recovery = runtime["recovery"]
    goal_manager = runtime["goal_manager"]
    transport_registry = runtime["transport_registry"]
    bus = runtime["bus"]

    components = [
        config,
        logger,
        bus,
        state,
        metrics,
        scheduler,
        health,
        runtime["governor"],
        runtime["accessibility"],
        runtime["planner"],
        workflow_executor,
        runtime["grok"],
        runtime["knowledge_graph"],
        runtime["knowledge_graph_transport"],
        runtime["coordinator"],
        goal_manager,
        recovery,
        runtime["plugins"],
        runtime["plugin_loader_transport"],
        transport_registry,
    ]

    transport_registry.start_all()
    lifecycle.startup(components)

    goal_manager.create_goal("test_goal", "Test autonomous task")

    state.transition("RUNNING")
    logger.log("INFO", "Autonomous Task Executive started", "Core")

    tick = 0
    try:
        while True:
            bus.publish("TICK")
            scheduler.run_pending()
            workflow_executor.run_pending()
            transport_registry.publish_health()
            health_report = health.check()
            bus.publish("HEALTH_CHECK", health_report, source="HealthMonitor")
            metrics.increment("loop_cycles")

            tick += 1
            if tick % RECOVERY_SCAN_EVERY == 0:
                recovered = recovery.scan_and_recover()
                if recovered:
                    logger.log("INFO", f"Recovered {recovered} goal(s)", "Recovery")

            time.sleep(config.tick_seconds)
    except KeyboardInterrupt:
        logger.log("INFO", "Shutdown requested", "Core")
        state.transition("STOPPED")
    finally:
        try:
            lifecycle.shutdown(components)
        finally:
            transport_registry.stop_all()


if __name__ == "__main__":
    main()


def capability_status(event):
    try:
        print(
            "Capability:",
            event.get("capability"),
            "available=",
            event.get("available"),
            "fallback=",
            event.get("fallback"),
        )
    except Exception:
        pass


try:
    from runtime.eventbus.service import bus

    bus.subscribe("CAPABILITY_STATUS", capability_status)
except Exception:
    pass
