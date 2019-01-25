
from abc import ABCMeta, abstractmethod
from typing import Any
import six

from .context import SpanContext


class Propagator(six.with_metaclass(ABCMeta, object)):

    @abstractmethod
    def inject(self, span_context: SpanContext, carrier: Any) -> None:
        pass

    @abstractmethod
    def extract(self, carrier) -> SpanContext:
        pass
