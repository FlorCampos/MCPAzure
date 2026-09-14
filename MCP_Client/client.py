# Allows communication with the server using stdio
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="mcp",
    args=["run", "server.py"],
    env=None,
)


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
    
async def run():
    async with stdio_client(server_params) as (read, write):
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


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())