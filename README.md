# pyWeather

A lightweight desktop weather application built with Python and Tkinter. Enter a US zip code to get a 7-day forecast from the National Weather Service API.

## Features

- 7-day forecast (14 half-day periods) from api.weather.gov
- Dark/light/system theme support with Windows dark mode detection
- Detailed forecast view for selected periods
- Remembers your last-used zip code
- Zero external dependencies — uses only the Python standard library

## Usage

```bash
python main.py
```

## Requirements

- Python 3.12+
- Internet connection (for weather data)
- Windows (for automatic theme detection; falls back to light theme on other platforms)

## License

MIT
