import uuid
import random
from itertools import count
from abc import ABC
from collections import namedtuple
from typing import Dict, Tuple, List

from fnvhash import fnv1a_64, fnv1a_32

from . import tracent_pb2 as pb

TraceContext = namedtuple("TraceContext", ["traceID", "eventId"])


class ExecutionUnit(object):

    def __init__(self, euType: int, **kwargs):
        self.id = random.getrandbits(64)
        self.eventSequenceNbr = self.nextEventSequenceNbr = None
        self._generateNextEventId = self._initEventNumbering()
        self._generateNextEventId()

        self.traceBuilder = globalTraceBuilder
        self.traceBuilder.startEU(self.id, euType, tags)
        self.traceId = uuid.uuid1().int
        self.traceBuilder.startTrace(self.traceId)

        self.traceBuilder.addEvent(
            self.traceId, self.id, self.nextEventSequenceNbr,
            eventType=pb.Event.CREATE_EU,
            causingTraceId=None, causingEventId=None, tags=dict())
        self._generateNextEventId()

    def _initEventNumbering(self) -> NoneTye:
        eventSequenceNumber = count(0)

        def _generateNextEventId(self):
            # Switch the actual event ID to the next event ID
            self.eventSequenceNbr = self.nextEventSequenceNbr

            # Generate a new number for the next event
            self.nextEventSequenceNbr = next(self.eventSequenceNumber)

        return _generateNextEventId

    def tracePoint(self, eventType: int, status: int,
                   causingContext: TraceContext = None,
                   switchTrace: bool = True, **tags
                   ):
        if causingContext is None:
            causingTraceId = None
            causingEventId = None
        else:
            causingTraceId = causingContext.traceId
            assert causingTraceId is not None
            if switchTrace and causingTraceId != self.traceId:
                self.traceBuilder.finishTrace(self.traceId)
                self.traceId = causingTraceId
                self.traceBuilder.startTrace(self.traceId)
            causingEventId = causingContext.eventId

        self.traceBuilder.addEvent(
            self.traceId, self.id, self.nextEventSequenceNbr,
            eventType, causingTraceId, causingEventId, tags)
        self._generateNextEventId()

    def _getEventId(self, eventSequenceNbr):
        # Apply the fnv1a hash on the Little-endian encoding of the
        # (sequence number, eu-id) tuple
        eventIdInt = fnv1a_64(struct.pack(    # Little-endian encoding
                              "<QQ",  eventSequenceNbr, self.id))
        return struct.pack("<Q", eventIdInt)

    def getTraceContext():
        return TraceContext(self.traceId,
                            self._getEventId(self.eventSequenceNbr))

    def peek():
        return TraceContext(self.traceId,
                            self._getEventId(self.nextEventSequenceNbr))

    def addTag(self, **tags):
        """ Add the key-value tags to the event most recently created on the EU
        """
        self.traceBuilder.addTag(self.id, self.eventSequenceNbr, **tags)

    def finish(self):
        self.eventId = self.traceBuilder.addEvent(
            self.traceId, self.id, next(self.eventSequenceNumber),
            eventType=pb.Event.FINISH_EU,
            causingTraceId=None, causingEventId=None, tags=dict())
        self.traceBuilder.finishTrace(self.traceId)
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
    def startEU(self, euId: int, euType: int, tags: dict):
        """ Register a new EU with the trace builder

            Events can only be added to registered EUs.
        """

    @abstractmethod
    def finishEU(self, euId: int):
        """  Unregister an EU

            Registered EUs occupy resources, therefore must be cleand up
            when no more events are expected on them.
        """

    @abstractmethod
    def startTrace(self, euId: int, traceId: byte): pass

    @abstractmethod
    def addEvent(self, traceId: byte, euId: int, sequence_number: int,
                 eventType: int, status: int,
                 causingTraceId: byte, causingEventId: byte, tags: dict):
        """
        """

    @abstractmethod
    def addTag(self, euId: int, eventSequenceNbr: byte, tags: dict):
        """ Attach the tags to the given event, overriding conflicting tags.
        """

    @abstractmethod
    def finishTrace(self, euId: int): pass



class SimpleTraceBuilder(AbstractTraceBuilder):
    """ A simple trace TraceBuilder

        Build a new Payload PDU for every trace fragment
        adding an ExecutionUnit PDU for the referred EU and
        prefixing it with a Metadata PDU if there have been changes to the
        string table since the last publication of it.

        Cache an ExecutionUnit PDU and copy it to to the Payload

    """

    # stringTable: StringTable  # one global isinstance
    # euPDUs: Dict[int, ]
    # ExecutionUnit # one per EU, life-cycle is managed by startEU/finishEU
    # TracingData  # one per EU, life-cycle is managed by startTrace/finishTrace
    #     Payload
    #         TraceFragment
    #             Event
    #         ExecutionUnit  # copied on finishTrace

    def __init__(self):
        self.stringTable = StringTable()

    def startEU(self, executionUnit):
        self.traceBuilder.startTrace(None)

    def startTrace(self, executionUnit, traceId):
        if traceId is None:
            traceId = uuid.uuid1().int

        self.partitionNumber = self.computePartitionNumber(traceId)
        self.traceFragment = pb.TraceFragment()

        (self.traceFragment.trace_id.hi,
         self.traceFragment.trace_id.lo) = traceId

        self.traceFragment.execution_unit_id = self.executionUnit.id
        self.traceFragment.time_reference.GetCurrentTime()

    def addEvent(self, executionUnit, sequence_number, eventType, status,
                 causes, **tags):
        event = self.traceFragment.events.add()
        event.sequence_number = sequence_number
        event.lag = GetCurrentTime() - self.traceFragment.time_reference
        event.event_type = eventType
        event.status = status

        for causingEventTraceId, causingEventHash in causes:
            event.causing_events.add(trace_id=causingEventTraceId,
                                     event_hash=causingEventHash)

        self.addTags(self.event.tags, tags, self.partitionNumber)
        # string alias in tag may be wrong!

    def finishTrace(self, executionUnit):
        self.addTraceFragment(self.partitionNumber,
                                          self.executionUnit,
                                          self.traceFragment)


class StringTable(object):
    """ Translate strings into probabilisticly unique aliases
    """
    stringByAlias: Dict[int, str]
    aliasByString: Dict[str, int]

    def __init__(self):
        self.stringByAlias = dict()
        self.aliasByString = dict()

    def getAlias(string: str) -> int:
        try:
            alias = self.aliasByString[string]
        except KeyError:
            alias = fnv1a_32(string)
            try:
                conflictingString = self.stringByAlias[alias]
            except KeyError:
                self.stringByAlias[alias] = string
                self.aliasByString[string] = alias
            else:
                raise ValueError("The fnv1a hash {} of the new string '{}' "
                                 "collides with that of the existing string "
                                 "{}".format(alias, string, conflictingString))
        return alias

globalTraceBuilder = SimpleTraceBuilder()


class TraceBuffer(object):
    """ Buffer complete TraceFragments in TracingInfo objects until sending.

        Before sending, execution unit info and the string registry is attached
        to the TracingInfo.

        A TraceBuffer can be shared by multiple TraceBuilder objects and thus
        multiple EUs.
    """

    def __init__(self, numPartitions=1):
        self.numPartitions = numPartitions

        # For reverse lookup, a dict per partition
        self.stringRegistry = defaultdict(dict)

        # EUs to report about periodically, by partition number
        # TODO: track on which partition the EU has not been sent yet
        self.executionUnits = defaultdict(set)

        self.tracingInfos = defaultdict(pb.TracingInfo)

    def _getStringIndex(self, partitionNumber, string):
        stringRegistry = self.stringRegistry[partitionNumber]
        try:
            i = stringRegistry[string]
        except KeyError:
            i = len(stringRegistry)
            stringRegistry[string] = i
            tracingInfo = self.tracingInfos[partitionNumber]
            tracingInfo.strings.append(string)
        return i

    def addTraceFragment(self, partitionNumber, executionUnit, traceFragment):
        self.executionUnits[partitionNumber].add(executionUnit)
        tracingInfo = self.tracingInfos[partitionNumber]
        tracingInfo.trace_fragments.add().CopyFrom(traceFragment)

    def computePartitionNumber(self, traceId):
        return traceId % self.numPartitions

    def flush(self, write):
        """ Complete the tracingInfos and output them

            Fill in the
                - partition_number
                - num_strings
                - execution_units
            Serialize and write it out

            @arg write: a function to perform the output; should take a
                        partitionNumber and the data for that partition
        """
        for partitionNumber, tracingInfo in self.tracingInfos.items():
            tracingInfo.partition_number = partitionNumber
            tracingInfo.num_strings = len(self.stringRegistry[partitionNumber])
            for eu in self.executionUnits:
                pb_eu = tracingInfo.execution_units.add(id=eu.id,
                                                        type=eu.euType)
                addTags(pb_eu.tags, tags, partitionNumber)

        for partitionNumber, tracingInfo in self.tracingInfos.items():
            write(partitionNumber, tracingInfo.SerializeToString())

        self.stringRegistry.clear()
        self.executionUnits.clear()
        self.tracingInfos.clear()

    def addTags(self, tagsField, tags, partitionNumber):
        for key, value in tags.items():
            tag = tagsField.add()
            tag.key_alias = self._getStringIndex(partitionNumber, key)

            if isinstance(value, int):
                tag.int_value = value
            elif isinstance(value, float):
                tag.float_value = value
            elif isinstance(value, bool):
                tag.boolean_value = value
            elif isinstance(value, str):
                tag.string_alias_value = self._getStringIndex(partitionNumber,
                                                              value)
            elif isinstance(value, bytes):
                tag.bytes_value = value
            else:
                raise TypeError("Supported tag value types are int, float, "
                                "boolean, str and bytes, found {}"
                                .format(type(value)))
