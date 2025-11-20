from typing import Optional

from octoprint.schema import BaseModel


class ApiJobFile(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    display: Optional[str] = None
    origin: Optional[str] = None
    size: Optional[int] = None
    date: Optional[int] = None


class ApiJobInfo(BaseModel):
    file: ApiJobFile
    estimatedPrintTime: Optional[float] = None
    filament: Optional[dict[str, dict[str, float]]] = None
    user: Optional[str] = None


class ApiProgressInfo(BaseModel):
    completion: Optional[int] = None
    filepos: Optional[int] = None
    printTime: Optional[int] = None
    printTimeLeft: Optional[int] = None
    printTimeLeftOrigin: Optional[str] = None


class ApiJobResponse(BaseModel):
    job: ApiJobInfo
    progress: ApiProgressInfo
    state: str
    error: Optional[str] = None
