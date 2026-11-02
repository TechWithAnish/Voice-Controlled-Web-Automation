"""Weather client behaviour, with HTTP fully mocked."""

from __future__ import annotations

import pytest
import requests
import responses

from voice_automation.exceptions import WeatherError
from voice_automation.services.weather import ENDPOINT, WeatherClient

URL = "https://wttr.in/London"


@responses.activate
def test_successful_lookup():
    responses.add(responses.GET, URL, body="Sunny, +21°C, humidity 40%", status=200)
    assert WeatherClient().summary("London") == "Sunny, +21°C, humidity 40%"


@responses.activate
def test_city_is_percent_encoded():
    responses.add(
        responses.GET,
        "https://wttr.in/New%20York",
        body="Cloudy, +8°C",
        status=200,
    )
    assert WeatherClient().summary("New York") == "Cloudy, +8°C"


@responses.activate
def test_non_200_is_reported():
    responses.add(responses.GET, URL, body="rate limited", status=429)
    with pytest.raises(WeatherError, match="429"):
        WeatherClient().summary("London")


@responses.activate
def test_html_error_page_is_not_read_aloud():
    """A 200 that is actually an error page must not be spoken as a forecast."""
    responses.add(
        responses.GET, URL, body="<!DOCTYPE html><html>oops</html>", status=200
    )
    with pytest.raises(WeatherError):
        WeatherClient().summary("London")


@responses.activate
def test_unknown_location_is_reported():
    responses.add(responses.GET, URL, body="Unknown location; please try ...", status=200)
    with pytest.raises(WeatherError, match="No weather data"):
        WeatherClient().summary("London")


@responses.activate
def test_oversized_response_is_rejected():
    responses.add(responses.GET, URL, body="x" * 5000, status=200)
    with pytest.raises(WeatherError):
        WeatherClient().summary("London")


@responses.activate
def test_empty_response_is_rejected():
    responses.add(responses.GET, URL, body="   ", status=200)
    with pytest.raises(WeatherError):
        WeatherClient().summary("London")


@responses.activate
def test_timeout_is_reported_clearly():
    responses.add(responses.GET, URL, body=requests.Timeout("too slow"))
    with pytest.raises(WeatherError, match="did not respond in time"):
        WeatherClient().summary("London")


@responses.activate
def test_connection_error_is_reported_clearly():
    responses.add(responses.GET, URL, body=requests.ConnectionError("down"))
    with pytest.raises(WeatherError, match="could not be reached"):
        WeatherClient().summary("London")


@pytest.mark.parametrize("city", ["", "   ", "x" * 200, "<script>", "a; rm -rf /"])
def test_invalid_city_never_reaches_the_network(city):
    client = WeatherClient(endpoint=ENDPOINT)
    with pytest.raises(WeatherError):
        client.summary(city)
