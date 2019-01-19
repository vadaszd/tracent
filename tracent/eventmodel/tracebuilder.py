from abc import ABC, abstractmethod
from datetime import datetime
from encodings import utf_8 as utf8codec
from uuid import UUID

from fnvhash import fnv1a_32
from google.protobuf.internal.containers import (
    RepeatedCompositeFieldContainer
    )
from typing import (
    Optional, Dict, Union, NamedTuple, Iterable
    )

from .reporter import AbstractReporter
from ..oob import tracent_pb2 as pb

TagType = Union[bool, int, float, str, bytes]


class EventReference(NamedTuple):
    trace_id: UUID
    event_id: bytes


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
    def start_eu(self, eu_id: bytes, eu_type: pb.ExecutionUnit.Type,
                 tags: Dict[str, TagType]) -> None:
        """ Register a new EU with the trace builder

            Events can only be added to registered EUs.
        """

    @abstractmethod
    def finish_eu(self, eu_id: bytes) -> None:
        """  Unregister an EU

            Registered EUs occupy resources, therefore must be cleand up
            when no more events are expected on them.
        """

    @abstractmethod
    def start_trace(self, eu_id: bytes, trace_id: UUID) -> None: pass

    @abstractmethod
    def add_event(self, eu_id: bytes, trace_id: UUID, sequence_number: int,
                  event_type: pb.Event.Type, status: pb.Event.Status,
                  causes: Iterable[EventReference],
                  ) -> None:
        """
        """

    @abstractmethod
    def add_tags(self, eu_id: bytes, event_sequence_number: bytes,
                 tags: Dict[str, TagType]) -> None:
        """ Attach the tags to the given event, overriding conflicting tags.
        """

    @abstractmethod
    def finish_trace(self, eu_id: bytes, trace_id: UUID) -> None: pass


class SimpleTraceBuilder(AbstractTraceBuilder):
    """ A simple trace TraceBuilder

        Build a new RoutedData PDU for every trace fragment
        adding an ExecutionUnit PDU for the referred EU and
        prefixing it with a Metadata PDU if there have been changes to the
        string table since the last publication of it.

        Cache an ExecutionUnit PDU and copy it to to the RoutedData

    """

    class EuState(object):
        eu_pdu: pb.ExecutionUnit
        tracing_data_pdu: pb.TracingData
        trace_fragment_pdu:  pb.TraceFragment
        event_pdu: pb.Event
        time_reference:  datetime
        is_trace_ongoing: bool
        event_tags: Dict[str, TagType]   # Track the last value of each tag key

        def __repr__(self) -> str:
            return repr(self.__dict__)

    string_table: 'StringTable'  # one global isinstance
    eu_states: Dict[bytes, EuState]
    reporter: AbstractReporter

    def __init__(self, reporter: AbstractReporter) -> None:
        self.string_table = StringTable()
        self.reporter = reporter
        self.eu_states = dict()

    def start_eu(self, eu_id: bytes, eu_type: pb.ExecutionUnit.Type,
                 tags: Dict[str, TagType]
                 ) -> None:
        assert eu_id not in self.eu_states
        eu_state = self.eu_states[eu_id] = SimpleTraceBuilder.EuState()
        eu_state.eu_pdu = pb.ExecutionUnit()
        eu_state.eu_pdu.id = eu_id
        eu_state.eu_pdu.type = eu_type
        eu_state.is_trace_ongoing = False
        eu_state.event_tags = dict()
        for key, value in tags.items():
            assert value is not None
            self._add_tag(eu_state.eu_pdu.tags, key, value)

    def finish_eu(self, eu_id: bytes) -> None:
        eu_state = self.eu_states.pop(eu_id)
        assert not eu_state.is_trace_ongoing, eu_state

    def start_trace(self, eu_id: bytes, trace_id: UUID) -> None:
        tracing_data_pdu = pb.TracingData()
        tracing_data_pdu.routing_key = trace_id.bytes   # big-endian
        trace_fragment_pdu = tracing_data_pdu.routed_data.trace_fragments.add()
        trace_fragment_pdu.trace_id = trace_id.bytes  # big-endian
        trace_fragment_pdu.execution_unit_id = eu_id
        trace_fragment_pdu.time_reference.GetCurrentTime()

        eu_state = self.eu_states[eu_id]
        assert not eu_state.is_trace_ongoing, eu_state
        eu_state.is_trace_ongoing = True
        eu_state.tracing_data_pdu = tracing_data_pdu
        eu_state.trace_fragment_pdu = trace_fragment_pdu
        eu_state.time_reference = trace_fragment_pdu.time_reference.ToDatetime()

    def finish_trace(self, eu_id: bytes, trace_id: UUID) -> None:
        eu_state = self.eu_states[eu_id]
        assert eu_state.is_trace_ongoing, eu_state
        eu_state.is_trace_ongoing = False
        eu_state.event_tags.clear()

        trace_fragment_pdu = eu_state.trace_fragment_pdu
        assert trace_fragment_pdu.trace_id == trace_id.bytes, (eu_id, UUID(bytes=trace_fragment_pdu.trace_id), trace_id)

        if self.string_table.is_dirty:
            # Broadcast the string table
            tracing_data_pdu = pb.TracingData()
            self.string_table.save_to(tracing_data_pdu.broadcast_data.strings)
            self._send(tracing_data_pdu)

        tracing_data_pdu = eu_state.tracing_data_pdu
        tracing_data_pdu.routed_data.execution_units.extend([eu_state.eu_pdu])
        self._send(tracing_data_pdu)

    def add_event(self, eu_id: bytes, trace_id: UUID, sequence_number: int,
                  event_type: pb.Event.Type, status: pb.Event.Status,
                  causes: Iterable[EventReference],
                  ) -> None:
        eu_state = self.eu_states[eu_id]
        assert eu_state.is_trace_ongoing, eu_state
        trace_fragment_pdu = eu_state.trace_fragment_pdu
        event_pdu = trace_fragment_pdu.events.add()
        event_pdu.sequence_number = sequence_number
        event_pdu.timestamp.FromTimedelta(datetime.utcnow() -
                                          eu_state.time_reference)
        event_pdu.event_type = event_type
        event_pdu.status = status

        for causing_context in causes:
            event_reference_pdu = event_pdu.causing_events.add()

            if causing_context.trace_id.bytes != trace_fragment_pdu.trace_id:
                # .bytes: big endian byte order
                event_reference_pdu.trace_id = causing_context.trace_id.bytes

            event_reference_pdu.event_id = causing_context.event_id

        eu_state.event_pdu = event_pdu

    def add_tags(self, eu_id: bytes, event_sequence_number: bytes,
                 tags: Dict[str, TagType]) -> None:
        eu_state = self.eu_states[eu_id]
        assert eu_state.is_trace_ongoing, eu_state

        for key, value in tags.items():
            if value == eu_state.event_tags[key]:
                value_to_add = None
            else:
                value_to_add = value
                eu_state.event_tags[key] = value
            self._add_tag(eu_state.event_pdu.tags, key, value_to_add)

    def _add_tag(self, tag_container: 'RepeatedCompositeFieldContainer[pb.Tag]',
                 key: str,
                 value: Optional[TagType],
                 encode_string_values: bool = False
                 ) -> None:

        tag_pdu = tag_container.add()

        try:
            tag_pdu.alias_key = self.string_table.get_alias(key)
        except StringTable.HashCollisionError:
            tag_pdu.string_key = key

        if value is not None:
            if isinstance(value, int):
                tag_pdu.int_value = value
            elif isinstance(value, float):
                tag_pdu.float_value = value
            elif isinstance(value, bool):
                tag_pdu.boolean_value = value
            elif isinstance(value, str):
                if encode_string_values:
                    try:
                        tag_pdu.alias_value = self.string_table.get_alias(key)
                    except StringTable.HashCollisionError:
                        tag_pdu.string_value = key
                else:
                    tag_pdu.string_value = key
            elif isinstance(value, bytes):
                tag_pdu.bytes_value = value
            else:
                raise TypeError("Supported tag value types are int, float, "
                                "boolean, str and bytes, found {}"
                                .format(type(value)))

    def _send(self, tracing_data_pdu: pb.TracingData) -> None:
        serialized_tracing_data = tracing_data_pdu.SerializeToString()
        routing_key = tracing_data_pdu.routing_key
        if routing_key:
            self.reporter.send(routing_key, serialized_tracing_data)
        else:
            self.reporter.broadcast(serialized_tracing_data)


class StringTable(object):
    """ Translate strings into probabilisticly unique aliases
    """
    strings_by_alias: Dict[int, str]
    aliases_by_string: Dict[str, int]
    is_dirty: bool

    class HashCollisionError(ValueError):
        pass

    def __init__(self) -> None:
        self.strings_by_alias = dict()
        self.aliases_by_string = dict()
        self.is_dirty = False

    def get_alias(self, string: str) -> int:
        try:
            alias = self.aliases_by_string[string]
        except KeyError:
            encoded_string, consumed = utf8codec.encode(string)
            assert consumed == len(string)
            alias = fnv1a_32(encoded_string)
            try:
                conflicting_string = self.strings_by_alias[alias]
            except KeyError:
                self.strings_by_alias[alias] = string
                self.aliases_by_string[string] = alias
                self.is_dirty = True
            else:
                raise StringTable.HashCollisionError(
                    "The fnv1a hash {} of the new string '{}' "
                    "collides with that of the existing string "
                    "{}".format(alias, string, conflicting_string))
        return alias

    def save_to(self,
                entries: 'RepeatedCompositeFieldContainer[pb.StringTableEntry]'
                ) -> None:
            for alias, value in self.strings_by_alias.items():
                entry = entries.add()
                entry.alias = alias
                entry.value = value
            self.is_dirty = False
