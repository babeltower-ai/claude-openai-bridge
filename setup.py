from setuptools import setup, find_packages

setup(
    name="claude2openai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "aiohttp_socks",
        "pydantic",
    ],
    entry_points={
        "console_scripts": [
            "claude2openai=claude2openai.main:main",
        ],
    },
    python_requires=">=3.9",
    description="Claude API to OpenAI API adapter",
    author="Claude2OpenAI",
    author_email="bo@babeltower.cn",
    url="https://github.com/babeltower-ai/claude2openai",
)
