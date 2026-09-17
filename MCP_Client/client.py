# Allows communication with the server using stdio
from mcp.client.streamable_http import streamable_http_client
import anthropic
import os
import json
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import httpx2

load_dotenv()

class SpyWrite:
    """Envuelve el canal de escritura para ver cada mensaje que sale."""

    def __init__(self, inner):
        self._inner = inner

    async def send(self, message):
        print(f"\n→ ENVIANDO: {message}\n")
        await self._inner.send(message)

    async def aclose(self):
        await self._inner.aclose()

    async def __aenter__(self):
        await self._inner.__aenter__()
        return self

    async def __aexit__(self, *args):
        return await self._inner.__aexit__(*args)


class SpyRead:
    """Envuelve el canal de lectura para ver cada mensaje que entra."""

    def __init__(self, inner):
        self._inner = inner

    async def receive(self):
        message = await self._inner.receive()
        print(f"\n← RECIBIENDO: {message}\n")
        return message

    async def aclose(self):
        await self._inner.aclose()

    async def __aenter__(self):
        await self._inner.__aenter__()
        return self

    async def __aexit__(self, *args):
        return await self._inner.__aexit__(*args)

    def __aiter__(self):
        return self

    async def __anext__(self):
        message = await self._inner.__anext__()
        print(f"\n← RECIBIENDO: {message}\n")
        return message


def call_llm(prompt, functions, system=None):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("CALLING LLM")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        system=system or "You are a helpful assistant.",
        tools=functions,
        messages=[{"role": "user", "content": prompt}],
    )

    functions_to_call = []

    for block in response.content:
        if block.type == "tool_use":
            print("TOOL: ", block)
            functions_to_call.append({"name": block.name, "args": block.input})

    return functions_to_call


def convert_to_llm_tool(tool):
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }


async def run():
    http_client = httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {os.environ['API_KEY']}"}
    )
    async with streamable_http_client(
        "https://mcp-flor-804516708784.us-central1.run.app/mcp",
        http_client=http_client,) as (read, write):
        async with ClientSession(SpyRead(read), SpyWrite(write)) as session:
            await session.initialize()

            resources = await session.list_resources()
            print("LISTING RESOURCES")
            for resource in resources.resources:
                print("Resource: ", resource.uri)

            templates = await session.list_resource_templates()
            print("LISTING TEMPLATES")
            for template in templates.resource_templates:
                print("Template: ", template.uri_template)

            tools = await session.list_tools()
            print("LISTING TOOLS")
            for tool in tools.tools:
                print("Tool: ", tool.name)

            print("READING RESOURCE")
            result = await session.read_resource("greeting://hello")
            for content in result.contents:
                print(content.text, content.mime_type)

            print("CALL TOOL")
            result = await session.call_tool("add", arguments={"a": 1, "b": 7})
            print(result.content)

            print("CALL TOOL CON ERROR")
            result = await session.call_tool("divide", arguments={"a": 10, "b": 0})
            print("is_error:", result.is_error)
            print(result.content)

            functions = []

            for tool in tools.tools:
                print("Tool: ", tool.name)
                print("Tool", tool.input_schema["properties"])
                functions.append(convert_to_llm_tool(tool))

            system = "Eres un profesor de matemáticas. Usa las herramientas disponibles para calcular, nunca calcules mentalmente."
            prompt = "What's 6 times 7?"

            functions_to_call = call_llm(prompt, functions, system=system)

            for f in functions_to_call:
                result = await session.call_tool(f["name"], arguments=f["args"])
                print("TOOLS result: ", result.content)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())