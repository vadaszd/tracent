# @generated by generate_proto_mypy_stubs.py.  Do not edit!
from google.protobuf.descriptor import (
    EnumDescriptor as google___protobuf___descriptor___EnumDescriptor,
)

from google.protobuf.duration_pb2 import (
    Duration as google___protobuf___duration_pb2___Duration,
)

from google.protobuf.internal.containers import (
    RepeatedCompositeFieldContainer as google___protobuf___internal___containers___RepeatedCompositeFieldContainer,
)

from google.protobuf.message import (
    Message as google___protobuf___message___Message,
)

from google.protobuf.timestamp_pb2 import (
    Timestamp as google___protobuf___timestamp_pb2___Timestamp,
)

from typing import (
    Iterable as typing___Iterable,
    List as typing___List,
    Optional as typing___Optional,
    Text as typing___Text,
    Tuple as typing___Tuple,
    cast as typing___cast,
)


class TracingData(google___protobuf___message___Message):
    routing_key = ... # type: bytes
    sender_id = ... # type: bytes

    @property
    def routed_data(self) -> RoutedData: ...

    @property
    def broadcast_data(self) -> BroadcastData: ...

    def __init__(self,
        routing_key : typing___Optional[bytes] = None,
        sender_id : typing___Optional[bytes] = None,
        routed_data : typing___Optional[RoutedData] = None,
        broadcast_data : typing___Optional[BroadcastData] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> TracingData: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class TracingDataHeader(google___protobuf___message___Message):
    routing_key = ... # type: bytes

    def __init__(self,
        routing_key : typing___Optional[bytes] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> TracingDataHeader: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class RoutedData(google___protobuf___message___Message):

    @property
    def trace_fragments(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[TraceFragment]: ...

    @property
    def execution_units(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[ExecutionUnit]: ...

    def __init__(self,
        trace_fragments : typing___Optional[typing___Iterable[TraceFragment]] = None,
        execution_units : typing___Optional[typing___Iterable[ExecutionUnit]] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> RoutedData: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class BroadcastData(google___protobuf___message___Message):

    @property
    def strings(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[StringTableEntry]: ...

    @property
    def execution_units(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[ExecutionUnit]: ...

    def __init__(self,
        strings : typing___Optional[typing___Iterable[StringTableEntry]] = None,
        execution_units : typing___Optional[typing___Iterable[ExecutionUnit]] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> BroadcastData: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class StringTableEntry(google___protobuf___message___Message):
    alias = ... # type: int
    value = ... # type: typing___Text

    def __init__(self,
        alias : typing___Optional[int] = None,
        value : typing___Optional[typing___Text] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> StringTableEntry: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class TraceFragment(google___protobuf___message___Message):
    trace_id = ... # type: bytes
    execution_unit_id = ... # type: bytes

    @property
    def time_reference(self) -> google___protobuf___timestamp_pb2___Timestamp: ...

    @property
    def events(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[Event]: ...

    def __init__(self,
        trace_id : typing___Optional[bytes] = None,
        execution_unit_id : typing___Optional[bytes] = None,
        time_reference : typing___Optional[google___protobuf___timestamp_pb2___Timestamp] = None,
        events : typing___Optional[typing___Iterable[Event]] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> TraceFragment: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class ExecutionUnit(google___protobuf___message___Message):
    class Type(int):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        @classmethod
        def Name(cls, number: int) -> str: ...
        @classmethod
        def Value(cls, name: str) -> ExecutionUnit.Type: ...
        @classmethod
        def keys(cls) -> typing___List[str]: ...
        @classmethod
        def values(cls) -> typing___List[ExecutionUnit.Type]: ...
        @classmethod
        def items(cls) -> typing___List[typing___Tuple[str, ExecutionUnit.Type]]: ...
    UNKNOWN = typing___cast(Type, 0)
    PROCESS = typing___cast(Type, 1)
    THREAD = typing___cast(Type, 2)
    COROUTINE = typing___cast(Type, 3)

    id = ... # type: bytes
    type = ... # type: ExecutionUnit.Type

    @property
    def tags(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[Tag]: ...

    def __init__(self,
        id : typing___Optional[bytes] = None,
        type : typing___Optional[ExecutionUnit.Type] = None,
        tags : typing___Optional[typing___Iterable[Tag]] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> ExecutionUnit: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class Event(google___protobuf___message___Message):
    class Type(int):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        @classmethod
        def Name(cls, number: int) -> str: ...
        @classmethod
        def Value(cls, name: str) -> Event.Type: ...
        @classmethod
        def keys(cls) -> typing___List[str]: ...
        @classmethod
        def values(cls) -> typing___List[Event.Type]: ...
        @classmethod
        def items(cls) -> typing___List[typing___Tuple[str, Event.Type]]: ...
    CREATE_EU = typing___cast(Type, 0)
    FINISH_EU = typing___cast(Type, 1)
    OT_START_SPAN = typing___cast(Type, 10)
    OT_LOG = typing___cast(Type, 11)
    OT_GET_CONTEXT = typing___cast(Type, 12)
    OT_FINISH_SPAN = typing___cast(Type, 13)

    class Status(int):
        DESCRIPTOR: google___protobuf___descriptor___EnumDescriptor = ...
        @classmethod
        def Name(cls, number: int) -> str: ...
        @classmethod
        def Value(cls, name: str) -> Event.Status: ...
        @classmethod
        def keys(cls) -> typing___List[str]: ...
        @classmethod
        def values(cls) -> typing___List[Event.Status]: ...
        @classmethod
        def items(cls) -> typing___List[typing___Tuple[str, Event.Status]]: ...
    UNKNOWN = typing___cast(Status, 0)
    BUSY = typing___cast(Status, 1)
    IDLE = typing___cast(Status, 2)

    sequence_number = ... # type: int
    event_type = ... # type: Event.Type
    status = ... # type: Event.Status

    @property
    def timestamp(self) -> google___protobuf___duration_pb2___Duration: ...

    @property
    def causing_events(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[EventReference]: ...

    @property
    def tags(self) -> google___protobuf___internal___containers___RepeatedCompositeFieldContainer[Tag]: ...

    def __init__(self,
        sequence_number : typing___Optional[int] = None,
        timestamp : typing___Optional[google___protobuf___duration_pb2___Duration] = None,
        event_type : typing___Optional[Event.Type] = None,
        status : typing___Optional[Event.Status] = None,
        causing_events : typing___Optional[typing___Iterable[EventReference]] = None,
        tags : typing___Optional[typing___Iterable[Tag]] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> Event: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class EventReference(google___protobuf___message___Message):
    trace_id = ... # type: bytes
    event_id = ... # type: bytes

    def __init__(self,
        trace_id : typing___Optional[bytes] = None,
        event_id : typing___Optional[bytes] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> EventReference: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...

class Tag(google___protobuf___message___Message):
    string_key = ... # type: typing___Text
    alias_key = ... # type: int
    float_value = ... # type: float
    int_value = ... # type: int
    boolean_value = ... # type: bool
    string_value = ... # type: typing___Text
    alias_value = ... # type: int
    bytes_value = ... # type: bytes

    def __init__(self,
        string_key : typing___Optional[typing___Text] = None,
        alias_key : typing___Optional[int] = None,
        float_value : typing___Optional[float] = None,
        int_value : typing___Optional[int] = None,
        boolean_value : typing___Optional[bool] = None,
        string_value : typing___Optional[typing___Text] = None,
        alias_value : typing___Optional[int] = None,
        bytes_value : typing___Optional[bytes] = None,
        ) -> None: ...
    @classmethod
    def FromString(cls, s: bytes) -> Tag: ...
    def MergeFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
    def CopyFrom(self, other_msg: google___protobuf___message___Message) -> None: ...
