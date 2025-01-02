#!/usr/bin/env python3
import asyncio
import argparse
from anthropic import Anthropic
from .tools import ToolCollection, ComputerTool, BashTool, EditTool
from .loop import sampling_loop

async def main(prompt: str, api_key: str, port: int = 8002):
    responses = []  # Create a list to store responses
    
    def output_callback(content):
        if content["type"] == "text":
            responses.append(("text", content['text']))
            print(f"Assistant: {content['text']}")
        elif content["type"] == "tool_use":
            responses.append(("tool_use", content['name'], content['input']))
            print(f"Tool use: {content['name']} with input {content['input']}")

    def tool_output_callback(result, tool_id):
        if result.output:
            responses.append(("tool_output", result.output))
            print(f"Tool output: {result.output}")
        if result.error:
            responses.append(("tool_error", result.error))
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
        tools=tools,
        max_iterations=20
    )
    
    return responses  # Return the collected responses

if __name__ == "__main__":
    asyncio.run(main())