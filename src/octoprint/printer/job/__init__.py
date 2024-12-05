from typing import Optional

from octoprint.schema import BaseModel


class PrintJob(BaseModel):
    origin: str
    path: str
    size: int = 0
    owner: Optional[str] = None
    path_on_disk: Optional[str] = None

    def __str__(self):
        return f"{self.origin}:{self.path}"

    def __eq__(self, value):
        return self.origin == value.origin and self.path == value.path


class UploadJob(PrintJob):
    remote_path: Optional[str] = None


class JobProgress(BaseModel):
    job: PrintJob
    progress: float
    pos: int
    elapsed: int
    cleaned_elapsed: int
