from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Location:
    zipcode: str
    city: str
    state: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class ForecastPeriod:
    name: str
    temperature: int
    temperature_unit: str
    wind_speed: str
    wind_direction: str
    short_forecast: str
    detailed_forecast: str
    is_daytime: bool
    precip_probability: int | None


@dataclass(frozen=True)
class Forecast:
    location: Location
    periods: list[ForecastPeriod]
    fetched_at: datetime
