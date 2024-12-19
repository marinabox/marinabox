#!/usr/bin/env python3
import asyncio
import argparse
from anthropic import Anthropic
from .tools import ToolCollection, ComputerTool, BashTool, EditTool
from .loop import sampling_loop

async def main(prompt: str, api_key: str, port: int = 8002):
    
    def output_callback(content):
        if content["type"] == "text":
            print(f"Assistant: {content['text']}")
        elif content["type"] == "tool_use":
            print(f"Tool use: {content['name']} with input {content['input']}")

    def tool_output_callback(result, tool_id):
        if result.output:
            print(f"Tool output: {result.output}")
        if result.error:
            print(f"Tool error: {result.error}")

    def api_response_callback(request, response, error):
        if error:
            print(f"API error: {error}")

    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

    computer_tool = ComputerTool(port=port)
    bash_tool = BashTool()
    edit_tool = EditTool()
    
    tools = ToolCollection(computer_tool, bash_tool, edit_tool)

    await sampling_loop(
        model="claude-3-5-sonnet-20241022",
        provider="anthropic",
        system_prompt_suffix="",
        messages=messages,
        output_callback=output_callback,
        tool_output_callback=tool_output_callback,
        api_response_callback=api_response_callback,
        api_key=api_key,
        tools=tools
    )

if __name__ == "__main__":
    asyncio.run(main())