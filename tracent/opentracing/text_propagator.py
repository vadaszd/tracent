from __future__ import absolute_import

import uuid
from typing import Dict
from uuid import UUID

from opentracing import SpanContextCorruptedException

from tracent.eventmodel.tracebuilder import EventReference
from .context import SpanContext
from .propagator import Propagator

prefix_tracer_state = 'ot-tracer-'
prefix_baggage = 'ot-baggage-'
field_name_trace_id = prefix_tracer_state + 'trace_id'
field_name_span_id = prefix_tracer_state + 'spanid'
field_name_sampled = prefix_tracer_state + 'sampled'
field_count = 3


class TextPropagator(Propagator):
    """A EventBasedTracer Propagator for Format.TEXT_MAP."""

    def inject(self, span_context: SpanContext, carrier: Dict[str, str]):
        carrier[field_name_trace_id] = span_context.event_reference.trace_id.hex
        carrier[field_name_span_id] = span_context.event_reference.event_id.hex()
        carrier[field_name_sampled] = "true"
        if span_context.baggage is not None:
            for k in span_context.baggage:
                carrier[prefix_baggage+k] = span_context.baggage[k]

    def extract(self, carrier: Dict[str, str]) -> SpanContext:  # noqa
        count = 0
        span_id, trace_id, sampled = (None, None, False)
        baggage = {}
        for k in carrier:
            v = carrier[k]
            k = k.lower()
            if k == field_name_span_id:
                try:
                    span_id = bytes.fromhex(v)
                except ValueError:
                    raise SpanContextCorruptedException()
                count += 1
            elif k == field_name_trace_id:
                try:
                    trace_id = UUID(hex=v)
                except ValueError:
                    raise SpanContextCorruptedException()
                if trace_id.variant != uuid.RFC_4122 or trace_id.version != 1:
                    raise SpanContextCorruptedException()
                count += 1
            elif k == field_name_sampled:
                if v in ('true', '1'):
                    sampled = True
                elif v in ('false', '0'):
                    sampled = False
                else:
                    raise SpanContextCorruptedException()
                count += 1
            elif k.startswith(prefix_baggage):
                baggage[k[len(prefix_baggage):]] = v

        if count != field_count:
            raise SpanContextCorruptedException()

        return SpanContext(
            event_reference=EventReference(trace_id=trace_id, event_id=span_id, eu_id=None),
            baggage=baggage,
            )
