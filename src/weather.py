"""Direct API clients, offline parsers and weather display."""

import json, time, math
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from typing import Callable, Any
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
MET = "https://api.met.no/weatherapi/locationforecast/2.0/compact"


class WeatherError(Exception):
    """Actionable request, input or payload error."""


CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def user_agent(email: str) -> str:
    """Require real user contact; no invented fallback."""
    if (
        "@" not in email
        or "." not in email.split("@")[-1]
        or any(s in email.lower() for s in ("example.", "your_", "placeholder"))
    ):
        raise WeatherError("Set your actual university email in configuration.")
    return f"UniversityWeatherAssignment/1.0 ({email})"


def request_json(
    url: str,
    params: dict[str, Any],
    email: str,
    timeout: float = 10,
    retries: int = 2,
    get: Callable = requests.get,
    sleep: Callable = time.sleep,
) -> tuple[dict, dict]:
    """Timeout/status validation and capped exponential retry for connection/5xx."""
    if timeout <= 0 or retries < 0:
        raise WeatherError("Invalid request settings.")
    headers = {"User-Agent": user_agent(email)}
    for attempt in range(retries + 1):
        started = time.perf_counter()
        try:
            r = get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            payload = r.json()
            if not isinstance(payload, dict):
                raise WeatherError("Expected JSON object.")
            return payload, {
                "status": r.status_code,
                "content_type": r.headers.get("Content-Type"),
                "seconds": time.perf_counter() - started,
                "attempts": attempt + 1,
            }
        except (requests.RequestException, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            retryable = isinstance(
                exc, (requests.ConnectionError, requests.Timeout)
            ) or (status is not None and 500 <= status <= 599)
            if not retryable or attempt == retries:
                raise WeatherError(
                    f"Failed after {attempt+1} attempt(s): {type(exc).__name__}; status={status}"
                ) from exc
            sleep(0.5 * 2**attempt)
    raise WeatherError("Unreachable request state.")


def urllib_geocode(
    name: str, email: str, timeout: float = 10, retries: int = 2
) -> tuple[dict, dict]:
    """Part A: urllib-only HTTP, urlencode and json response decoding."""
    url = (
        GEOCODING
        + "?"
        + urlencode({"name": name, "count": 10, "language": "en", "format": "json"})
    )
    for attempt in range(retries + 1):
        started = time.perf_counter()
        try:
            with urlopen(
                Request(url, headers={"User-Agent": user_agent(email)}), timeout=timeout
            ) as r:
                return json.loads(r.read().decode("utf-8")), {
                    "status": r.status,
                    "content_type": r.headers.get("Content-Type"),
                    "seconds": time.perf_counter() - started,
                    "attempts": attempt + 1,
                }
        except (URLError, TimeoutError, ValueError) as exc:
            if attempt == retries or (
                isinstance(exc, HTTPError) and not 500 <= exc.code <= 599
            ):
                raise WeatherError("urllib HTTP failed.") from exc
            time.sleep(0.5 * 2**attempt)
    raise WeatherError("Unreachable request state.")


def validate_coordinates(lat: float, lon: float) -> None:
    """Validate finite latitude/longitude before HTTP."""
    try:
        valid = (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        )
    except TypeError:
        valid = False
    if not valid:
        raise WeatherError("Latitude must be [-90,90]; longitude [-180,180].")


def parse_candidates(payload: dict) -> list[dict]:
    """Absent results means empty; malformed candidate records raise clearly."""
    rows = payload.get("results", [])
    if not isinstance(rows, list):
        raise WeatherError("Results must be a list.")
    for row in rows:
        if not isinstance(row, dict) or not all(
            k in row for k in ("name", "latitude", "longitude")
        ):
            raise WeatherError("Incomplete candidate.")
        validate_coordinates(row["latitude"], row["longitude"])
    return rows


def geocode(name: str, email: str) -> list[dict]:
    """Return candidates without silently resolving ambiguity."""
    if not name.strip():
        raise WeatherError("Enter a city name.")
    return parse_candidates(
        request_json(
            GEOCODING,
            {"name": name, "count": 10, "language": "en", "format": "json"},
            email,
        )[0]
    )


def choose_candidate(rows: list[dict], index: int) -> dict:
    """Configured zero-based choice avoids blocking notebook execution."""
    if not rows:
        raise WeatherError("No matching city; change configuration.")
    if type(index) is not int or not 0 <= index < len(rows):
        raise WeatherError("Invalid candidate index.")
    return rows[index]


def get_forecast(lat: float, lon: float, days: int, email: str) -> dict:
    """Get daily weather, explicit units and local-date timezone."""
    validate_coordinates(lat, lon)
    if type(days) is not int or not 1 <= days <= 16:
        raise WeatherError("days must be 1–16.")
    return request_json(
        FORECAST,
        {
            "latitude": lat,
            "longitude": lon,
            "forecast_days": days,
            "timezone": "auto",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code",
        },
        email,
    )[0]


def parse_forecast(payload: dict) -> pd.DataFrame:
    """Validate daily arrays and return unit-labelled columns."""
    mapping = {
        "time": "Date",
        "temperature_2m_max": "Maximum temperature (°C)",
        "temperature_2m_min": "Minimum temperature (°C)",
        "precipitation_sum": "Precipitation (mm)",
        "wind_speed_10m_max": "Maximum wind (km/h)",
        "weather_code": "Weather code",
    }
    d = payload.get("daily", {})
    if not isinstance(d, dict) or not all(k in d for k in mapping):
        raise WeatherError("Missing daily fields.")
    arrays = [d[k] for k in mapping]
    if (
        not all(isinstance(a, list) for a in arrays)
        or len({len(a) for a in arrays}) != 1
        or not arrays[0]
    ):
        raise WeatherError("Daily arrays must be nonempty and aligned.")
    expected = {
        "temperature_2m_max": "°C",
        "temperature_2m_min": "°C",
        "precipitation_sum": "mm",
        "wind_speed_10m_max": "km/h",
    }
    if any(payload.get("daily_units", {}).get(k) != v for k, v in expected.items()):
        raise WeatherError("Invalid units.")
    try:
        f = pd.DataFrame({v: d[k] for k, v in mapping.items()})
        f["Date"] = pd.to_datetime(f["Date"], errors="raise")
        for c in list(mapping.values())[1:]:
            f[c] = pd.to_numeric(f[c], errors="raise")
            if f[c].isna().any() or not f[c].map(math.isfinite).all():
                raise ValueError("Nonfinite value.")
        if (f["Minimum temperature (°C)"] > f["Maximum temperature (°C)"]).any():
            raise ValueError("Inverted range.")
        if (f[["Precipitation (mm)", "Maximum wind (km/h)"]] < 0).any().any():
            raise ValueError("Negative rain/wind.")
        if f["Date"].duplicated().any() or not f["Date"].is_monotonic_increasing:
            raise ValueError("Invalid dates.")
        f["Description"] = f["Weather code"].map(
            lambda c: CODES.get(c, f"Unknown WMO code {c}")
        )
        return f
    except (ValueError, TypeError) as exc:
        raise WeatherError(f"Invalid forecast: {exc}") from exc


def get_met_forecast(lat: float, lon: float, email: str) -> dict:
    """Single compact MET request; truncate coordinates to four decimals."""
    validate_coordinates(lat, lon)
    return request_json(
        MET,
        {
            "lat": f"{math.trunc(lat*10000)/10000:.4f}",
            "lon": f"{math.trunc(lon*10000)/10000:.4f}",
        },
        email,
    )[0]


def parse_met(payload: dict) -> pd.DataFrame:
    """Read instantaneous UTC temperatures, not daily extrema."""
    try:
        p = payload["properties"]
        rows = p["timeseries"]
        if not rows or p["meta"]["units"]["air_temperature"] != "celsius":
            raise ValueError("Invalid MET units/series.")
        f = pd.DataFrame(
            [
                {
                    "Time (UTC)": pd.to_datetime(r["time"], utc=True),
                    "Temperature (°C)": r["data"]["instant"]["details"][
                        "air_temperature"
                    ],
                }
                for r in rows
            ]
        )
        f["Temperature (°C)"] = pd.to_numeric(f["Temperature (°C)"], errors="raise")
        if not f["Temperature (°C)"].map(math.isfinite).all():
            raise ValueError("Invalid temperature.")
        return f
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherError("Malformed MET response.") from exc


def plot_forecast(f: pd.DataFrame) -> Figure:
    """Temperature range and precipitation on separate labelled axes."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(
        f["Date"], f["Maximum temperature (°C)"], label="Maximum", color="firebrick"
    )
    ax.plot(
        f["Date"], f["Minimum temperature (°C)"], label="Minimum", color="royalblue"
    )
    ax.fill_between(
        f["Date"],
        f["Minimum temperature (°C)"].to_numpy(dtype=float),
        f["Maximum temperature (°C)"].to_numpy(dtype=float),
        alpha=0.15,
    )
    rain = ax.twinx()
    rain.bar(
        f["Date"],
        f["Precipitation (mm)"],
        alpha=0.25,
        color="teal",
        label="Precipitation",
    )
    ax.set(
        xlabel="Local date",
        ylabel="Temperature (°C)",
        title="Daily temperature range and precipitation",
    )
    rain.set_ylabel("Precipitation (mm)")
    ax.legend(loc="upper left")
    rain.legend(loc="upper right")
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def forecast_summary(f: pd.DataFrame) -> str:
    """Describe this response window only."""
    return f"{len(f)} days; minimum {f['Minimum temperature (°C)'].min():.1f} °C; maximum {f['Maximum temperature (°C)'].max():.1f} °C; precipitation {f['Precipitation (mm)'].sum():.1f} mm."
