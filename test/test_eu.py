#!python3
import unittest
import re
from pprint import pprint
from textwrap import dedent

from typing import List

# noinspection PyPackageRequirements
from google.protobuf.text_format import MessageToString

from tracent.eventmodel.eu import ExecutionUnit
from tracent.eventmodel.reporter import AbstractReporter
from tracent.eventmodel.tracebuilder import SimpleTraceBuilder

from tracent.oob import tracent_pb2 as pb


class TestTracingDataHeader(unittest.TestCase):

    def testRoutingInfoCanBeExtracted(self) -> None:
        serialized_tracing_data = pb.TracingData()
        serialized_tracing_data.routing_key = b'example routing key'
        serialized = serialized_tracing_data.SerializeToString()
        routingInfo = pb.TracingDataHeader()
        routingInfo.ParseFromString(serialized)
        assert routingInfo.routing_key == serialized_tracing_data.routing_key, (
            routingInfo.routing_key, serialized_tracing_data.routing_key)


class InMemoryReporter(AbstractReporter):

    def __init__(self) -> None:
        self.items: List[str] = list()

    def send(self, routing_key: bytes, serialized_tracing_data: bytes) -> None:
        self.items.append(self._to_text(serialized_tracing_data))
        # print ("Sent to '{}': \n{}"
        #        .format(UUID(bytes=routing_key).hex, self._to_text(serialized_tracing_data)))

    def broadcast(self, serialized_tracing_data: bytes) -> None:
        self.items.append(self._to_text(serialized_tracing_data))
        # print ("Broadcast: \n{}".format(self._to_text(serialized_tracing_data)))

    @staticmethod
    def _to_text(serialized_tracing_data: bytes) -> str:
        tracing_data_pdu = pb.TracingData()
        tracing_data_pdu.ParseFromString(serialized_tracing_data)
        return MessageToString(tracing_data_pdu)


class TestEU(unittest.TestCase):

    def setUp(self) -> None:
        self.reporter = InMemoryReporter()
        self.trace_builder = SimpleTraceBuilder(self.reporter)

    def testCreateAndDestroyEU(self) -> None:
        eu = ExecutionUnit(self.trace_builder, pb.ExecutionUnit.PROCESS,
                           tagBoolean=True, tagInt=123,
                           tagFloat=3.14, tagString="String tag",
                           tagBytes=b"bytes tag 7")
        eu.finish()
        # FIXME: order of strings is non-deterministic
        expected_broadcast = dedent("""\
            broadcast_data {
              strings {
                alias: 3191348081
                value: "tagBoolean"
              }
              strings {
                alias: 3350542684
                value: "tagInt"
              }
              strings {
                alias: 465169687
                value: "tagFloat"
              }
              strings {
                alias: 1042072278
                value: "tagString"
              }
              strings {
                alias: 1660915494
                value: "tagBytes"
              }
            }
            """)
        expected_routed = dedent("""\
            routing_key: ".+"
            routed_data {
              trace_fragments {
                trace_id: ".+"
                execution_unit_id: ".+"
                time_reference {
                  seconds: \d+
                  nanos: \d+
                }
                events {
                  timestamp {
                    nanos: \d+
                  }
                  status: IDLE
                }
                events {
                  sequence_number: 1
                  timestamp {
                    nanos: \d+
                  }
                  event_type: FINISH_EU
                }
              }
              execution_units {
                id: ".+"
                type: PROCESS
                tags {
                  alias_key: 3191348081
                  int_value: 1
                }
                tags {
                  alias_key: 3350542684
                  int_value: 123
                }
                tags {
                  alias_key: 465169687
                  float_value: 3.14
                }
                tags {
                  alias_key: 1042072278
                  string_value: "tagString"
                }
                tags {
                  alias_key: 1660915494
                  bytes_value: "bytes tag 7"
                }
              }
            }
            """)
        actual_broadcast = dedent(self.reporter.items[0])
        assert actual_broadcast == expected_broadcast, actual_broadcast
        actual_routed = self.reporter.items[1]
        assert re.match(expected_routed, actual_routed), actual_routed

    def testCrossEuTrace(self) -> None:
        eu1 = ExecutionUnit(self.trace_builder, pb.ExecutionUnit.PROCESS)
        eu2 = ExecutionUnit(self.trace_builder, pb.ExecutionUnit.PROCESS)

        eu1.trace_point(trace_id=None,
                        event_type=pb.Event.OT_START_SPAN,
                        status=pb.Event.BUSY
                        )
        trace_id = eu1.trace_id
        # This is not the intended way of using peek(). Our goal here is
        # to test peek() looks ahead correctly
        event_reference = eu1.peek()
        eu1.trace_point(trace_id=eu1.trace_id,  # continue the trace
                        event_type=pb.Event.OT_FINISH_SPAN,
                        status=pb.Event.IDLE)
        assert event_reference == eu1.get_trace_context()

        eu2.trace_point(trace_id=eu1.trace_id,  # continue the trace
                        event_type=pb.Event.OT_START_SPAN,
                        status=pb.Event.BUSY,
                        causes=[eu1.get_trace_context()])

        # The correct use case for peek(): model a blocking send operation
        # The context returned by peek() refers to the send event that is
        # just *going* to happen. We need to extract this context because it
        # needs to be injected into the msg, which will be transmitted
        # in a blocking operation. That means the send event will only be
        # created after that operation completed.
        send_event = eu2.peek()
        # The receive event; it will refer to the send event
        eu1.trace_point(trace_id=trace_id,  # continue the trace
                        event_type=pb.Event.OT_START_SPAN,
                        status=pb.Event.BUSY,
                        causes=[send_event])
        # The send event
        eu2.trace_point(trace_id=trace_id,  # continue the trace
                        event_type=pb.Event.OT_FINISH_SPAN,
                        status=pb.Event.IDLE
                        )

        eu1.trace_point(trace_id=trace_id,  # continue the trace
                        event_type=pb.Event.OT_FINISH_SPAN,
                        status=pb.Event.IDLE,
                       )
        eu2.finish()
        eu1.finish()
        pprint([str(item) for item in self.reporter.items])


if __name__ == '__main__':
    unittest.main()
"""
"""
