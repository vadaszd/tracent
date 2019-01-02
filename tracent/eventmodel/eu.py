from uuid import UUID, uuid1
import random
import struct
from itertools import count
from abc import ABC, abstractmethod
from collections import namedtuple

from typing import (
    Optional, Dict, Tuple, NamedTuple, List, Union, Callable
    )
from google.protobuf.timestamp_pb2 import Timestamp

from fnvhash import fnv1a_64, fnv1a_32

from .tracebuilder import AbstractTraceBuilder, TagType
from ..oob import tracent_pb2 as pb


class TraceContext(NamedTuple):
    traceId: bytes
    eventId: bytes


class ExecutionUnit(object):

    id: bytes
    eventSequenceNbr: int
    traceId: UUID
    traceBuilder: AbstractTraceBuilder

    def __init__(self, euType: pb.ExecutionUnit.Type, **tags: TagType) -> None:
        self.id = struct.pack("Q", random.getrandbits(64))
        self.eventSequenceNbr = -1   # This value is used nowhere
        self.nextEventSequenceNbr = 0
        self._generateNextEventId = self._initEventNumbering()
        self._generateNextEventId()

        if globalTraceBuilder is None:
            raise ValueError("Use setTraceBuilder(...) to set a trace builder")
        self.traceBuilder = globalTraceBuilder
        self.traceBuilder.startEU(self.id, euType, tags)
        self.traceId = uuid1()
        self.traceBuilder.startTrace(self.id, self.traceId)

        self.traceBuilder.addEvent(
            self.id, self.traceId, self.nextEventSequenceNbr,
            eventType=pb.Event.CREATE_EU, status=pb.Event.IDLE,
            causingTraceId=None, causingEventId=None, tags=dict())
        self._generateNextEventId()

    def _initEventNumbering(self) -> Callable[[], None]:
        eventCounter = count(0)

        def _generateNextEventId() -> None:
            # Switch the actual event ID to the next event ID
            self.eventSequenceNbr = self.nextEventSequenceNbr

            # Generate a new number for the next event
            self.nextEventSequenceNbr = next(eventCounter)

        return _generateNextEventId

    def startNewTrace(self) -> None:
        self.traceBuilder.finishTrace(self.id, self.traceId)
        self.traceId = uuid1()
        self.traceBuilder.startTrace(self.id, self.traceId)

    def tracePoint(self, eventType: pb.Event.Type, status: pb.Event.Status,
                   causingContext: Optional[TraceContext] = None,
                   switchTrace: bool = True, **tags: TagType
                   ) -> None:
        if causingContext is None:
            causingTraceId = None
            causingEventId = None
        else:
            causingTraceId = causingContext.traceId
            assert causingTraceId is not None
            if switchTrace and causingTraceId != self.traceId:
                self.traceBuilder.finishTrace(self.id, self.traceId)
                self.traceId = UUID(bytes=causingTraceId)
                self.traceBuilder.startTrace(self.id, self.traceId)
            causingEventId = causingContext.eventId

        self.traceBuilder.addEvent(
            self.id, self.traceId, self.nextEventSequenceNbr,
            eventType, status, causingTraceId, causingEventId, tags)
        self._generateNextEventId()

    def _getEventId(self, eventSequenceNbr:int) -> bytes:
        # Apply the fnv1a hash on the Little-endian encoding of the
        # (sequence number, eu-id) tuple
        eventIdInt = fnv1a_64(struct.pack(    # Little-endian encoding
                              "<Q",  eventSequenceNbr) + self.id)
        return struct.pack("<Q", eventIdInt)

    def getTraceContext(self) -> TraceContext:
        return TraceContext(self.traceId.bytes,  # big endian
                            self._getEventId(self.eventSequenceNbr))

    def peek(self) -> TraceContext:
        return TraceContext(self.traceId.bytes,  # big endian
                            self._getEventId(self.nextEventSequenceNbr))

    def addTags(self, **tags: TagType) -> None:
        """ Add the key-value tags to the event most recently created on the EU
        """
        self.traceBuilder.addTags(self.id,
                                 self._getEventId(self.eventSequenceNbr),
                                 tags)

    def finish(self) -> None:
        self.eventId = self.traceBuilder.addEvent(
            self.id, self.traceId, self.nextEventSequenceNbr,
            eventType=pb.Event.FINISH_EU, status=pb.Event.UNKNOWN,
            causingTraceId=None, causingEventId=None, tags=dict())
        self.traceBuilder.finishTrace(self.id, self.traceId)
        self.traceBuilder.finishEU(self.id)


globalTraceBuilder: Optional[AbstractTraceBuilder] = None
def setTraceBuilder(traceBuilder: AbstractTraceBuilder) -> None:
    global globalTraceBuilder
    globalTraceBuilder = traceBuilder
