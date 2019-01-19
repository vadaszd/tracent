# Copyright The OpenTracing Authors
# Copyright Uber Technologies, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Optional, Dict, Type
from types import TracebackType

from .tracer import Tracer
from . import TagType


class SpanContext(object):

    EMPTY_BAGGAGE: Dict[str, str]

    @property
    def baggage(self) -> Dict[str, str]: ...


class Span(object):

    def __init__(self, tracer: Tracer, context: SpanContext) -> None: ...

    @property
    def context(self) -> SpanContext: ...

    @property
    def tracer(self) -> Tracer: ...

    def set_operation_name(self, operation_name: str) -> 'Span': ...

    def finish(self, finish_time: Optional[float]) -> None: ...

    def set_tag(self, key: str, value: TagType) -> 'Span': ...

    def log_kv(self,
               key_values: Dict[str, TagType],
               timestamp: Optional[float]) -> 'Span': ...

    def set_baggage_item(self, key: str, value: str) -> 'Span': ...

    def get_baggage_item(self, key: str) -> str: ...

    def __enter__(self) -> 'Span': ...

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]
                 ) -> Optional[bool]: ...

    def log_event(self,
                  event: TagType,
                  payload: Optional[TagType]
                  ) -> 'Span': ...

    def log(self, **kwargs: TagType) -> 'Span': ...
