"""Network-free parser and transport tests."""

import json
from pathlib import Path
import pytest
import requests
from src.weather import *

DATA = Path(__file__).resolve().parents[1] / "data" / "samples"


def sample(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_empty():
    assert parse_candidates(sample("geocoding_empty.json")) == []


def test_city():
    assert parse_candidates(sample("geocoding_kampala.json"))[0]["name"] == "Kampala"


def test_ambiguous():
    rows = parse_candidates(sample("geocoding_ambiguous.json"))
    assert len(rows) == 2 and choose_candidate(rows, 1)["admin1"] == "Massachusetts"


@pytest.mark.parametrize("rows,index", [([], 0), ([{}], 2), ([{}], -1)])
def test_selection(rows, index):
    with pytest.raises(WeatherError):
        choose_candidate(rows, index)


def test_forecast():
    f = parse_forecast(sample("forecast_kampala.json"))
    assert (
        len(f) == 7
        and f["Precipitation (mm)"].sum() == 28
        and f["Description"].iloc[3] == "Thunderstorm"
    )


def test_missing():
    p = sample("forecast_kampala.json")
    del p["daily"]["weather_code"]
    with pytest.raises(WeatherError):
        parse_forecast(p)


def test_lengths():
    p = sample("forecast_kampala.json")
    p["daily"]["time"].pop()
    with pytest.raises(WeatherError):
        parse_forecast(p)


@pytest.mark.parametrize(
    "change", ["null", "negative", "inverted", "units", "duplicate"]
)
def test_malformed(change):
    p = sample("forecast_kampala.json")
    if change == "null":
        p["daily"]["temperature_2m_max"][0] = None
    if change == "negative":
        p["daily"]["precipitation_sum"][0] = -1
    if change == "inverted":
        p["daily"]["temperature_2m_min"][0] = 100
    if change == "units":
        p["daily_units"]["precipitation_sum"] = "inch"
    if change == "duplicate":
        p["daily"]["time"][1] = p["daily"]["time"][0]
    with pytest.raises(WeatherError):
        parse_forecast(p)


def test_unknown():
    p = sample("forecast_kampala.json")
    p["daily"]["weather_code"][0] = 999
    assert "Unknown" in parse_forecast(p)["Description"].iloc[0]


def test_met():
    assert len(parse_met(sample("met_kampala.json"))) == 4
    with pytest.raises(WeatherError):
        parse_met({})


@pytest.mark.parametrize("lat,lon", [(91, 0), (0, 181), (float("nan"), 0), ("x", 0)])
def test_coordinates(lat, lon):
    with pytest.raises(WeatherError):
        validate_coordinates(lat, lon)


def test_contact():
    with pytest.raises(WeatherError):
        user_agent("your_email@example.com")


class Response:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self.headers = {"Content-Type": "application/json"}
        self.payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("simulated", response=self)

    def json(self):
        return self.payload


def test_backoff(monkeypatch):
    monkeypatch.setattr("src.weather.user_agent", lambda _: "offline-test")
    responses = iter([Response(500), Response(503), Response(200, {"ok": True})])
    waits = []
    p, m = request_json(
        "mock", {}, "", get=lambda *a, **k: next(responses), sleep=waits.append
    )
    assert p["ok"] and m["attempts"] == 3 and waits == [0.5, 1.0]


def test_400(monkeypatch):
    monkeypatch.setattr("src.weather.user_agent", lambda _: "offline-test")
    calls = []

    def get(*a, **k):
        calls.append(1)
        return Response(400)

    with pytest.raises(WeatherError):
        request_json("mock", {}, "", get=get, sleep=lambda _: None)
    assert len(calls) == 1


@pytest.mark.parametrize("error", [requests.ConnectionError, requests.Timeout])
def test_failures(error, monkeypatch):
    monkeypatch.setattr("src.weather.user_agent", lambda _: "offline-test")
    calls = []

    def get(*a, **k):
        calls.append(k["timeout"])
        raise error("simulated")

    with pytest.raises(WeatherError, match="3 attempt"):
        request_json("mock", {}, "", timeout=0.000001, get=get, sleep=lambda _: None)
    assert calls == [0.000001] * 3


def test_json(monkeypatch):
    monkeypatch.setattr("src.weather.user_agent", lambda _: "offline-test")

    def get(*a, **k):
        class Broken(Response):
            def json(self):
                raise ValueError("malformed")

        return Broken()

    with pytest.raises(WeatherError):
        request_json("mock", {}, "", get=get)
