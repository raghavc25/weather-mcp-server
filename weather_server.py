import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather", host="0.0.0.0", port=8001)


async def geocode(city: str) -> tuple[float, float, str]:
    """Turn a city name into lat/lon + resolved display name."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params={"name": city, "count": 1})
        resp.raise_for_status()
        data = resp.json()
        if not data.get("results"):
            raise ValueError(f"Could not find location: {city}")
        r = data["results"][0]
        return r["latitude"], r["longitude"], r.get("name", city)


@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get the weather forecast for a city.

    Args:
        city: Name of the city, e.g. "Hyderabad"
        days: Number of days to forecast (1-7)
    """
    days = max(1, min(days, 7))
    lat, lon, resolved_name = await geocode(city)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "forecast_days": days,
        "timezone": "auto",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    daily = data["daily"]
    lines = [f"Forecast for {resolved_name}:"]
    for i, date in enumerate(daily["time"]):
        hi = daily["temperature_2m_max"][i]
        lo = daily["temperature_2m_min"][i]
        rain = daily["precipitation_sum"][i]
        lines.append(f"  {date}: {lo}°C to {hi}°C, {rain}mm precipitation")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
