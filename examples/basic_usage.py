"""
Basic usage example for Claude2OpenAI adapter.
"""

import os
import sys
from openai import OpenAI

# 确保 Claude2OpenAI 服务器正在运行
# 可以使用 `claude2openai` 或 `uvx run claude2openai` 启动

# 设置 OpenAI 客户端
client = OpenAI(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),  # 使用您的 Anthropic API 密钥
    base_url="http://localhost:8080/v1",  # 指向您的 Claude2OpenAI 服务器
)

# 发送请求
try:
    response = client.chat.completions.create(
        model="claude-3-opus-20240229",  # 使用 Claude 模型名称
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, what can you tell me about Python?"},
        ],
    )

    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    print(
        "Make sure the Claude2OpenAI server is running and your API key is set correctly.",
        file=sys.stderr,
    )
