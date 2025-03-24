from typing import AsyncGenerator, Callable, TypedDict, Optional, Iterable
from collections.abc import ByteString

KeywordDetector = Callable[[bytes], bool]
Modifier = Callable[[dict], bool]


class Event(TypedDict):
    raw_bytes: bytearray
    separator: bytes
    event: Optional[bytearray]
    id: Optional[bytearray]
    retry: Optional[bytearray]
    data: Optional[Iterable[ByteString]]


class EventStreamModifier:
    def should_modify(self, data: bytes) -> bool:
        raise NotImplementedError

    def modify(self, event: Event) -> Optional[Event]:
        raise NotImplementedError


async def apply_event_stream_modifiers(
    byte_stream: Callable[[], AsyncGenerator[bytes, None]],
    modifiers: list[EventStreamModifier],
) -> AsyncGenerator[bytes, None]:
    stream = lazy_decode_sse_stream(byte_stream)
    for modifier in modifiers:
        stream = smart_modify_sse_events(stream, modifier)
    async for output in encode_sse_events(stream):
        yield output


async def lazy_decode_sse_stream(content) -> AsyncGenerator[Event, None]:
    buffer = bytearray()
    separator = None
    line_separator = None
    sep_len = 0

    async for chunk in content():
        buffer.extend(chunk)

        while True:
            if separator is None:
                if b"\r\n\r\n" in buffer:
                    separator = b"\r\n\r\n"
                    sep_len = 4
                    line_separator = b"\r\n"
                elif b"\n\n" in buffer:
                    separator = b"\n\n"
                    sep_len = 2
                    line_separator = b"\n"
                else:
                    break

            end_pos = buffer.find(separator)
            if end_pos == -1:
                break

            event_bytes = buffer[:end_pos]
            buffer = buffer[end_pos + sep_len :]

            yield Event(
                raw_bytes=event_bytes,
                separator=line_separator or b"\n",
                event=None,
                id=None,
                retry=None,
                data=None,
            )

    if buffer:
        yield Event(
            raw_bytes=buffer,
            separator=line_separator or b"\n",
            event=None,
            id=None,
            retry=None,
            data=None,
        )


def extract_event(event: Event):
    """从事件字节中提取JSON数据"""

    datas: list[bytearray] = []
    for line in event["raw_bytes"].split(event["separator"]):
        key, value = line.split(b": ", 1)
        # print(key, value)
        if key == b"data":
            datas.append(value)
        elif key == b"event":
            event["event"] = value
        elif key == b"id":
            event["id"] = value
        elif key == b"retry":
            event["retry"] = value
    if datas:
        event["data"] = datas
    else:
        event["data"] = None


def build_event(event: Event):
    """构建事件"""
    lines = []
    if event["event"]:
        lines.append(b"event: " + event["event"])
    if event["id"]:
        lines.append(b"id: " + event["id"])
    if event["retry"]:
        lines.append(b"retry: " + event["retry"])
    if event["data"]:
        lines.extend([b"data: " + line for line in event["data"]])
    return event["separator"].join(lines)


async def smart_modify_sse_events(
    event_generator,
    modifier: EventStreamModifier,
) -> AsyncGenerator[Optional[Event], None]:
    """智能修改SSE事件"""
    async for event in event_generator:
        if modifier.should_modify(event["raw_bytes"]):
            extract_event(event)
            yield modifier.modify(event)
        else:
            yield event


async def encode_sse_events(event_generator) -> AsyncGenerator[bytes, None]:
    """编码SSE事件"""
    async for event in event_generator:
        if event is None:
            continue
        if event["data"]:
            yield build_event(event) + event["separator"] * 2
        else:
            yield event["raw_bytes"] + event["separator"] * 2
