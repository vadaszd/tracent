from uuid import UUID, uuid1
import random
import struct
from itertools import count


from typing import (Callable, Iterable, Optional)

from fnvhash import fnv1a_64

from .tracebuilder import AbstractTraceBuilder, TagType, TagDict, EventReference
from ..oob import tracent_pb2 as pb


class ExecutionUnit(object):

    # TODO: Avoid dupe EU IDs after a fork, generated both pre- and post-fork
    id: bytes
    event_sequence_number: int
    next_event_sequence_number: int
    latest_event_ref: EventReference
    event_tags: TagDict
    trace_id: UUID
    trace_builder: AbstractTraceBuilder

    def __init__(self, trace_builder: AbstractTraceBuilder,
                 eu_type: pb.ExecutionUnit.Type, **tags: TagType
                 ) -> None:
        self.id = struct.pack("Q", random.getrandbits(64))
        self.event_sequence_number = -1   # This value is used nowhere
        self.next_event_sequence_number = 0
        self.trace_id = uuid1()
        self._generate_next_event_ref = self._init_event_numbering()
        self._generate_next_event_ref()
        self.event_tags = dict()
        self.trace_builder = trace_builder
        self.trace_builder.start_eu(self.id, eu_type, tags)
        self.trace_builder.start_trace(self.id, self.trace_id)

        self.trace_builder.add_event(
            self.id, self.trace_id, self.next_event_sequence_number,
            event_type=pb.Event.CREATE_EU, status=pb.Event.IDLE,
            causes=tuple())
        self._generate_next_event_ref()

    def _init_event_numbering(self) -> Callable[[], None]:
        event_counter = count(0)

        def _generate_next_event_id() -> None:
            # Switch the actual event ID to the next event ID
            self.event_sequence_number = self.next_event_sequence_number

            # Generate a new number for the next event
            self.next_event_sequence_number = next(event_counter)
            self.latest_event_ref = EventReference(
                self.trace_id,
                self._get_event_id(self.event_sequence_number),
                self.id
            )

        return _generate_next_event_id

    def trace_point(self, trace_id: Optional[UUID],
                    event_type: pb.Event.Type,
                    status: pb.Event.Status,
                    causes: Iterable[EventReference] = tuple(),
                    tags: TagDict = dict()
                    ) -> EventReference:
        """ Generate a new event in a trace

        :param trace_id: ID of the trace to continue or None to start a new one
        :param event_type:
        :param status:
        :param causes:
        :param tags:
        :return: a reference to the new event
        """
        self._flush_tags()    # These tags belong to the previous event

        if trace_id is None:
            trace_id = uuid1()

        if self.trace_id != trace_id:
            self.trace_builder.finish_trace(self.id, self.trace_id)
            self.trace_id = trace_id
            self.trace_builder.start_trace(self.id, self.trace_id)

        self.event_tags.update(tags)

        self.trace_builder.add_event(
            self.id, self.trace_id, self.next_event_sequence_number,
            event_type, status, causes)
        self._generate_next_event_ref()
        return self.latest_event_ref

    def _get_event_id(self, event_sequence_number: int) -> bytes:
        # Apply the fnv1a hash on the Little-endian encoding of the
        # (sequence number, eu-id) tuple
        event_id_int = fnv1a_64(struct.pack(    # Little-endian encoding
                              "<Q",  event_sequence_number) + self.id)
        return struct.pack("<Q", event_id_int)

    def get_trace_context(self) -> EventReference:
        return self.latest_event_ref

    def peek(self) -> EventReference:
        """ Pre-view the next event reference.

        Useful for recording blocking send operations.

        :return: A reference to the next event, provided the trace remains the
                    same
        """
        return EventReference(
            self.trace_id,
            self._get_event_id(self.next_event_sequence_number),
            self.id
        )

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
            self.id, self.trace_id, self.next_event_sequence_number,
            event_type=pb.Event.FINISH_EU, status=pb.Event.UNKNOWN,
            causes=list())
        self.trace_builder.finish_trace(self.id, self.trace_id)
        self.trace_builder.finish_eu(self.id)
