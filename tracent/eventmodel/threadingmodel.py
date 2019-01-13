import threading

from abc import ABC, abstractmethod

from .eu import ExecutionUnit
from .tracebuilder import AbstractTraceBuilder
from ..oob import tracent_pb2 as pb


class AbstractThreadingModel(ABC):

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


class StandardThreadingModel(AbstractThreadingModel):

    class _EuProxy(threading.local):
        eu: ExecutionUnit

    def __init__(self, trace_builder: AbstractTraceBuilder) -> None:
        super(StandardThreadingModel, self).__init__(trace_builder)
        self._eu_proxy = StandardThreadingModel._EuProxy()

    def get_eu(self) -> ExecutionUnit:
        try:
            eu = self._eu_proxy.eu
        except AttributeError:
            eu = ExecutionUnit(self.trace_builder, pb.ExecutionUnit.THREAD)
            self._eu_proxy.eu = eu
        return eu

    def finish(self) -> None:
        try:
            del self._eu_proxy.eu
        except AttributeError:
            pass
