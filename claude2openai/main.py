import os
import os.path
import time
import json
import uuid
import logging
from typing import List, Dict, Any, Optional, Union

import aiohttp
from aiohttp import web
from pydantic import BaseModel
from claude2openai.sse import (
    Event,
    EventStreamModifier,
    apply_event_stream_modifiers,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class OpenAIMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]


class OpenAIRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class ClaudeSource(BaseModel):
    type: str
    media_type: str
    data: str


class ClaudeContent(BaseModel):
    type: str
    text: Optional[str] = None
    source: Optional[ClaudeSource] = None


class ClaudeMessage(BaseModel):
    role: str
    content: List[ClaudeContent]


class ClaudeAPIRequest(BaseModel):
    model: str
    messages: List[ClaudeMessage]
    system: Optional[str] = None
    max_tokens: int = 4096
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class OpenAIModel(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "user"


class OpenAIModelsResponse(BaseModel):
    object: str = "list"
    data: List[OpenAIModel] = []


def process_messages(openai_req: dict) -> tuple:
    """Convert OpenAI messages to Claude format"""
    new_messages = []
    system_prompt = None

    for message in openai_req.get("messages", []):
        if message.get("role") == "system":
            # Extract system message
            content = message.get("content", "")
            if isinstance(content, str):
                system_prompt = content
            elif isinstance(content, list):
                # For array content, concatenate all text parts
                system_content = ""
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        system_content += part.get("text", "")
                system_prompt = system_content
        else:
            # Process regular messages
            claude_message = {"role": message.get("role"), "content": []}
            content = message.get("content", "")

            if isinstance(content, str):
                # Simple string content
                claude_message["content"].append({"type": "text", "text": content})
            elif isinstance(content, list):
                # Process array of content blocks
                for part in content:
                    if isinstance(part, dict):
                        content_type = part.get("type")

                        if content_type == "text":
                            claude_message["content"].append(
                                {"type": "text", "text": part.get("text", "")}
                            )
                        elif content_type == "image_url":
                            # Handle image URLs
                            image_url = part.get("image_url", {})
                            url = image_url.get("url", "")

                            # For base64 images
                            if url.startswith("data:image/"):
                                parts = url.split(",", 1)
                                if len(parts) >= 2:
                                    media_type = (
                                        parts[0]
                                        .replace("data:", "")
                                        .replace(";base64", "")
                                    )
                                    source = {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": parts[1],
                                    }
                                    claude_message["content"].append(
                                        {"type": "image", "source": source}
                                    )
                            else:
                                # For HTTP URLs
                                source = {
                                    "type": "url",
                                    "url": url,
                                }
                                claude_message["content"].append(
                                    {"type": "image", "source": source}
                                )

            # Only add message if it has content
            if claude_message["content"]:
                new_messages.append(claude_message)

    return new_messages, system_prompt


def create_claude_request(openai_req: dict, stream: bool) -> dict:
    """Create a Claude API request from an OpenAI request"""
    messages, system = process_messages(openai_req)

    claude_req = {
        "model": openai_req.get("model"),
        "messages": messages,
        "max_tokens": 4096,
        "stream": stream,
    }

    # Add optional parameters if present
    if system:
        claude_req["system"] = system
    if "temperature" in openai_req and openai_req.get("temperature") is not None:
        claude_req["temperature"] = openai_req.get("temperature")
    if "top_p" in openai_req and openai_req.get("top_p") is not None:
        claude_req["top_p"] = openai_req.get("top_p")

    return claude_req


class ClaudeToOpenAIModifier(EventStreamModifier):
    def __init__(self, openai_req: dict):
        self.openai_req = openai_req
        self.chat_id = f"chatcmpl-{str(uuid.uuid4())}"
        self.timestamp = int(time.time())
        self.content_buffer = ""
        self.input_tokens = 0
        self.output_tokens = 0

    def should_modify(self, data: bytes) -> bool:
        """Check if the event should be modified"""
        return True

    def modify(self, event: Event) -> Optional[Event]:
        """Modify the event data to convert from Claude to OpenAI format"""
        if not event["data"]:
            return

        event_type = event["event"]

        try:
            json_bytes = event["separator"].join(event["data"])
            data = json.loads(json_bytes)
        except json.JSONDecodeError:
            return event

        if event_type == b"message_start":
            event["event"] = None
            # Convert message_start to OpenAI format
            usage = data.get("message", {}).get("usage", {})
            self.input_tokens += usage.get("input_tokens", 0)
            self.output_tokens += usage.get("output_tokens", 0)
            data = {
                "choices": [
                    {
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                        "index": 0,
                        "logprobs": None,
                    }
                ],
                "created": self.timestamp,
                "id": self.chat_id,
                "model": self.openai_req.get("model"),
                "object": "chat.completion.chunk",
                "system_fingerprint": "fp_f3927aa00d",
            }
            event["data"] = json.dumps(data).encode("utf-8").split(event["separator"])
            return event
        elif event_type == b"content_block_start":
            return
        elif event_type == b"ping":
            return
        elif event_type == b"content_block_delta":
            event["event"] = None
            delta = data.get("delta", {})
            if delta.get("type") == "text_delta":
                text_delta = delta.get("text", "")
                self.content_buffer += text_delta

                # Convert to OpenAI format
                data = {
                    "choices": [
                        {
                            "delta": {"content": text_delta},
                            "finish_reason": None,
                            "index": 0,
                            "logprobs": None,
                        }
                    ],
                    "created": self.timestamp,
                    "id": self.chat_id,
                    "model": self.openai_req.get("model"),
                    "object": "chat.completion.chunk",
                    "system_fingerprint": "fp_f3927aa00d",
                }
                event["data"] = (
                    json.dumps(data).encode("utf-8").split(event["separator"])
                )
                return event
        elif event_type == b"content_block_stop":
            return
        elif event_type == b"message_delta":
            usage = data.pop("usage", {})
            self.input_tokens += usage.get("input_tokens", 0)
            self.output_tokens += usage.get("output_tokens", 0)
            return
        elif event_type == b"message_stop":
            # Convert message_stop to OpenAI format
            event["event"] = None
            data = {
                "choices": [
                    {
                        "delta": {},
                        "finish_reason": "stop",
                        "index": 0,
                        "logprobs": None,
                    }
                ],
                "created": self.timestamp,
                "id": self.chat_id,
                "model": self.openai_req.get("model"),
                "object": "chat.completion.chunk",
                "system_fingerprint": "fp_f3927aa00d",
                "usage": {
                    "prompt_tokens": self.input_tokens,
                    "completion_tokens": self.output_tokens,
                    "total_tokens": self.input_tokens + self.output_tokens,
                },
            }
            event["data"] = json.dumps(data).encode("utf-8").split(event["separator"])
            return event
        else:
            return event


async def handle_chat_completions(request):
    """Handle chat completions endpoint"""
    try:
        # Parse request body
        body_bytes = await request.read()
        body = json.loads(body_bytes)

        # Extract API key from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            return web.json_response(
                {"error": {"message": "Invalid Authorization header format"}},
                status=400,
            )
        api_key = auth_header.replace("Bearer ", "")

        # Create Claude request
        stream = body.get("stream", False)
        claude_req = create_claude_request(body, stream)

        # Get endpoint from environment variable or use default
        endpoint = os.getenv(
            "ANTHROPIC_ENDPOINT", "https://api.anthropic.com/v1/messages"
        )
        if endpoint != "https://api.anthropic.com/v1/messages":
            endpoint = endpoint.rstrip("/")
            if endpoint.endswith("/v1/messages") or endpoint.endswith("/v1"):
                return web.json_response(
                    {
                        "error": {
                            "message": f"Invalid ANTHROPIC_ENDPOINT format: {endpoint}"
                        }
                    },
                    status=400,
                )
            endpoint = f"{endpoint}/v1/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                endpoint, json=claude_req, headers=headers
            ) as response:
                content_type = response.headers.get("content-type", "")

                if stream and "text/event-stream" in content_type:
                    # Handle streaming response
                    resp = web.StreamResponse(
                        status=response.status,
                        headers={
                            "Content-Type": "text/event-stream",
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                        },
                    )

                    await resp.prepare(request)

                    # Create modifier for Claude to OpenAI conversion
                    modifier = ClaudeToOpenAIModifier(body)

                    async for chunk in apply_event_stream_modifiers(
                        response.content.iter_any,  # type: ignore
                        [modifier],
                    ):
                        await resp.write(chunk)

                    # Send [DONE] at the end
                    await resp.write(b"data: [DONE]\n\n")

                    return resp
                else:
                    # Handle non-streaming response
                    if response.status != 200:
                        error_data = await response.json()
                        return web.json_response(
                            {
                                "error": {
                                    "type": error_data.get("error", {}).get(
                                        "type", "unknown"
                                    ),
                                    "message": error_data.get("error", {}).get(
                                        "message", "Unknown error"
                                    ),
                                }
                            },
                            status=response.status,
                        )

                    claude_data = await response.json()

                    # Extract text content from Claude response
                    response_text = ""

                    for content in claude_data.get("content", []):
                        if content.get("type") == "text":
                            response_text += content.get("text", "")
                        elif content.get("type") == "" and content.get("text"):
                            response_text += content.get("text", "")

                    # If responseText is still empty, try different approach
                    if not response_text and claude_data.get("content"):
                        # Try to extract text regardless of content type
                        for content in claude_data.get("content", []):
                            if content.get("text"):
                                response_text += content.get("text", "")

                        # Last resort: use the first block's text field no matter what
                        if not response_text and claude_data.get("content"):
                            response_text = claude_data.get("content", [{}])[0].get(
                                "text", ""
                            )

                    openai_resp = {
                        "id": claude_data.get("id"),
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": claude_data.get("model"),
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": response_text,
                                },
                                "logprobs": None,
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": claude_data.get("usage", {}).get(
                                "input_tokens", 0
                            ),
                            "completion_tokens": claude_data.get("usage", {}).get(
                                "output_tokens", 0
                            ),
                            "total_tokens": claude_data.get("usage", {}).get(
                                "input_tokens", 0
                            )
                            + claude_data.get("usage", {}).get("output_tokens", 0),
                        },
                    }

                    return web.json_response(openai_resp)

    except Exception as e:
        logger.error(f"Error in chat completions: {str(e)}")
        return web.json_response(
            {"error": {"message": f"Internal server error: {str(e)}"}}, status=500
        )


def create_app():
    """Create the web application"""
    app = web.Application()

    app.router.add_post("/v1/chat/completions", handle_chat_completions)
    return app


def main():
    """Main entry point"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    app = create_app()
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    main()
