import datetime

from octoprint.schema import BaseModel


class DurationEstimate(BaseModel):
    estimate: float
    source: str | None = None


class FilamentEstimate(BaseModel):
    length: float | None = None
    volume: float | None = None
    weight: float | None = None


class PrintJob(BaseModel):
    storage: str
    path: str
    plate: int = 1
    display: str
    size: int = 0
    date: datetime.datetime | None = None
    owner: str | None = None
    duration_estimate: DurationEstimate | None = None
    filament_estimate: dict[str, FilamentEstimate] = {}
    path_on_disk: str | None = None

    params: dict | None = None

    def __str__(self):
        return f"{self.storage}:{self.path}"

    def __eq__(self, value):
        if isinstance(value, PrintJob):
            return self.storage == value.storage and self.path == value.path
        if isinstance(value, str):
            return str(self) == value
        return NotImplemented


class UploadJob(PrintJob):
    pass


class JobProgress(BaseModel):
    job: PrintJob
    progress: float
    pos: int
    elapsed: float
    cleaned_elapsed: float
    left_estimate: float | None = None
