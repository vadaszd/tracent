from __future__ import absolute_import

import uuid
from uuid import UUID

from .context import SpanContext
from .propagator import Propagator

from opentracing import InvalidCarrierException
from opentracing import SpanContextCorruptedException

from tracent.eventmodel.tracebuilder import EventReference

_BINARY_FORMAT_LENGTH = 26


class SimpleBinaryPropagator(Propagator):
    """A Propagator for Format.BINARY.

        Follows the layout of the traceparent header in
        https://w3c.github.io/trace-context/ as of Editor's Draft 19 January 2019
        Does not support baggage items.
    """

    def inject(self, span_context: SpanContext, carrier: bytearray):

        if type(carrier) is not bytearray:
            raise InvalidCarrierException()

        carrier.extend(b'\00')  # version
        carrier.extend(span_context.event_reference.trace_id.bytes)
        carrier.extend(span_context.event_reference.event_id)
        carrier.extend(b'\01')  # flag sampled=true

    def extract(self, carrier: memoryview):

        if type(carrier) is not memoryview:
            raise InvalidCarrierException()

        if len(carrier) < _BINARY_FORMAT_LENGTH:
            raise SpanContextCorruptedException()

        try:
            version = carrier[0]
            trace_id_bytes = bytes(carrier[1:17])
            parent_id = bytes(carrier[17:25])
            #  flags_bytes = carrier[25]
        except (IndexError, ):
            raise SpanContextCorruptedException()
        else:
            if version == 255:
                raise SpanContextCorruptedException()
            try:
                trace_id = UUID(bytes=trace_id_bytes)
            except ValueError:
                raise SpanContextCorruptedException()
            if trace_id.variant != uuid.RFC_4122 or trace_id.version != 1:
                raise SpanContextCorruptedException()

            return SpanContext(
                event_reference=EventReference(trace_id=trace_id,
                                               event_id=parent_id,
                                               eu_id=None),
                baggage=SpanContext.EMPTY_BAGGAGE,
            )
