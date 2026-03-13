from typing import Optional

from octoprint.schema import BaseModel


class ApiJobFile(BaseModel):
    name: Optional[str] = None
    """Internal name of the file being printed"""
    path: Optional[str] = None
    """Path of the file being printed"""
    display: Optional[str] = None
    """Display name of the file being printed"""
    origin: Optional[str] = None
    """Storage of the file being printed"""
    size: Optional[int] = None
    """Size of the file being printed in bytes"""
    date: Optional[int] = None
    """Last modification date of the file being printed as timestamp"""
    upload: Optional[bool] = None
    """Whether this file is currently being uploaded (true) or already available on the storage (false)"""


class ApiJobInfo(BaseModel):
    file: ApiJobFile
    """File being printed"""
    estimatedPrintTime: Optional[float] = None
    """Estimated print time in seconds, if known"""
    filament: Optional[dict[str, Optional[dict[str, float]]]] = None
    """Filament usage information as mapping from printer profile to mappings from tool to used length, if known"""
    user: Optional[str] = None
    """The user who started the job, if known"""


class ApiJobInfo_pre_1_12(ApiJobInfo):
    lastPrintTime: Optional[float] = None
    """The last print time in seconds"""


class ApiProgressInfo(BaseModel):
    completion: Optional[int] = None
    """Completion in percentage, if known"""
    filepos: Optional[int] = None
    """Current file position, if known"""
    printTime: Optional[int] = None
    """Print time so far"""
    printTimeLeft: Optional[int] = None
    """Estimated print time left"""
    printTimeLeftOrigin: Optional[str] = None
    """
    Origin of estimate.

    E.g.:

    * ``linear``: based on a linear approximation of the progress in file in bytes vs time
    * ``analysis``: based on an analysis of the file
    * ``estimate``: calculated estimate after stabilization of linear estimation
    * ``average``: based on the average total from past prints of the same model against the same printer profile
    * ``mixed-analysis``: mixture of ``estimate`` and ``analysis``
    * ``mixed-average``: mixture of ``estimate`` and ``average``
    * ``printer``: estimate by printer
    """


class ApiJobResponse(BaseModel):
    job: ApiJobInfo
    """Information about the current job"""
    progress: ApiProgressInfo
    """Information about the current job's progress"""
    state: str
    """Current state"""
    error: Optional[str] = None
    """Error, if any"""


class ApiJobResponse_pre_1_12(ApiJobResponse):
    job: ApiJobInfo_pre_1_12
    """Information about the current job"""
