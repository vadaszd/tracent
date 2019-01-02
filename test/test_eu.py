#!python3
import unittest
import re
from pprint import pprint
from textwrap import dedent
from uuid import UUID

from typing import List, Tuple, Union

from google.protobuf.json_format import MessageToJson
from google.protobuf.text_format import MessageToString

from tracent.eventmodel import (setTraceBuilder, ExecutionUnit,
                                SimpleTraceBuilder, AbstractReporter)
from tracent.oob import tracent_pb2 as pb


class TestTracingDataHeader(unittest.TestCase):

    def testRoutingInfoCanBeExtracted(self) -> None:
        tracingData = pb.TracingData()
        tracingData.routing_key = b'example routing key'
        serialized = tracingData.SerializeToString()
        routingInfo = pb.TracingDataHeader()
        routingInfo.ParseFromString(serialized)
        assert routingInfo.routing_key == tracingData.routing_key, (
            routingInfo.routing_key, tracingData.routing_key)


class InMemoryReporter(AbstractReporter):

    def __init__(self) -> None:
        self.items: List[str] = list()

    def send(self, routingKey: bytes, tracingData: bytes) -> None:
        self.items.append(self._toText(tracingData))
        # print ("Sent to '{}': \n{}"
        #        .format(UUID(bytes=routingKey).hex, self._toText(tracingData)))

    def broadcast(self, tracingData: bytes) -> None:
        self.items.append(self._toText(tracingData))
        # print ("Broadcast: \n{}".format(self._toText(tracingData)))

    def _toText(self,  tracingData: bytes) -> str:
        tracingDataPDU = pb.TracingData()
        tracingDataPDU.ParseFromString(tracingData)
        return MessageToString(tracingDataPDU)


class TestEU(unittest.TestCase):

    def setUp(self) -> None:
        self.reporter = InMemoryReporter()
        setTraceBuilder(SimpleTraceBuilder(self.reporter))

    def testCreateAndDestroyEU(self) -> None:
        eu = ExecutionUnit(pb.ExecutionUnit.PROCESS,
                           tagBoolean=True, tagInt=123,
                           tagFloat=3.14, tagString="String tag",
                           tagBytes=b"bytes tag 7")
        eu.finish()
        expectedBroadcast = dedent("""\
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
        expectedRouted = dedent("""\
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
        actualBroadcast = dedent(self.reporter.items[0])
        assert actualBroadcast == expectedBroadcast, actualBroadcast
        actualRouted = self.reporter.items[1]
        assert re.match(expectedRouted, actualRouted), actualRouted

    def testCrossEuTrace(self) -> None:
        eu1 = ExecutionUnit(pb.ExecutionUnit.PROCESS)
        eu2 = ExecutionUnit(pb.ExecutionUnit.PROCESS)

        eu1.startNewTrace()
        eu1.tracePoint(pb.Event.OT_START_SPAN, pb.Event.BUSY)

        # This is not the intended way of using peek(). Our goal here is
        # to test peek() looks ahead correctly
        traceContext = eu1.peek()
        eu1.tracePoint(pb.Event.OT_START_SPAN, pb.Event.IDLE)
        assert traceContext == eu1.getTraceContext()

        eu2.tracePoint(pb.Event.OT_START_SPAN, pb.Event.BUSY,
                       causingContext=eu1.getTraceContext())

        # The correct use case for peek(): model a blocking send operation
        # The context returned by peek() refers to the send event that is
        # just *going* to happen. We need to extract this context because it
        # needs to be injected into the msg, which will be transmitted
        # in a blocking operation. That means the send event will only be
        # created after that operation completed.
        ctxOfSend = eu2.peek()
        # The receive event; it will refer to the send event
        eu1.tracePoint(pb.Event.OT_START_SPAN, pb.Event.BUSY,
                       causingContext=ctxOfSend)
        # The send event
        eu2.tracePoint(pb.Event.OT_START_SPAN, pb.Event.IDLE)

        eu1.tracePoint(pb.Event.OT_START_SPAN, pb.Event.IDLE,
                       )
        eu2.finish()
        eu1.finish()
        pprint (self.reporter.items)

if __name__ == '__main__':
    unittest.main()
"""
"""
