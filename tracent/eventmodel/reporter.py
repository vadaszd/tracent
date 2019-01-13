
from abc import ABC, abstractmethod


class AbstractReporter(ABC):
    """ A partitioned message stream that can be used to report trace fragments
    """

    @abstractmethod
    def send(self, routing_key: bytes, serialized_tracing_data: bytes) -> None:
        """ Send the serialized_tracing_data over a potentially partitioned data stream.

            @param routing_key: the transport may use this data as partitioning
                key. All serialized_tracing_data messages having the same routing_key
                MUST end up at the same destination (partition).

            @param serialized_tracing_data: a byte-array representing a piece of a trace
        """

    @abstractmethod
    def broadcast(self, serialized_tracing_data: bytes) -> None:
        """ Broadcast the serialized_tracing_data over a potentially partitioned data stream.

            @param serialized_tracing_data: A byte-array containing data relevant trace for
                several traces. It MUST be sent to all destinations even in
                partitioned data stream scenarios.

        """
