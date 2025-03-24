# Claude2OpenAI

[中文版本](README_zh.md)

Claude2OpenAI is an efficient Python adapter that allows you to interact with Anthropic's Claude API using OpenAI API clients. It provides a proxy server that converts OpenAI API requests to Claude API requests and transforms Claude's responses back to OpenAI format.

## Features

- Support for OpenAI chat completion API format
- Streaming response support
- Text and image input support
- Automatic conversion between Claude and OpenAI message formats
- Efficient request forwarding using asyncio and lazy modification techniques
- Minimalist implementation, easy to extend and customize

## Installation

### One-click execution with uvx

[uvx](https://github.com/astral-sh/uv) is a fast Python package manager and installer. You can use uvx to run Claude2OpenAI with a single command, without prior installation:

```bash
uvx run claude2openai
```

Or specify host and port:

```bash
HOST=0.0.0.0 PORT=8080 uvx run claude2openai
```

### Installation with pip

```bash
pip install claude2openai
```

## Usage

### Setting Environment Variables

Before running, you need to set the following environment variables:

```bash
# Optional: Set the listening address (default is 0.0.0.0)
export HOST=127.0.0.1

# Optional: Set the listening port (default is 8080)
export PORT=8080

# Optional: Set the Anthropic API endpoint (default is https://api.anthropic.com/v1/messages)
export ANTHROPIC_ENDPOINT=https://api.anthropic.com/v1/messages
```

### Starting the Server

```bash
# If installed
claude2openai

# Or use uvx for one-click execution
uvx run github.com/yourusername/claude2openai
```

### Using OpenAI Client

Once the server is running, you can connect to it using any OpenAI client by setting the base URL to your server address and the API key to your Anthropic API key.

Python example:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-anthropic-api-key",  # Use your Anthropic API key
    base_url="http://localhost:8080/v1"  # Point to your Claude2OpenAI server
)

response = client.chat.completions.create(
    model="claude-3-opus-20240229",  # Use Claude model name
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

## Supported Models

You can use any Claude model by specifying the corresponding model name in your request:

- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307
- ...

## Notes

- You need a valid Anthropic API key
- Some OpenAI-specific features may not be available or behave differently
- Image input supports both base64 encoding and URL formats

## License

[MIT License](LICENSE)
