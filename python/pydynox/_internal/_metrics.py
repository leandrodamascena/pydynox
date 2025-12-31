"""Internal metrics helpers."""

from __future__ import annotations

from typing import Any

from pydynox import pydynox_core

# Re-export OperationMetrics from Rust
OperationMetrics = pydynox_core.OperationMetrics


class DictWithMetrics(dict[str, Any]):
    """A dict subclass that carries operation metrics.

    Internal class - users just see a dict with .metrics attribute.
    """

    metrics: OperationMetrics

    def __init__(self, data: dict[str, Any], metrics: OperationMetrics):
        super().__init__(data)
        self.metrics = metrics
