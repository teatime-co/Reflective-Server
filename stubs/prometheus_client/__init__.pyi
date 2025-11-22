from typing import List, Optional, Sequence, Any

CONTENT_TYPE_LATEST: str

class CollectorRegistry:
    def __init__(self) -> None: ...

class Counter:
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = ...,
        registry: Optional[CollectorRegistry] = None,
    ) -> None: ...
    def inc(self, amount: float = 1.0) -> None: ...
    def labels(self, **labelkwargs: str) -> Counter: ...

class Gauge:
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = ...,
        registry: Optional[CollectorRegistry] = None,
    ) -> None: ...
    def set(self, value: float) -> None: ...
    def inc(self, amount: float = 1.0) -> None: ...
    def dec(self, amount: float = 1.0) -> None: ...
    def labels(self, **labelkwargs: str) -> Gauge: ...

class Histogram:
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = ...,
        buckets: Sequence[float] = ...,
        registry: Optional[CollectorRegistry] = None,
    ) -> None: ...
    def observe(self, amount: float) -> None: ...
    def labels(self, **labelkwargs: str) -> Histogram: ...

def generate_latest(registry: Optional[CollectorRegistry] = None) -> bytes: ...
