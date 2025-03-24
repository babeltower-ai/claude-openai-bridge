# Claude-OpenAI-Bridge

Claude-OpenAI-Bridge 是一个Python实现的高效适配器，允许您使用 OpenAI API 客户端与 Anthropic 的 Claude API 进行交互。它提供了一个代理服务器，将 OpenAI API 请求转换为 Claude API 请求，并将 Claude 的响应转换回 OpenAI 格式。

## 功能特点

- 支持 OpenAI 聊天完成 API 格式
- 支持流式响应
- 支持文本和图像输入
- 自动转换 Claude 和 OpenAI 的消息格式
- 使用asyncio和懒修改技术实现高效的请求转发
- 实现极简，易于扩展和定制

## 安装

### 使用 uvx 一键执行

[uvx](https://github.com/astral-sh/uv) 是一个快速的 Python 包管理器和安装工具。您可以使用 uvx 一键执行 Claude-OpenAI-Bridge，无需预先安装：

```bash
uvx run claude-openai-bridge
```

或者指定host和port：

```bash
HOST=0.0.0.0 PORT=8080 uvx run claude-openai-bridge
```

### 使用 pip 安装

```bash
pip install claude-openai-bridge
```

## 使用方法

### 设置环境变量

在运行之前，您需要设置以下环境变量：

```bash
# 可选：设置监听地址（默认为 0.0.0.0）
export HOST=127.0.0.1

# 可选：设置监听端口（默认为 8080）
export PORT=8080

# 可选：设置 Anthropic API 端点（默认为 https://api.anthropic.com/v1/messages）
export ANTHROPIC_ENDPOINT=https://api.anthropic.com/v1/messages
```

### 启动服务器

```bash
# 如果已安装
claude-openai-bridge

# 或使用 uvx 一键执行
uvx run claude-openai-bridge
```

### 使用 OpenAI 客户端

一旦服务器运行，您可以使用任何 OpenAI 客户端连接到它，只需将基础 URL 设置为您的服务器地址，并将 API 密钥设置为您的 Anthropic API 密钥。

Python 示例：

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-anthropic-api-key",  # 使用您的 Anthropic API 密钥
    base_url="http://localhost:8080/v1"  # 指向您的 Claude2OpenAI 服务器
)

response = client.chat.completions.create(
    model="claude-3-opus-20240229",  # 使用 Claude 模型名称
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

## 支持的模型

您可以使用任何 Claude 模型，只需在请求中指定相应的模型名称：

- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307
- ...

## 注意事项

- 您需要有一个有效的 Anthropic API 密钥
- 某些 OpenAI 特定的功能可能不可用或行为不同
- 图像输入支持 base64 编码和 URL 格式

## 许可证

[MIT License](LICENSE)
