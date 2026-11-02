"""Weather lookup via wttr.in.

The original call trusted any HTTP 200 and read it straight out to the user,
so an error page or a rate-limit notice was spoken as if it were a forecast.
This client validates the shape of the response, percent-encodes the city,
sets an explicit User-Agent (wttr.in serves HTML to browser agents) and caps
how much text it will accept.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

import requests

from ..exceptions import WeatherError

logger = logging.getLogger(__name__)

ENDPOINT = "https://wttr.in/{city}"
#: ``%C`` condition, ``%t`` temperature, ``%h`` humidity.
FORMAT = "%C, %t, humidity %h"
USER_AGENT = "curl/8 (voice-web-automation)"

_MAX_RESPONSE_CHARS = 200
_CITY_RE = re.compile(r"^[\w\s.,'\-]{1,80}$", re.UNICODE)
_FAILURE_MARKERS = (
    "unknown location",
    "we were unable",
    "sorry",
    "error",
    "<!doctype",
    "<html",
)


class WeatherClient:
    """Fetches a one-line weather summary for a city."""

    def __init__(
        self,
        timeout: float = 10.0,
        session: requests.Session | None = None,
        endpoint: str = ENDPOINT,
    ) -> None:
        self._timeout = timeout
        self._session = session or requests.Session()
        self._endpoint = endpoint

    def summary(self, city: str) -> str:
        """Return a short description of the weather in ``city``.

        Raises :class:`WeatherError` with a message safe to read aloud.
        """
        cleaned = " ".join((city or "").split())
        if not cleaned:
            raise WeatherError("No city was given")
        if not _CITY_RE.match(cleaned):
            raise WeatherError(f"{cleaned!r} does not look like a place name")

        url = self._endpoint.format(city=quote(cleaned, safe=""))
        try:
            response = self._session.get(
                url,
                params={"format": FORMAT},
                timeout=self._timeout,
                headers={"User-Agent": USER_AGENT, "Accept": "text/plain"},
            )
        except requests.Timeout as exc:
            raise WeatherError("The weather service did not respond in time") from exc
        except requests.RequestException as exc:
            logger.debug("Weather request failed", exc_info=True)
            raise WeatherError("The weather service could not be reached") from exc

        if response.status_code != 200:
            raise WeatherError(
                f"The weather service returned status {response.status_code}"
            )

        text = (response.text or "").strip()
        if not text or len(text) > _MAX_RESPONSE_CHARS:
            raise WeatherError("The weather service returned an unexpected response")
        lowered = text.lower()
        if any(marker in lowered for marker in _FAILURE_MARKERS):
            raise WeatherError(f"No weather data is available for {cleaned}")
        return text
