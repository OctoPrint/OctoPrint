from octoprint.schema import BaseModel


class ApiJobFile(BaseModel):
    name: str | None = None
    """Internal name of the file being printed"""
    path: str | None = None
    """Path of the file being printed"""
    display: str | None = None
    """Display name of the file being printed"""
    origin: str | None = None
    """Storage of the file being printed"""
    size: int | None = None
    """Size of the file being printed in bytes"""
    date: int | None = None
    """Last modification date of the file being printed as timestamp"""
    upload: bool | None = None
    """Whether this file is currently being uploaded (true) or already available on the storage (false)"""


class ApiJobInfo(BaseModel):
    file: ApiJobFile
    """File being printed"""
    estimatedPrintTime: float | None = None
    """Estimated print time in seconds, if known"""
    filament: dict[str, dict[str, float | None] | None] | None = None
    """Filament usage information as mapping from printer profile to mappings from tool to used length, if known"""
    user: str | None = None
    """The user who started the job, if known"""


class ApiJobInfo_pre_2_0_0(ApiJobInfo):
    lastPrintTime: float | None = None
    """The last print time in seconds"""


class ApiProgressInfo(BaseModel):
    completion: float | None = None
    """Completion in percentage, if known"""
    filepos: int | None = None
    """Current file position, if known"""
    printTime: int | None = None
    """Print time so far"""
    printTimeLeft: int | None = None
    """Estimated print time left"""
    printTimeLeftOrigin: str | None = None
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
    error: str | None = None
    """Error, if any"""


class ApiJobResponse_pre_2_0_0(ApiJobResponse):
    job: ApiJobInfo_pre_2_0_0
    """Information about the current job"""
