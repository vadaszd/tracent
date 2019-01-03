import threading

from abc import ABC, abstractmethod

from .eu import ExecutionUnit
from .tracebuilder import AbstractTraceBuilder
from ..oob import tracent_pb2 as pb

class AbstractThreadingModel(ABC):

    def __init__(self, traceBuilder: AbstractTraceBuilder) -> None:
        self.traceBuilder = traceBuilder

    @abstractmethod
    def getEu(self) -> ExecutionUnit:
        """ Return an ExecutionUnit according to the policy of the model
        """

    @abstractmethod
    def finish(self) -> None:
        """ Clean up the EU
        """

class StandardThreadingModel(AbstractThreadingModel):

    class _EuProxy(threading.local):
        eu: ExecutionUnit

    def __init__(self, traceBuilder: AbstractTraceBuilder) -> None:
        super(StandardThreadingModel, self).__init__(traceBuilder)
        self._eu_proxy = StandardThreadingModel._EuProxy()

    def getEu(self) -> ExecutionUnit:
        try:
            eu = self._eu_proxy.eu
        except AttributeError:
            eu = ExecutionUnit(self.traceBuilder, pb.ExecutionUnit.THREAD)
            self._eu_proxy.eu = eu
        return eu

    def finish(self) -> None:
        try:
            del self._eu_proxy.eu
        except AttributeError:
            pass
