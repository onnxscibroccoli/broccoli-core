"""
Global EventBus service.

Every runtime component imports the same bus instance:

    from runtime.eventbus.service import bus
"""

from runtime.eventbus.bus import EventBus

bus = EventBus()
