
from abc import ABC, abstractmethod

class AbstractReporter(ABC):
    """ A partitioned message stream that can be used to report trace fragments
    """

    @abstractmethod
    def send(self, routingKey: bytes, tracingData: bytes) -> None:
        """ Send the tracingData over a potentially partitioned data stream.

            @param routingKey: the transport may use this data as partitioning
                key. All tracingData messages having the same routingKey
                MUST end up at the same destination (partition).

            @param tracingData: a byte-array representing a piece of a trace
        """

    @abstractmethod
    def broadcast(self, tracingData: bytes) -> None:
        """ Broadcast the tracingData over a potentially partitioned data stream.

            @param tracingData: A byte-array containing data relevant trace for
                several traces. It MUST be sent to all destinations even in
                partitioned data stream scenarios.

        """
