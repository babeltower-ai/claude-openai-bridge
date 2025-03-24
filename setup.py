from setuptools import setup, find_packages

setup(
    name="claude-openai-bridge",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "aiohttp_socks",
        "pydantic",
    ],
    entry_points={
        "console_scripts": [
<<<<<<< HEAD
            "claude2openai=claude2openai.main:main",
=======
            "claude-openai-bridge=claude2openai.main:main",
>>>>>>> new bmDdFBmHb4
        ],
    },
    python_requires=">=3.9",
    description="Claude API to OpenAI API adapter",
    author="babeltower-ai",
    author_email="bo@babeltower.cn",
    url="https://github.com/babeltower-ai/claude-openai-bridge",
)
