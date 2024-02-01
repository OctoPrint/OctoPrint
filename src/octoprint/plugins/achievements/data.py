from typing import Dict

from pydantic import BaseModel


class StatsBase(BaseModel):
    last_version: str = ""
    """Version of OctoPrint during last start, used for keeping track of updates."""

    seen_versions: int = 0
    """Number of different versions seen."""

    server_starts: int = 0
    """Number of times OctoPrint was started."""

    prints_started: int = 0
    """Number of prints started."""

    prints_cancelled: int = 0
    """Number of prints cancelled."""

    prints_errored: int = 0
    """Number of prints errored."""

    prints_finished: int = 0
    """Number of prints finished."""

    prints_started_per_weekday: Dict[int, int] = {}
    """Number of prints started per weekday."""

    print_duration_total: float = 0
    """Total print duration."""

    print_duration_cancelled: float = 0
    """Total print duration of cancelled prints."""

    print_duration_errored: float = 0
    """Total print duration of errored prints."""

    print_duration_finished: float = 0
    """Total print duration of finished prints."""

    longest_print_duration: float = 0
    """Duration of longest print."""

    longest_print_date: int = 0
    """Timestamp of longest print."""

    files_uploaded: int = 0
    """Number of files uploaded."""

    files_deleted: int = 0
    """Number of files deleted."""

    plugins_installed: int = 0
    """Number of plugins installed."""

    plugins_uninstalled: int = 0
    """Number of plugins uninstalled."""

    most_plugins: int = 0
    """Most plugins installed at once."""


class Stats(StatsBase):
    created: int = 0
    """Timestamp of when stats collection was started."""

    created_version: str = ""
    """Version of OctoPrint when stats collection was started."""


class YearlyStats(StatsBase):
    achievements: int = 0
    """Number of achievements unlocked."""


class State(BaseModel):
    date_last_print: str = ""
    """Date of the last print."""

    prints_today: int = 0
    """Number of prints finished today."""

    date_last_cancelled_print: str = ""
    """Date of the last cancelled print."""

    prints_cancelled_today: int = 0
    """Number of prints cancelled today."""

    consecutive_prints_cancelled_today: int = 0
    """Number of consecutive prints cancelled today."""

    file_last_print: str = ""
    """Name of the file of the last print."""

    consecutive_prints_of_same_file: int = 0
    """Number of consecutive prints of the same file."""

    date_last_weekend_print: str = ""
    """Date of last print that was started on a weekend."""

    consecutive_weekend_prints: int = 0
    """Number of consecutive prints that were started on a weekend."""


class Data(BaseModel):
    stats: Stats
    achievements: Dict[str, int]
    state: State
