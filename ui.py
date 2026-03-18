import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import threading
import winreg

from models import Forecast
from validation import validate_zipcode, ValidationError
from settings import load_settings, save_settings
import api

_DARK = {
    "bg": "#1e1e1e",
    "fg": "#d4d4d4",
    "entry_bg": "#2d2d2d",
    "entry_fg": "#d4d4d4",
    "select_bg": "#264f78",
    "tree_bg": "#252526",
    "tree_fg": "#d4d4d4",
    "heading_bg": "#333333",
    "button_bg": "#3a3a3a",
    "error": "#f44747",
}

_LIGHT = {
    "bg": "#f0f0f0",
    "fg": "#1e1e1e",
    "entry_bg": "#ffffff",
    "entry_fg": "#1e1e1e",
    "select_bg": "#0078d4",
    "tree_bg": "#ffffff",
    "tree_fg": "#1e1e1e",
    "heading_bg": "#e0e0e0",
    "button_bg": "#e1e1e1",
    "error": "#d32f2f",
}


def _is_dark_mode() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except OSError:
        return False


def _resolve_dark(theme_pref: str) -> bool:
    if theme_pref == "dark":
        return True
    if theme_pref == "light":
        return False
    return _is_dark_mode()


def _apply_theme(root: tk.Tk, theme_pref: str = "system") -> dict:
    colors = _DARK if _resolve_dark(theme_pref) else _LIGHT
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=colors["bg"])

    style.configure(".", background=colors["bg"], foreground=colors["fg"])
    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
    style.configure("TEntry", fieldbackground=colors["entry_bg"], foreground=colors["entry_fg"])
    style.configure("TButton", background=colors["button_bg"], foreground=colors["fg"])
    style.map("TButton",
              background=[("active", colors["select_bg"])],
              foreground=[("active", "#ffffff")])
    style.configure("TSeparator", background=colors["fg"])

    style.configure("Treeview",
                     background=colors["tree_bg"],
                     foreground=colors["tree_fg"],
                     fieldbackground=colors["tree_bg"],
                     rowheight=24)
    style.configure("Treeview.Heading",
                     background=colors["heading_bg"],
                     foreground=colors["fg"])
    style.map("Treeview",
              background=[("selected", colors["select_bg"])],
              foreground=[("selected", "#ffffff")])

    return colors


class WeatherApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("pyWeather")
        self.root.resizable(False, False)

        self._settings = load_settings()
        self._colors = _apply_theme(root, self._settings["theme"])
        self._forecast_cache: dict[str, Forecast] = {}

        self._build_ui()
        self._center_window()

    def _center_window(self) -> None:
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")

        # Header row
        header_frame = ttk.Frame(frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header_frame.columnconfigure(0, weight=1)

        ttk.Label(header_frame, text="pyWeather", font=("", 14, "bold")).grid(row=0, column=0, sticky="w")

        theme_frame = ttk.Frame(header_frame)
        theme_frame.grid(row=0, column=1, sticky="e")
        ttk.Label(theme_frame, text="Theme:").pack(side="left", padx=(0, 6))
        self.theme_var = tk.StringVar(value=self._settings["theme"])
        theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=["system", "light", "dark"],
            state="readonly",
            width=8,
        )
        theme_combo.pack(side="left")
        theme_combo.bind("<<ComboboxSelected>>", self._on_theme_change)

        ttk.Separator(frame, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=(0, 12))

        # Input row
        input_frame = ttk.Frame(frame)
        input_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))

        ttk.Label(input_frame, text="Zip Code:").pack(side="left", padx=(0, 6))
        self.zip_var = tk.StringVar(value=self._settings.get("last_zipcode", ""))
        self.zip_entry = ttk.Entry(input_frame, textvariable=self.zip_var, width=10)
        self.zip_entry.pack(side="left", padx=(0, 8))
        self.zip_entry.bind("<Return>", self._on_fetch)

        self.fetch_btn = ttk.Button(input_frame, text="Get Forecast", command=self._on_fetch)
        self.fetch_btn.pack(side="left")

        # Error / status row
        self.error_var = tk.StringVar()
        self.error_label = ttk.Label(frame, textvariable=self.error_var, foreground=self._colors["error"])
        self.error_label.grid(row=3, column=0, sticky="w", pady=(0, 2))

        self.status_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.status_var).grid(row=4, column=0, sticky="w", pady=(0, 2))

        # Location label
        self.location_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.location_var, font=("", 10, "bold")).grid(
            row=5, column=0, sticky="w", pady=(0, 8)
        )

        # Treeview for forecast
        ttk.Separator(frame, orient="horizontal").grid(row=6, column=0, sticky="ew", pady=(0, 8))

        columns = ("period", "temp", "wind", "forecast", "precip")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=14)
        self.tree.heading("period", text="Period")
        self.tree.heading("temp", text="Temp")
        self.tree.heading("wind", text="Wind")
        self.tree.heading("forecast", text="Forecast")
        self.tree.heading("precip", text="Precip")
        self.tree.column("period", width=130)
        self.tree.column("temp", width=60, anchor="center")
        self.tree.column("wind", width=110, anchor="center")
        self.tree.column("forecast", width=180)
        self.tree.column("precip", width=60, anchor="center")
        self.tree.grid(row=7, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._on_period_select)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=7, column=1, sticky="ns")

        # Detail area
        ttk.Separator(frame, orient="horizontal").grid(row=8, column=0, sticky="ew", pady=(8, 8))
        ttk.Label(frame, text="Details", font=("", 10, "bold")).grid(row=9, column=0, sticky="w", pady=(0, 4))

        self.detail_text = tk.Text(frame, height=3, wrap="word", state="disabled", relief="flat", borderwidth=0)
        self.detail_text.configure(
            bg=self._colors["entry_bg"],
            fg=self._colors["entry_fg"],
            insertbackground=self._colors["fg"],
            font=("", 10),
        )
        self.detail_text.grid(row=10, column=0, sticky="ew", pady=(0, 4))

        self._periods: list = []

    def _on_theme_change(self, _event: tk.Event) -> None:
        choice = self.theme_var.get()
        self._settings["theme"] = choice
        save_settings(self._settings)
        self._colors = _apply_theme(self.root, choice)
        self.error_label.configure(foreground=self._colors["error"])
        self.detail_text.configure(
            bg=self._colors["entry_bg"],
            fg=self._colors["entry_fg"],
            insertbackground=self._colors["fg"],
        )

    def _on_fetch(self, _event=None) -> None:
        self.error_var.set("")
        self.status_var.set("")

        try:
            zipcode = validate_zipcode(self.zip_var.get())
        except ValidationError as e:
            self.error_var.set(str(e))
            return

        self._settings["last_zipcode"] = zipcode
        save_settings(self._settings)

        # Check cache (30 minute expiry)
        cached = self._forecast_cache.get(zipcode)
        if cached and (datetime.now() - cached.fetched_at) < timedelta(minutes=30):
            self._on_fetch_success(cached)
            return

        self.status_var.set("Loading forecast...")
        self.fetch_btn.configure(state="disabled")
        threading.Thread(target=self._fetch_thread, args=(zipcode,), daemon=True).start()

    def _fetch_thread(self, zipcode: str) -> None:
        try:
            location = api.lookup_location(zipcode)
            forecast = api.fetch_forecast(location)
            self.root.after(0, self._on_fetch_success, forecast)
        except api.WeatherAPIError as e:
            self.root.after(0, self._on_fetch_error, str(e))
        except Exception:
            self.root.after(0, self._on_fetch_error, "An unexpected error occurred.")

    def _on_fetch_success(self, forecast: Forecast) -> None:
        self.fetch_btn.configure(state="normal")
        self.status_var.set("")
        self._forecast_cache[forecast.location.zipcode] = forecast
        self.location_var.set(f"{forecast.location.city}, {forecast.location.state}")
        self._refresh_forecast(forecast)

    def _on_fetch_error(self, message: str) -> None:
        self.fetch_btn.configure(state="normal")
        self.status_var.set("")
        self.error_var.set(message)

    def _refresh_forecast(self, forecast: Forecast) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._periods = list(forecast.periods)
        for p in forecast.periods:
            precip = f"{p.precip_probability}%" if p.precip_probability is not None else "--"
            temp = f"{p.temperature}°{p.temperature_unit}"
            wind = f"{p.wind_speed} {p.wind_direction}"
            self.tree.insert("", "end", values=(p.name, temp, wind, p.short_forecast, precip))

        # Clear detail area
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.configure(state="disabled")

    def _on_period_select(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        index = self.tree.index(selection[0])
        if index < len(self._periods):
            detail = self._periods[index].detailed_forecast
            self.detail_text.configure(state="normal")
            self.detail_text.delete("1.0", "end")
            self.detail_text.insert("1.0", detail)
            self.detail_text.configure(state="disabled")
