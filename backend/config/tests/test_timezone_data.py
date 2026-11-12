"""The project ships its own time zone data instead of relying on the OS image."""

import zoneinfo

from django.conf import settings


def test_time_zone_loads_without_system_zoneinfo() -> None:
    # Empty search path: zoneinfo can only fall back to the `tzdata` package. This fails if
    # tzdata disappears from the dependencies, which CI's Ubuntu runner would otherwise hide.
    zoneinfo.reset_tzpath(to=[])
    try:
        assert zoneinfo.ZoneInfo.no_cache(settings.TIME_ZONE).key == settings.TIME_ZONE
    finally:
        zoneinfo.reset_tzpath()
