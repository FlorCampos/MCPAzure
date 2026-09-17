# MCP Calculator Server
 
A Model Context Protocol server and client built with the official Python SDK v2, including bearer token authentication and protocol-level traffic instrumentation.
 
The server exposes arithmetic tools over MCP. The client connects to it, discovers the available tools, and lets an LLM decide which one to call based on a natural language prompt.
 
## Why this exists
 
Most MCP examples stop at "here's a server, here's a tool." This one adds the parts you need to actually understand and operate the protocol:
 
- **Traffic inspection** — every JSON-RPC message in and out is printed, so the handshake, capability discovery, and tool calls are visible as they happen
- **Bearer authentication** — implements the SDK's `TokenVerifier` protocol, following the OAuth 2.1 resource server model from the MCP authorization spec
- **Two transports** — runs over stdio for local use or Streamable HTTP for remote deployment
- **Error semantics** — demonstrates the difference between transport failures, protocol errors, and tool execution errors
## Architecture
 
```
┌──────────────┐                      ┌──────────────┐
│  Anthropic   │                      │  server.py   │
│  Claude API  │                      │              │
└──────┬───────┘                      │  add()       │
       │ decides which tool           │  subtract()  │
       │                              │  multiply()  │
┌──────▼───────┐    JSON-RPC over     │  divide()    │
│  client.py   │◄────────────────────►│              │
│  (MCP host)  │   Streamable HTTP    │  greeting:// │
└──────────────┘    + Bearer auth     └──────────────┘
```
 
The client acts as an MCP host: it maintains the session with the server, translates MCP tool schemas into the format the model expects, and executes whatever the model decides to call.
 
## Setup
 
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
 
Copy `.env.example` to `.env` and fill in the values:
 
```
ANTHROPIC_API_KEY=sk-ant-...
API_KEY=your-bearer-token
```
 
Generate a token with:
 
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
 
## Running
 
Start the server:
 
```bash
python3 server.py
```
 
In a second terminal, run the client:
 
```bash
python3 client.py
```
 
## What you'll see
 
The client prints every protocol message as it travels:
 
```
→ SENDING: JSONRPCRequest(id=1, method='initialize', ...)
← RECEIVING: JSONRPCResponse(id=1, result={'serverInfo': {'name': 'MCP Calculator'}, ...})
→ SENDING: JSONRPCRequest(id=4, method='tools/list', ...)
← RECEIVING: JSONRPCResponse(id=4, result={'tools': [...]})
```
 
Followed by the model's decision and its execution:
 
```
CALLING LLM
TOOL: ToolUseBlock(name='multiply', input={'a': 6, 'b': 7})
→ SENDING: JSONRPCRequest(id=8, method='tools/call', params={'name': 'multiply', ...})
← RECEIVING: JSONRPCResponse(id=8, result={'content': [{'text': '42.0'}], ...})
```
 
Note that nothing in the code specifies `multiply`, `6`, or `7`. The prompt is `"What's 6 times 7?"` — the model picks the tool from its description and extracts the arguments.
 
## Implementation notes
 
### Tool schemas come from type hints
 
The server never declares a JSON Schema by hand. Type annotations and docstrings generate it:
 
```python
@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide two numbers. Show error if the divisor is zero"""
```
 
becomes
 
```json
{
  "name": "divide",
  "description": "Divide two numbers. Show error if the divisor is zero",
  "inputSchema": {
    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
    "required": ["a", "b"]
  }
}
```
 
The docstring is the only thing the model has to decide whether this tool fits a request. It is part of the contract, not documentation.
 
### Three layers of failure
 
| Layer | Example | Result |
|---|---|---|
| Transport | Invalid bearer token | HTTP 401, session never opens |
| Protocol | Unknown method | JSON-RPC error response |
| Tool execution | Division by zero | `isError: true` with a message the model can read |
 
The third case matters most: a failing tool should not break the conversation. Raising `ToolError` sends the message through to the model; any other exception is masked to avoid leaking internals.
 
### Traffic instrumentation
 
`SpyRead` and `SpyWrite` wrap the transport streams and print each message before passing it along. This is a decorator over the stream interface — the SDK is unaware it exists.
 
```python
async with ClientSession(SpyRead(read), SpyWrite(write)) as session:
```
 
Remove the wrappers and the client behaves identically, just silently.
 
## Switching transports
 
For stdio, where the client launches the server as a subprocess:
 
```python
server_params = StdioServerParameters(command="python", args=["server.py"])
async with stdio_client(server_params) as (read, write):
```
 
For Streamable HTTP, where the server runs independently:
 
```python
async with streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http_client) as (read, write):
```
 
Nothing else in the client changes. JSON-RPC does not know or care how it is transported.
 
## Stack
 
- Python 3.14
- MCP Python SDK v2
- Anthropic API (Claude)
- Streamable HTTP transport with bearer auth
## License
 
MIT