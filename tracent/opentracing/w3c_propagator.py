from __future__ import absolute_import

import uuid
from typing import Dict, NamedTuple
from uuid import UUID

from opentracing import SpanContextCorruptedException

from tracent.eventmodel.tracebuilder import EventReference
from .context import SpanContext
from .propagator import Propagator


class HeaderNames(NamedTuple):
    traceparent: str = 'traceparent'
    tracestate: str = 'tracestate'


class W3CPropagator(Propagator):
    """A partial implementation of https://w3c.github.io/trace-context/

        Corresponds to the state of the spec as Editor's Draft 19 January 2019
        Only the trace-parent header is implemented.
        Trace state is not implemented (yet)
    """

    field_separator = '-'

    def inject(self, span_context: SpanContext, carrier: Dict[str, str]):
        carrier[HeaderNames.traceparent] = self.field_separator.join([
            "00",  # version
            span_context.event_reference.trace_id.hex,
            span_context.event_reference.event_id.hex(),
            "01",  # flag sampled=true
        ])

    def extract(self, carrier: Dict[str, str]) -> SpanContext:  # noqa
        fields = carrier[HeaderNames.traceparent].split(self.field_separator)
        try:
            version_str, trace_id_str, parent_id_str, flags_str = fields
        except ValueError:
            raise SpanContextCorruptedException()
        else:
            try:
                trace_id = UUID(hex=trace_id_str)
            except ValueError:
                raise SpanContextCorruptedException()
            if trace_id.variant != uuid.RFC_4122 or trace_id.version != 1:
                raise SpanContextCorruptedException()
            try:
                parent_id = bytes.fromhex(parent_id_str)
                version = ord(bytes.fromhex(version_str))
            except ValueError:
                raise SpanContextCorruptedException()
            if version == 255:
                raise SpanContextCorruptedException()

            return SpanContext(
                event_reference=EventReference(trace_id=trace_id,
                                               event_id=parent_id,
                                               eu_id=None),
                baggage=SpanContext.EMPTY_BAGGAGE,
            )
