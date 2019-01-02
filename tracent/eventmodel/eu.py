from uuid import UUID, uuid1
import random
import struct
from datetime import datetime
from itertools import count
from abc import ABC, abstractmethod
from collections import namedtuple

from typing import (
    Optional, Dict, Tuple, NamedTuple, List, Union, Callable
    )
from google.protobuf.internal.containers import (
    RepeatedCompositeFieldContainer
    )
from google.protobuf.timestamp_pb2 import Timestamp

from fnvhash import fnv1a_64, fnv1a_32

from ..oob import tracent_pb2 as pb


TagType = Union[bool, int, float, str, bytes]

# class TraceId(object):
#     hi: int
#     lo: int
#
#     def __init__(self, traceId: int) -> None:
#         self.lo = traceId & 0xFFFFFFFFFFFFFFFF
#         self.hi = traceId >> 64


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

        self.traceBuilder = globalTraceBuilder
        self.traceBuilder.startEU(self.id, euType, tags)
        self.startNewTrace()

        self.traceBuilder.addEvent(
            self.id, self.traceId, self.nextEventSequenceNbr,
            eventType=pb.Event.CREATE_EU, status=pb.Event.BUSY,
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
                              "<QQ",  eventSequenceNbr, self.id))
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
            eventType=pb.Event.FINISH_EU, status=pb.Event.IDLE,
            causingTraceId=None, causingEventId=None, tags=dict())
        self.traceBuilder.finishTrace(self.id, self.traceId)
        self.traceBuilder.finishEU(self.id)


class AbstractTraceBuilder(ABC):
    """ Builds TracingInfo protocol data units

        Shared by all EUs

        Policies:
        - How do we populate TracingInfo PDUs?
        - How many and what kind of EUs and trace fragments we place in it?
        - How long do we retain it (waiting for additional data to place in it)
            before sending it to the collector?
        - How many TracingInfo PDUs do we keep around and how do we select the
            one to add a new EU or TF to?
        - How long do we keep entries in the string registry?

        A trace fragment contains some of the events of a given trace at a
        given EU.
    """

    @abstractmethod
    def startEU(self, euId: bytes, euType: pb.ExecutionUnit.Type,
                tags: Dict[str, TagType]) -> None:
        """ Register a new EU with the trace builder

            Events can only be added to registered EUs.
        """

    @abstractmethod
    def finishEU(self, euId: bytes) -> None:
        """  Unregister an EU

            Registered EUs occupy resources, therefore must be cleand up
            when no more events are expected on them.
        """

    @abstractmethod
    def startTrace(self, euId: bytes, traceId: UUID) -> None: pass

    @abstractmethod
    def addEvent(self, euId: bytes, traceId: UUID, sequence_number: int,
                 eventType: pb.Event.Type, status: pb.Event.Status,
                 causingTraceId: Optional[bytes],
                 causingEventId: Optional[bytes],
                 tags: Dict[str, TagType]) -> None:
        """
        """

    @abstractmethod
    def addTags(self, euId: bytes, eventSequenceNbr: bytes,
               tags: Dict[str, TagType]) -> None:
        """ Attach the tags to the given event, overriding conflicting tags.
        """

    @abstractmethod
    def finishTrace(self, euId: bytes, traceId: UUID) -> None: pass



class SimpleTraceBuilder(AbstractTraceBuilder):
    """ A simple trace TraceBuilder

        Build a new RoutedData PDU for every trace fragment
        adding an ExecutionUnit PDU for the referred EU and
        prefixing it with a Metadata PDU if there have been changes to the
        string table since the last publication of it.

        Cache an ExecutionUnit PDU and copy it to to the RoutedData

    """

    class EuState(object):
        euPDU: pb.ExecutionUnit
        tracingDataPDU: pb.TracingData
        traceFragmentPDU:  pb.TraceFragment
        eventPDU: pb.Event
        timeReference:  datetime
        isTraceOngoing: bool

    stringTable: StringTable  # one global isinstance
    euStates: Dict[bytes, EuState]
    reporter: Reporter
    # ExecutionUnit # one per EU, life-cycle is managed by startEU/finishEU
    # TracingData  # one per EU, life-cycle is managed by startTrace/finishTrace
    #     RoutedData
    #         TraceFragment
    #             Event
    #         ExecutionUnit  # copied on finishTrace

    def __init__(self, reporter: Reporter) -> None:
        self.stringTable = StringTable()
        self.reporter = reporter
        self.euStates = dict()

    def startEU(self, euId: bytes, euType: pb.ExecutionUnit.Type,
                tags: Dict[str, TagType]
                ) -> None:
        assert euId not in self.euStates
        euState = self.euStates[euId] = SimpleTraceBuilder.EuState()
        euState.euPDU = pb.ExecutionUnit()
        euState.euPDU.id = euId
        euState.euPDU.type = euType
        euState.isTraceOngoing = False
        self._addTags(euState.euPDU.tags, tags)

    def finishEU(self, euId: bytes) -> None:
        euState = self.euStates.pop(euId)
        assert not euState.isTraceOngoing, euState

    def startTrace(self, euId: bytes, traceId: UUID) -> None:
        tracingDataPDU = pb.TracingData()
        tracingDataPDU.routing_key = traceId.bytes   # big-endian
        traceFragmentPDU = tracingDataPDU.routed_data.trace_fragments.add()
        traceFragmentPDU.trace_id = traceId.bytes  # big-endian
        traceFragmentPDU.execution_unit_id = euId
        traceFragmentPDU.time_reference.GetCurrentTime()

        euState = self.euStates[euId]
        assert not euState.isTraceOngoing, euState
        euState.isTraceOngoing = True
        euState.tracingDataPDU = tracingDataPDU
        euState.traceFragmentPDU = traceFragmentPDU
        euState.timeReference = traceFragmentPDU.time_reference.ToDatetime()

    def finishTrace(self, euId: bytes, traceId: UUID) -> None:
        euState = self.euStates[euId]
        assert euState.isTraceOngoing, euState
        euState.isTraceOngoing = False

        traceFragmentPDU = euState.traceFragmentPDU
        assert traceFragmentPDU.trace_id == traceId.bytes, (euId,
                 UUID(bytes=traceFragmentPDU.trace_id), traceId)

        if self.stringTable.isDirty:
            # Broadcast the string table
            tracingDataPDU = pb.TracingData()
            self.stringTable.saveTo(tracingDataPDU.broadcast_data.strings)
            self._send(tracingDataPDU)

        tracingDataPDU = euState.tracingDataPDU
        tracingDataPDU.routed_data.execution_units.extend([euState.euPDU])
        self._send(tracingDataPDU)

    def addEvent(self, euId: bytes, traceId: UUID, sequence_number: int,
                 eventType: pb.Event.Type, status: pb.Event.Status,
                 causingTraceId: Optional[bytes],
                 causingEventId: Optional[bytes],
                 tags: Dict[str, TagType]
                 ) -> None:
        euState = self.euStates[euId]
        assert euState.isTraceOngoing, euState
        traceFragmentPDU = euState.traceFragmentPDU
        eventPDU = traceFragmentPDU.events.add()
        eventPDU.sequence_number = sequence_number
        eventPDU.timestamp.FromTimedelta(datetime.utcnow() -
                                         euState.timeReference)
        eventPDU.event_type = eventType
        eventPDU.status = status

        if causingTraceId is None:
            assert causingEventId is None
        else:
            assert causingEventId is not None
            eventReferencePDU = eventPDU.causing_events.add()

            if causingTraceId != traceFragmentPDU.trace_id:
                eventReferencePDU.trace_id=causingTraceId

            eventReferencePDU.event_id=causingEventId

        self._addTags(eventPDU.tags, tags)

        euState.eventPDU = eventPDU

    def addTags(self, euId: bytes, eventSequenceNbr: bytes,
               tags: Dict[str, TagType]) -> None:
        euState = self.euStates[euId]
        assert euState.isTraceOngoing, euState
        self._addTags(euState.eventPDU.tags, tags)

    def _addTags(self, tagContainer: RepeatedCompositeFieldContainer[pb.Tag],
                 tags: Dict[str, TagType],
                 encodeStringValues: bool=False) -> None:

        for key, value in tags.items():
            tagPDU = tagContainer.add()

            try:
                tagPDU.alias_key = self.stringTable.getAlias(key)
            except StringTable.HashCollisionError as e:
                tagPDU.string_key = key

            if isinstance(value, int):
                tagPDU.int_value = value
            elif isinstance(value, float):
                tagPDU.float_value = value
            elif isinstance(value, bool):
                tagPDU.boolean_value = value
            elif isinstance(value, str):
                if encodeStringValues:
                    try:
                        tagPDU.alias_value = self.stringTable.getAlias(key)
                    except StringTable.HashCollisionError as e:
                        tagPDU.string_value = key
                else:
                    tagPDU.string_value = key
            elif isinstance(value, bytes):
                tagPDU.bytes_value = value
            else:
                raise TypeError("Supported tag value types are int, float, "
                                "boolean, str and bytes, found {}"
                                .format(type(value)))

    def _send(self, tracingDataPDU: pb.TracingData) -> None:
        payload = tracingDataPDU.SerializeToString()
        routing_key = tracingDataPDU.routing_key
        if routing_key:
            self.reporter.send(routing_key, payload)
        else:
            self.reporter.broadcast(payload)

class StringTable(object):
    """ Translate strings into probabilisticly unique aliases
    """
    stringByAlias: Dict[int, str]
    aliasByString: Dict[str, int]
    isDirty: bool

    class HashCollisionError(ValueError): pass

    def __init__(self) -> None:
        self.stringByAlias = dict()
        self.aliasByString = dict()
        self.isDirty = False

    def getAlias(self, string: str) -> int:
        try:
            alias = self.aliasByString[string]
        except KeyError:
            alias = fnv1a_32(string)
            try:
                conflictingString = self.stringByAlias[alias]
            except KeyError:
                self.stringByAlias[alias] = string
                self.aliasByString[string] = alias
                self.isDirty = True
            else:
                raise StringTable.HashCollisionError(
                    "The fnv1a hash {} of the new string '{}' "
                    "collides with that of the existing string "
                    "{}".format(alias, string, conflictingString))
        return alias

    def saveTo(self,
               entries: RepeatedCompositeFieldContainer[pb.StringTableEntry]
               ) -> None:
            for alias, value in self.stringByAlias.items():
                entry = entries.add()
                entry.alias = alias
                entry.value = value
            self.isDirty = False


globalTraceBuilder: AbstractTraceBuilder = SimpleTraceBuilder()


class Reporter(ABC):
    def send(self, routingKey: bytes, tracingDataPDU: bytes) -> None:
        pass

    def broadcast(self, tracingDataPDU: bytes) -> None:
        pass
