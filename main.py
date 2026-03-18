import tkinter as tk
from ui import WeatherApp


def main() -> None:
    root = tk.Tk()
    WeatherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
