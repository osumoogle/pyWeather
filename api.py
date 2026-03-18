import json
import urllib.request
import urllib.error
from datetime import datetime

from models import Location, ForecastPeriod, Forecast

_USER_AGENT = "(pyWeather, contact@email.com)"
_ZIPPOPOTAM_URL = "https://api.zippopotam.us/us/{zipcode}"
_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"

_points_cache: dict[str, str] = {}


class WeatherAPIError(Exception):
    pass


def _make_request(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", _USER_AGENT)
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise WeatherAPIError("Zip code not found. Please check and try again.")
        if e.code in (500, 502, 503):
            raise WeatherAPIError("The weather service is temporarily unavailable. Try again later.")
        raise WeatherAPIError(f"Weather service returned an error (HTTP {e.code}).")
    except urllib.error.URLError:
        raise WeatherAPIError("Could not connect. Check your internet connection.")
    except TimeoutError:
        raise WeatherAPIError("Request timed out. Please try again.")
    except json.JSONDecodeError:
        raise WeatherAPIError("Received an unexpected response from the weather service.")


def lookup_location(zipcode: str) -> Location:
    url = _ZIPPOPOTAM_URL.format(zipcode=zipcode)
    data = _make_request(url)
    try:
        place = data["places"][0]
        return Location(
            zipcode=zipcode,
            city=place["place name"],
            state=place["state abbreviation"],
            latitude=float(place["latitude"]),
            longitude=float(place["longitude"]),
        )
    except (KeyError, IndexError, ValueError, TypeError):
        raise WeatherAPIError("Received an unexpected response for this zip code.")


def fetch_forecast(location: Location) -> Forecast:
    lat = round(location.latitude, 4)
    lon = round(location.longitude, 4)
    cache_key = f"{lat},{lon}"

    if cache_key in _points_cache:
        forecast_url = _points_cache[cache_key]
    else:
        points_url = _POINTS_URL.format(lat=lat, lon=lon)
        points_data = _make_request(points_url)
        try:
            forecast_url = points_data["properties"]["forecast"]
        except (KeyError, TypeError):
            raise WeatherAPIError("Received an unexpected response from the weather service.")
        _points_cache[cache_key] = forecast_url

    forecast_data = _make_request(forecast_url)
    try:
        raw_periods = forecast_data["properties"]["periods"]
        periods = []
        for p in raw_periods:
            precip = p.get("probabilityOfPrecipitation")
            precip_value = precip.get("value") if isinstance(precip, dict) else None
            periods.append(ForecastPeriod(
                name=p["name"],
                temperature=int(p["temperature"]),
                temperature_unit=p["temperatureUnit"],
                wind_speed=p["windSpeed"],
                wind_direction=p["windDirection"],
                short_forecast=p["shortForecast"],
                detailed_forecast=p["detailedForecast"],
                is_daytime=p["isDaytime"],
                precip_probability=int(precip_value) if precip_value is not None else None,
            ))
        return Forecast(location=location, periods=periods, fetched_at=datetime.now())
    except (KeyError, TypeError, ValueError):
        raise WeatherAPIError("Received an unexpected response from the weather service.")
