from typing import Set, Optional, Union, Iterable, Dict
from uuid import UUID

from opentracing import Format, Tracer, Span, Reference, Scope
from opentracing import UnsupportedFormatException
from opentracing.scope_managers import ThreadLocalScopeManager, ScopeManager
from .context import SpanContext
from .propagator import Propagator
from .span import EventBasedSpan
from ..eventmodel.tracebuilder import TagDict


class EventBasedTracer(Tracer):

    def __init__(self, scope_manager: ScopeManager = None):
        """Initialize an EventBasedTracer instance.
        Note that the returned EventBasedTracer has *no* propagators registered. The
        user should either call register_propagator() for each needed
        inject/extract format and/or the user can simply call
        register_required_propagators().
        The required formats are opt-in because of protobuf version conflicts
        with the binary carrier.
        """

        scope_manager = ThreadLocalScopeManager() \
            if scope_manager is None else scope_manager
        super(EventBasedTracer, self).__init__(scope_manager)

        self._propagators = {}

    def register_propagator(self, format_identifier: str,
                            propagator: Propagator):
        """Register a propagator with this EventBasedTracer.
        :param string format_identifier: a Format identifier like
                Format.TEXT_MAP
        :param Propagator propagator: a Propagator instance to handle
            inject/extract calls involving `format`
        """
        self._propagators[format_identifier] = propagator

    def register_required_propagators(self):
        from .text_propagator import TextPropagator
        from .binary_propagator import BinaryPropagator
        self.register_propagator(Format.TEXT_MAP, TextPropagator())
        self.register_propagator(Format.HTTP_HEADERS, TextPropagator())
        self.register_propagator(Format.BINARY, BinaryPropagator())

    def start_active_span(self,
                          operation_name: Optional[str],
                          child_of: Optional[Union[Span, SpanContext]] = None,
                          references:  Optional[Iterable[Reference]] = None,
                          tags: Optional[TagDict] = None,
                          start_time: Optional[float] = None,
                          ignore_active_span: bool = False,
                          finish_on_close: bool = True) -> Scope:

        # create a new Span
        span = self.start_span(
            operation_name=operation_name,
            child_of=child_of,
            references=references,
            tags=tags,
            start_time=start_time,
            ignore_active_span=ignore_active_span,
        )

        return self.scope_manager.activate(span, finish_on_close)

    def start_span(self,
                   operation_name: Optional[str] = None,
                   child_of: Optional[Union[Span, SpanContext]] = None,
                   references: Optional[Iterable[Reference]] = None,
                   tags: Optional[TagDict] = None,
                   start_time: Optional[float] = None,
                   ignore_active_span: bool = False) -> Span:

        # See if we have a parent_ctx in `references`
        trace_id: Optional[UUID] = None
        causes: Set[SpanContext] = set()
        if child_of is not None:
            ctx = (child_of if isinstance(child_of, SpanContext)
                   else child_of.context)
            causes.add(ctx)
            trace_id = ctx.event_reference.trace_id
        elif references is not None:
            causes += (reference.referenced_context
                       for reference in references)

        # retrieve the active SpanContext
        if not ignore_active_span and len(causes) == 0:
            scope = self.scope_manager.active
            if scope is not None:
                causes.add(scope.span.context)
                trace_id = scope.span.context.event_reference.trace_id

        span = EventBasedSpan(
            self, trace_id,
            operation_name=operation_name,
            causes=causes,
            tags=tags)
        return span

    def inject(self, span_context, format, carrier):
        if format in self._propagators:
            self._propagators[format].inject(span_context, carrier)
        else:
            raise UnsupportedFormatException()

    def extract(self, format, carrier):
        if format in self._propagators:
            return self._propagators[format].extract(carrier)
        else:
            raise UnsupportedFormatException()
