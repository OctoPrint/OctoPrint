from typing import Optional

from octoprint.schema import BaseModel


class DurationEstimate(BaseModel):
    estimate: float
    source: Optional[str] = None


class FilamentEstimate(BaseModel):
    length: Optional[float] = None
    volume: Optional[float] = None
    weight: Optional[float] = None


class PrintJob(BaseModel):
    storage: str
    path: str
    display: str
    size: int = 0
    date: Optional[int] = None
    owner: Optional[str] = None
    duration_estimate: Optional[DurationEstimate] = None
    filament_estimate: dict[str, FilamentEstimate] = {}
    path_on_disk: Optional[str] = None

    params: Optional[dict] = None

    def __str__(self):
        return f"{self.storage}:{self.path}"

    def __eq__(self, value):
        return self.storage == value.origin and self.path == value.path


class UploadJob(PrintJob):
    remote_path: Optional[str] = None


class JobProgress(BaseModel):
    job: PrintJob
    progress: float
    pos: int
    elapsed: float
    cleaned_elapsed: float
    left_estimate: Optional[float] = None
