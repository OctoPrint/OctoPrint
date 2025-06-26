from typing import Optional

from octoprint.schema import BaseModel


class PrintJob(BaseModel):
    storage: str
    path: str
    size: int = 0
    owner: Optional[str] = None
    path_on_disk: Optional[str] = None

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
