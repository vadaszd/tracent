
from threading import Lock
from typing import Optional, Iterable, Dict
from uuid import UUID

from opentracing import Tracer, Span

from .context import SpanContext
from ..eventmodel import tracent
from ..eventmodel.eu import EventReference
from ..eventmodel.tracebuilder import TagType
from ..oob import tracent_pb2 as pb


class EventBasedSpan(Span):
    """EventBasedSpan is a thread-safe implementation of opentracing.Span.
    """

    startEvent: EventReference
    latestEvent: EventReference

    def __init__(
            self,
            tracer: Tracer,
            trace_id: UUID,
            operation_name: Optional[str] = None,
            causes: Iterable[SpanContext] = tuple(),
            tags=Dict[str, TagType]
    ):
        merged_baggage: Dict[str, str] = dict()
        for parent_ctx in causes:
            merged_baggage.update(parent_ctx.baggage)

        context = SpanContext(tracent().peek(), merged_baggage)
        super(EventBasedSpan, self).__init__(tracer, context=context)

        tracent().switch_trace(trace_id)
        self.start_event = tracent().trace_point(
            event_type=pb.Event.OT_START_SPAN,
            status=pb.Event.UNKNOWN,
            causes=(parent_ctx.event_reference for parent_ctx in causes),
            tags=tags
        )
        tracent().add_tags(operation_name=operation_name)
        self._lock = Lock()   # XXX should use the lock class of threadingmodel
        self.trace_id = trace_id

    def set_operation_name(self, operation_name: str) -> Span:
        tracent().add_tags(operation_name=operation_name)
        return super(EventBasedSpan, self).set_operation_name(operation_name)

    def set_tag(self, key: str, value: TagType) -> Span:
        tracent().add_tags(**{key: value})
        return super(EventBasedSpan, self).set_tag(key, value)

    def log_kv(self, key_values: Dict[str, str], timestamp=None) -> Span:
        tracent().trace_point(
            event_type=pb.Event.OT_LOG,
            status=pb.Event.UNKNOWN,
            tags=key_values
        )
        return super(EventBasedSpan, self).log_kv(key_values, timestamp)

    def finish(self, finish_time=None):
        tracent().trace_point(
            event_type=pb.Event.OT_FINISH_SPAN,
            status=pb.Event.UNKNOWN,
        )

    @property
    def context(self) -> SpanContext:
        tracent().trace_point(event_type=pb.Event.OT_GET_CONTEXT,
                              status=pb.Event.UNKNOWN,
                              )
        baggage = super(EventBasedSpan, self).context.baggage
        return SpanContext(tracent().get_trace_context(), baggage)

    def set_baggage_item(self, key, value):
        new_context = self._context.with_baggage_item(key, value)
        with self._lock:
            self._context = new_context
        return self

    def get_baggage_item(self, key):
        with self._lock:
            return self._context.baggage.get(key)


