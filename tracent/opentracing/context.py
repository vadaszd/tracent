from __future__ import absolute_import

from typing import Dict

import opentracing

from tracent.eventmodel.tracebuilder import EventReference


class SpanContext(opentracing.SpanContext):
    """SpanContext satisfies the opentracing.SpanContext contract.
    """

    def __init__(
            self,
            event_reference: EventReference,
            baggage: Dict[str, str] = opentracing.SpanContext.EMPTY_BAGGAGE):
        self.event_reference = event_reference
        self._baggage = baggage

    @property
    def baggage(self):
        return self._baggage

    def with_baggage_item(self, key, value):
        new_baggage = self._baggage.copy()
        new_baggage[key] = value
        return SpanContext(
            event_reference=self.event_reference,
            baggage=new_baggage)
