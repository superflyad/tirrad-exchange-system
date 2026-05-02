from sim.tes_serialization.events import serialize_event, serialize_events

__all__ = ["serialize_event", "serialize_events"]

# Backward-compatible aliases (intentionally not exported in __all__).
event_to_dict = serialize_event
events_to_dicts = serialize_events
