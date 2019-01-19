from typing import Optional, Union, NamedTuple, List, Dict, Any

from .span import Span
from .span import SpanContext
from .scope import Scope
from .scope_manager import ScopeManager
from .propagation import Format, UnsupportedFormatException

from . import TagType


class Tracer(object):
    """Tracer is the entry point API between instrumentation code and the
    tracing implementation.
    This implementation both defines the public Tracer API, and provides
    a default no-op behavior.
    """

    # TODO: proper type (enum) for formats
    _supported_formats = [Format.TEXT_MAP, Format.BINARY, Format.HTTP_HEADERS]

    def __init__(self, scope_manager: Optional[ScopeManager] = None): ...

    @property
    def scope_manager(self) -> ScopeManager: ...

    @property
    def active_span(self) -> Span: ...

    def start_active_span(self,
                          operation_name: str,
                          child_of: Optional[Union[Span, SpanContext]],
                          references: Optional[List[References]],
                          tags: Optional[Dict[str, TagType]],
                          # https://github.com/python/typeshed/blob/master/stdlib/2and3/time.pyi#L81
                          start_time: float,
                          ignore_active_span: bool,
                          finish_on_close: bool) -> Scope: ...

    def start_span(self,
                   operation_name: Optional[str],
                   child_of: Optional[Union[Span, SpanContext]],
                   references: Optional[List[References]],
                   tags: Optional[Dict[str, TagType]],
                   start_time: float,
                   ignore_active_span: bool) -> Span: ...

    def inject(self, span_context: SpanContext,
               format: str,  # TODO: proper type (enum) for formats
               carrier: Any) -> None:  ...

    def extract(self,
                format: str,  # TODO: proper type (enum) for formats
                carrier: Any) -> SpanContext:  ...


class ReferenceType(object):
    CHILD_OF: str      # TODO: proper type (enum) for ReferenceType
    FOLLOWS_FROM: str  # TODO: proper type (enum) for ReferenceType

class Reference(NamedTuple):
    type: str    # TODO: proper type (enum) for ReferenceType
    referenced_context: SpanContext


def child_of(referenced_context: SpanContext) -> Reference: ...


def follows_from(referenced_context: SpanContext) -> Reference: ...


def start_child_span(parent_span: Span,
                     operation_name: str,
                     tags: Optional[Dict[str, TagType]],
                     start_time: Optional[float]) -> Span: ...
