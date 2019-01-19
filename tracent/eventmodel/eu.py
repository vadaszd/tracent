from uuid import UUID, uuid1
import random
import struct
from itertools import count


from typing import (Dict, Callable, Iterable)

from fnvhash import fnv1a_64

from .tracebuilder import AbstractTraceBuilder, TagType, EventReference
from ..oob import tracent_pb2 as pb


class ExecutionUnit(object):

    id: bytes
    event_sequence_number: int
    event_tags: Dict[str, TagType]
    trace_id: UUID
    trace_builder: AbstractTraceBuilder

    def __init__(self, trace_builder: AbstractTraceBuilder,
                 eu_type: pb.ExecutionUnit.Type, **tags: TagType
                 ) -> None:
        self.id = struct.pack("Q", random.getrandbits(64))
        self.event_sequence_number = -1   # This value is used nowhere
        self.nextEventSequenceNbr = 0
        self._generate_next_event_id = self._init_event_numbering()
        self._generate_next_event_id()
        self.event_tags = dict()
        self.trace_builder = trace_builder
        self.trace_builder.start_eu(self.id, eu_type, tags)
        self.trace_id = uuid1()
        self.trace_builder.start_trace(self.id, self.trace_id)

        self.trace_builder.add_event(
            self.id, self.trace_id, self.nextEventSequenceNbr,
            event_type=pb.Event.CREATE_EU, status=pb.Event.IDLE,
            causes=tuple())
        self._generate_next_event_id()

    def _init_event_numbering(self) -> Callable[[], None]:
        event_counter = count(0)

        def _generate_next_event_id() -> None:
            # Switch the actual event ID to the next event ID
            self.event_sequence_number = self.nextEventSequenceNbr

            # Generate a new number for the next event
            self.nextEventSequenceNbr = next(event_counter)

        return _generate_next_event_id

    def start_new_trace(self) -> None:
        self.trace_builder.finish_trace(self.id, self.trace_id)
        self.trace_id = uuid1()
        self.trace_builder.start_trace(self.id, self.trace_id)

    def switch_trace(self, new_context: EventReference) -> None:
        if self.trace_id != new_context.trace_id:
            self.trace_builder.finish_trace(self.id, self.trace_id)
            self.trace_id = new_context.trace_id
            self.trace_builder.start_trace(self.id, self.trace_id)

    def trace_point(self, event_type: pb.Event.Type, status: pb.Event.Status,
                    causes: Iterable[EventReference] = tuple(),
                    tags: Dict[str, TagType] = dict()
                    ) -> None:
        self._flush_tags()    # These tags belong to the previous event
        self.event_tags.update(tags)

        self.trace_builder.add_event(
            self.id, self.trace_id, self.nextEventSequenceNbr,
            event_type, status, causes)
        self._generate_next_event_id()

    def _get_event_id(self, event_sequence_number: int) -> bytes:
        # Apply the fnv1a hash on the Little-endian encoding of the
        # (sequence number, eu-id) tuple
        event_id_int = fnv1a_64(struct.pack(    # Little-endian encoding
                              "<Q",  event_sequence_number) + self.id)
        return struct.pack("<Q", event_id_int)

    def get_trace_context(self) -> EventReference:
        return EventReference(self.trace_id,
                              self._get_event_id(self.event_sequence_number))

    def peek(self) -> EventReference:
        return EventReference(self.trace_id,
                              self._get_event_id(self.nextEventSequenceNbr))

    def add_tags(self, **tags: TagType) -> None:
        """ Add the key-value tags to the event most recently created on the EU

            Multiple tags with the same key added in different calls to
            `add_tags()` or in `trace_point()` are filtered out and the value
            associated with the last key will take effect.
        """
        #  The tags are added lazily, buffering them in event_tags just
        #  until the next event needs to be created, so that key collisions can
        #  be detected
        self.event_tags.update(tags)

    def _flush_tags(self) -> None:
        self.trace_builder.add_tags(
            self.id,
            self._get_event_id(self.event_sequence_number),
            self.event_tags)
        self.event_tags.clear()

    def finish(self) -> None:
        self._flush_tags()
        self.trace_builder.add_event(
            self.id, self.trace_id, self.nextEventSequenceNbr,
            event_type=pb.Event.FINISH_EU, status=pb.Event.UNKNOWN,
            causes=list())
        self.trace_builder.finish_trace(self.id, self.trace_id)
        self.trace_builder.finish_eu(self.id)
