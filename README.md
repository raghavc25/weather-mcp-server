# weather-mcp-server

An MCP (Model Context Protocol) server that gives an LLM client weather
forecast lookups for any city. Built with [FastMCP](https://github.com/jlowin/fastmcp)
and [Open-Meteo](https://open-meteo.com/) for geocoding and forecasts — no
API key required.

## How it works

1. **Geocode** — the city name is resolved to latitude/longitude via
   Open-Meteo's geocoding API (first match is used).
2. **Forecast** — a daily forecast (min/max temperature, precipitation) is
   fetched for the requested number of days.

## Tools exposed

| Tool | Description | Args |
|---|---|---|
| `get_forecast` | Weather forecast for a city | `city: str`, `days: int = 3` |

`days` is clamped to the range 1–7. `city` is a free-text city name, e.g.
`"Hyderabad"`.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`:
  - `mcp[cli]`
  - `httpx`

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

The server runs over the `streamable-http` transport, bound to `0.0.0.0:8001`:

```bash
python weather_server.py
```

### Connecting an MCP client

```json
{
  "mcpServers": {
    "weather": {
      "url": "http://<host>:8001/mcp"
    }
  }
}
```

## Notes

- Open-Meteo requires no API key and has generous free-tier rate limits,
  suitable for personal/demo use.
- This is a demo/personal project, not hardened for production traffic
  (no auth, no rate limiting, no input sanitization beyond clamping `days`).
