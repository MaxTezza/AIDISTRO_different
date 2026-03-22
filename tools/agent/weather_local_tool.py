#!/usr/bin/env python3
import os
import sys


def target_day(payload: str) -> str:
    p = (payload or "today").strip().lower()
    if "tomorrow" in p:
        return "tomorrow"
    return "today"


def local_forecast(location: str, day_label: str):
    seed = sum(ord(ch) for ch in f"{location.lower()}:{day_label}")
    base = 10 + (seed % 14)
    swing = 6 + (seed % 7)
    min_c = base
    max_c = base + swing
    rain = (seed * 7) % 75
    return {
        "location": location,
        "min_c": min_c,
        "max_c": max_c,
        "rain": rain,
    }


def main():
    payload = "today" if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    day_label = target_day(payload)
    location = os.environ.get("AI_DISTRO_WEATHER_LOCATION", "Austin").strip() or "Austin"
    forecast = local_forecast(location, day_label)
    print(
        f"{forecast['location']} {day_label}: "
        f"{forecast['min_c']}C to {forecast['max_c']}C, "
        f"rain chance up to {forecast['rain']}%."
    )


if __name__ == "__main__":
    main()
