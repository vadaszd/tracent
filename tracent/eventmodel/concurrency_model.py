import threading

from abc import ABC, abstractmethod
from typing import Type, Protocol, ContextManager

from .eu import ExecutionUnit
from .tracebuilder import AbstractTraceBuilder
from ..oob import tracent_pb2 as pb


class ConcurrencyModel(ABC):

    class Acquirable(Protocol, ContextManager['Acquirable']):

        if sys.version_info >= (3,):
            def acquire(self, blocking: bool = ..., timeout: float = ...) -> bool:
                ...
        else:
            def acquire(self, blocking: bool = ...) -> bool:
                ...

        def release(self) -> None:
            ...

        def locked(self) -> bool:
            ...

    Lock: Type[Acquirable]

    def __init__(self, trace_builder: AbstractTraceBuilder) -> None:
        self.trace_builder = trace_builder

    @abstractmethod
    def get_eu(self) -> ExecutionUnit:
        """ Return an ExecutionUnit according to the policy of the model
        """

    @abstractmethod
    def finish(self) -> None:
        """ Clean up the EU
        """


class PythonThreads(ConcurrencyModel):

    class _EuProxy(threading.local):
        eu: ExecutionUnit

    Lock = threading.Lock

    def __init__(self, trace_builder: AbstractTraceBuilder) -> None:
        super(PythonThreads, self).__init__(trace_builder)
        self._eu_proxy = PythonThreads._EuProxy()

    def get_eu(self) -> ExecutionUnit:
        try:
            eu = self._eu_proxy.eu
        except AttributeError:
            eu = ExecutionUnit(self.trace_builder, pb.ExecutionUnit.THREAD)
            self._eu_proxy.eu = eu
            # TODO: Register finish() as a per thread exit handler
            # once https://bugs.python.org/issue14073 is done.
        return eu

    def finish(self) -> None:
        try:
            del self._eu_proxy.eu
        except AttributeError:
            pass
