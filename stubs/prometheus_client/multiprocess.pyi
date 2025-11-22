from prometheus_client import CollectorRegistry

class MultiProcessCollector:
    def __init__(self, registry: CollectorRegistry) -> None: ...
