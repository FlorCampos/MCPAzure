# server.py
import os

from pydantic import AnyHttpUrl

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings


class StaticTokenVerifier(TokenVerifier):
    """Verifica tokens bearer contra un valor fijo leído de API_KEY.

    Implementación mínima del protocolo TokenVerifier del SDK, pensada
    para desarrollo y demostración. Un despliegue real debería validar
    la firma de un JWT o consultar el endpoint de introspección del
    authorization server.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        expected = os.environ.get("API_KEY")
        if not expected or token != expected:
            return None
        return AccessToken(token=token, client_id="flor-client", scopes=["user"])


resource_url = os.environ.get("RESOURCE_URL", "http://127.0.0.1:8000/mcp")

mcp = MCPServer(
    "MCP Server - Flor Campos Flores :)",
    token_verifier=StaticTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl("https://auth.example.com"),
        resource_server_url=AnyHttpUrl(resource_url),
        required_scopes=["user"],
    ),
)


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract two numbers"""
    return a - b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide two numbers. Show error if the divisor is zero"""
    if b == 0:
        raise ToolError("Divisor cannot be zero")
    return a / b


@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)