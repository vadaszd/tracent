# from .eu import ExecutionUnit
# from .reporter import AbstractReporter
# from .tracebuilder import TraceBuilder, SimpleTraceBuilder

from functools import wraps
from typing import Optional, Callable, TypeVar, Any, Dict, Tuple, Type

from .eu import ExecutionUnit
from .tracebuilder import (
    AbstractTraceBuilder as _TraceBuilder,
    SimpleTraceBuilder as _SimpleTraceBuilder
    )
from .reporter import AbstractReporter as _Reporter
from .threadingmodel import (
    AbstractThreadingModel,
    StandardThreadingModel
    )

RT = TypeVar('RT')
ARGS = TypeVar('ARGS')
KWARGS = TypeVar('KWARGS')
def delegateTo(f: Callable[[ExecutionUnit], RT]
               ) -> Callable[[], RT]:
    @wraps(f)
    def _delegateToEu(self: 'Tracent', *args: ARGS,
                      **kwargs: KWARGS) -> RT:
        if self._traceBuilder is None:
            raise ValueError("To start tracing, "
                             "tracent().startTracing() must be called")
        eu = self._threadingModel.getEu()
        return f(eu, *args, **kwargs)
    return _delegateToEu


class Tracent(object):
    ConcreteThreadingModel = TypeVar('ConcreteThreadingModel',
                                     bound=AbstractThreadingModel)
    # _ThreadingModel: Callable[[_TraceBuilder], ConcreteThreadingModel]
    _reporter:  _Reporter
    _traceBuilder: Optional[_TraceBuilder]

    def __init__(self) -> None:
        self._ThreadingModel:Type[AbstractThreadingModel] = StandardThreadingModel
        self._reporter = _Reporter()
        self._traceBuilder = None

    def setThreadingModel(self,
                          ThreadingModel: Type[ConcreteThreadingModel]
                          ) -> Tracent:
        self._ThreadingModel = ThreadingModel
        return self

    def setReporter(self, reporter: _Reporter) -> Tracent:
        self._reporter = reporter
        return self

    def startTracing(self) -> None:
        self._traceBuilder = _SimpleTraceBuilder(self._reporter)
        self._threadingModel = self._ThreadingModel(self._traceBuilder)

    startNewTrace = delegateTo(ExecutionUnit.startNewTrace)
    tracePoint = delegateTo(ExecutionUnit.tracePoint)
    getTraceContext = delegateTo(ExecutionUnit.getTraceContext)
    peek = delegateTo(ExecutionUnit.peek)
    addTags = delegateTo(ExecutionUnit.addTags)
    finish = delegateTo(ExecutionUnit.finish)


def tracent() -> Tracent:
    return _tracent

_tracent = Tracent()
