from .span import Span  # noqa
from .span import SpanContext  # noqa
from .scope import Scope  # noqa
from .scope_manager import ScopeManager  # noqa
from .tracer import child_of  # noqa
from .tracer import follows_from  # noqa
from .tracer import Reference  # noqa
from .tracer import ReferenceType  # noqa
from .tracer import Tracer  # noqa
from .tracer import start_child_span  # noqa
from .propagation import Format  # noqa
from .propagation import InvalidCarrierException  # noqa
from .propagation import SpanContextCorruptedException  # noqa
from .propagation import UnsupportedFormatException  # noqa

#tracer: Tracer
TagType = Union[bool, int, float, str, bytes]

def global_tracer() -> Tracer: ...

def set_global_tracer(value: Tracer): ...