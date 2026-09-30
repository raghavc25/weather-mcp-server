import unicodedata

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather", host="0.0.0.0", port=8001)

# Popular destinations that are regions rather than towns, so Open-Meteo's
# geocoder (which only knows populated places) can't find them by name, or
# whose plain name resolves to a different place first. Each maps to a
# representative town, written as a "City, State" query.
DESTINATION_ALIASES = {
    "goa": "Panjim, Goa",
    "kerala": "Kochi, Kerala",
    "coorg": "Madikeri, Karnataka",
    "kodagu": "Madikeri, Karnataka",
    "kashmir": "Srinagar, Jammu and Kashmir",
    "manali": "Manali, Himachal Pradesh",
}


def _normalize(text: str) -> str:
    """Case- and accent-insensitive form for comparing place names."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().strip()


def _matches_qualifier(result: dict, qualifier: str) -> bool:
    return qualifier in {
        _normalize(result.get("country", "")),
        _normalize(result.get("country_code", "")),
        _normalize(result.get("admin1", "")),
    }


async def geocode(city: str) -> tuple[float, float, str]:
    """Turn a city name into lat/lon + resolved display name.

    Accepts "City" or "City, Country/State" (e.g. "Goa, Philippines",
    "Manali, Tamil Nadu", "Paris, US"). Exact name matches win over fuzzy
    ones, so "Goa" doesn't become Genoa and "Leh" doesn't become Le Havre.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    label = city.strip()
    query = DESTINATION_ALIASES.get(_normalize(label), label)
    name, _, qualifier = (part.strip() for part in query.partition(","))

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params={"name": name, "count": 10})
        resp.raise_for_status()
        results = resp.json().get("results") or []

    if qualifier:
        # A stated country/state is a hard filter: better "not found" than
        # a same-named place somewhere else.
        results = [r for r in results if _matches_qualifier(r, _normalize(qualifier))]
    if not results:
        raise ValueError(f"Could not find location: {city}")

    exact = [r for r in results if _normalize(r["name"]) == _normalize(name)]
    r = (exact or results)[0]

    display_name = r["name"]
    if query != label and _normalize(r["name"]) != _normalize(label):
        display_name = f"{label.title()} ({r['name']})"  # e.g. "Goa (Panjim)"
    # Include the state/province for disambiguation unless it just repeats the name.
    region = r.get("admin1", "")
    if _normalize(region) in (_normalize(r["name"]), _normalize(label)):
        region = ""
    display_name = ", ".join(p for p in (display_name, region, r.get("country", "")) if p)
    return r["latitude"], r["longitude"], display_name


@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get the weather forecast for a city.

    Args:
        city: Name of the city, optionally with country or state to disambiguate,
              e.g. "Hyderabad", "Goa", "Paris, France" or "Manali, Tamil Nadu"
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
