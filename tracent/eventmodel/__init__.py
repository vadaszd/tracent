from functools import wraps
from typing import Optional, Callable, TypeVar, Type, Any, cast

from .eu import ExecutionUnit
from .tracebuilder import (
    AbstractTraceBuilder as _TraceBuilder,
    SimpleTraceBuilder as _SimpleTraceBuilder
    )
from .reporter import AbstractReporter as _Reporter
from .concurrency_model import (
    ConcurrencyModel,
    PythonThreads
    )


FuncType = Callable[..., Any]
F = TypeVar('F', bound=FuncType)


def delegate_to(f: F) -> F:
    @wraps(f)
    def _delegate_to_eu(self: 'Tracent', *args: Any,
                        **kwargs: Any) -> Any:
        if self._threading_model is None:
            raise ValueError("To start tracing, "
                             "tracent().startTracing() must be called")
        eu_instance = self._threading_model.get_eu()
        return f(eu_instance, *args, **kwargs)
        # return f(*args, **kwargs)
    return cast(F, _delegate_to_eu)


class Tracent(object):
    ConcreteThreadingModel = TypeVar('ConcreteThreadingModel',
                                     bound=ConcurrencyModel)

    _reporter:  _Reporter
    _traceBuilder: Optional[_TraceBuilder]
    _concurrency_model_class: Type[ConcurrencyModel]
    _threading_model: Optional[ConcurrencyModel]

    def __init__(self) -> None:
        self._concurrency_model_class = PythonThreads
        self._reporter = _Reporter()
        self._traceBuilder = None
        self._threading_model = None

    @property
    def lock_class(self) -> Type[ConcurrencyModel.Acquirable]:
        return self._concurrency_model_class.Lock

    @property
    def my_eu_id(self) -> bytes:
        return self._threading_model.get_eu().id

    def set_threading_model(self,
                            threading_model_class: Type[ConcreteThreadingModel]
                            ) -> 'Tracent':
        self._concurrency_model_class = threading_model_class
        return self

    def set_reporter(self, reporter: _Reporter) -> 'Tracent':
        self._reporter = reporter
        return self

    def start_tracing(self) -> None:
        self._traceBuilder = _SimpleTraceBuilder(self._reporter)
        self._threading_model = self._concurrency_model_class(
            self._traceBuilder
        )

    trace_point = delegate_to(ExecutionUnit.trace_point)
    get_trace_context = delegate_to(ExecutionUnit.get_trace_context)
    peek = delegate_to(ExecutionUnit.peek)
    add_tags = delegate_to(ExecutionUnit.add_tags)
    finish = delegate_to(ExecutionUnit.finish)


def tracent() -> Tracent:
    return _tracent


_tracent = Tracent()
