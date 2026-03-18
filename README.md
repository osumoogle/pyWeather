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

### Running with JetBrains Rider

A run configuration is included in `.run/pyWeather.run.xml`. To use it:

1. Install the **Python** plugin from the JetBrains marketplace (Settings > Plugins).
2. Open the project folder in Rider.
3. Ensure your Python interpreter is configured:
   - Go to **Settings > Languages & Frameworks > Python**.
   - Add or select your global Python installation (e.g. `C:\Python314\python.exe`).
4. The **pyWeather** run configuration should appear in the toolbar dropdown. Click the run button to launch the app.

If the configuration does not appear automatically, you can add it manually:
- Go to **Run > Edit Configurations > + > Python**.
- Set **Script** to `main.py` and **Working directory** to the project root.

## Requirements

- Python 3.12+
- Internet connection (for weather data)
- Windows (for automatic theme detection; falls back to light theme on other platforms)

## License

MIT
