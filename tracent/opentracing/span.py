
from typing import Optional, Iterable, Dict
from uuid import UUID

from opentracing import Tracer, Span

from .context import SpanContext
from ..eventmodel import ConcurrencyModel
from ..eventmodel import tracent
from ..eventmodel.eu import EventReference
from ..eventmodel.tracebuilder import TagType
from ..oob import tracent_pb2 as pb


class EventBasedSpan(Span):
    """EventBasedSpan is a thread-safe implementation of opentracing.Span.
    """

    _trace_id: UUID
    _lock: ConcurrencyModel.Acquirable
    _start_event: EventReference
    _finish_event: Optional[EventReference]
    _latest_events: Dict[bytes, EventReference]  # keyed by EU ID

    def __init__(
            self,
            tracer: Tracer,
            trace_id: Optional[UUID],
            operation_name: Optional[str] = None,
            causes: Iterable[SpanContext] = tuple(),
            tags=Dict[str, TagType]
    ):
        merged_baggage: Dict[str, str] = dict()

        for parent_ctx in causes:
            merged_baggage.update(parent_ctx.baggage)

        context = SpanContext(tracent().peek(), merged_baggage)
        super(EventBasedSpan, self).__init__(tracer, context=context)

        self._lock = tracent().lock_class()
        self._start_event = tracent().trace_point(
            trace_id=trace_id,
            event_type=pb.Event.OT_START_SPAN,
            status=pb.Event.UNKNOWN,
            causes=(parent_ctx.event_reference for parent_ctx in causes),
            tags=tags
        )
        self._trace_id = self._start_event.trace_id
        self._finish_event = None
        self._latest_events = dict()
        tracent().add_tags(operation_name=operation_name)

    def set_operation_name(self, operation_name: str) -> Span:
        tracent().add_tags(operation_name=operation_name)
        return super(EventBasedSpan, self).set_operation_name(operation_name)

    def set_tag(self, key: str, value: TagType) -> Span:
        tracent().add_tags(**{key: value})
        return super(EventBasedSpan, self).set_tag(key, value)

    def log_kv(self, key_values: Dict[str, str], timestamp=None) -> Span:
        if self._finish_event is not None:
            raise RuntimeError("Span is already finished.")

        event = tracent().trace_point(
            trace_id=self._trace_id,
            event_type=pb.Event.OT_LOG,
            status=pb.Event.UNKNOWN,
            tags=key_values
        )
        with self._lock:
            assert event.eu_id is not None
            self._latest_events[event.eu_id] = event

        return super(EventBasedSpan, self).log_kv(key_values, timestamp)

    def finish(self, finish_time=None):
        # need to lock due to access to _latest_events & _finish_event
        with self._lock:
            if self._finish_event is not None:
                raise RuntimeError("Span is already finished.")

            my_eu_id = tracent().my_eu_id
            self._finish_event = tracent().trace_point(
                trace_id=self._trace_id,
                event_type=pb.Event.OT_FINISH_SPAN,
                status=pb.Event.UNKNOWN,
                causes=[event for event in self._latest_events.values()
                        if event.eu_id != my_eu_id]
            )

    @property
    def context(self) -> SpanContext:
        event = (tracent().trace_point(event_type=pb.Event.OT_GET_CONTEXT,
                                       status=pb.Event.UNKNOWN,
                                       )
                 if self._finish_event is None
                 else self._finish_event)

        with self._lock:
            assert event.eu_id is not None
            self._latest_events[event.eu_id] = event

        baggage = super(EventBasedSpan, self).context.baggage
        return SpanContext(event, baggage)

    def set_baggage_item(self, key, value):
        new_context = self._context.with_baggage_item(key, value)
        with self._lock:
            self._context = new_context
        return self

    def get_baggage_item(self, key):
        with self._lock:
            return self._context.baggage.get(key)


