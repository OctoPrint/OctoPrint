from typing import Optional, Union

from pydantic import Field

from octoprint.schema import BaseModel, BaseModelExtra


class ApiAnalysisVolume(BaseModel):
    minX: float
    minY: float
    minZ: float
    maxX: float
    maxY: float
    maxZ: float


class ApiAnalysisDimensions(BaseModel):
    width: float
    height: float
    depth: float


class ApiAnalysisFilamentUse(BaseModel):
    length: Optional[float] = None
    volume: Optional[float] = None
    weight: Optional[float] = None


class ApiEntryAnalysis(BaseModelExtra):
    printingArea: Optional[ApiAnalysisVolume] = None
    dimensions: Optional[ApiAnalysisDimensions] = None
    travelArea: Optional[ApiAnalysisVolume] = None
    travelDimensions: Optional[ApiAnalysisDimensions] = None
    estimatedPrintTime: Optional[float] = None
    filament: dict[str, ApiAnalysisFilamentUse] = {}


class ApiEntryLastPrint(BaseModel):
    success: bool
    date: float
    printerProfile: Optional[str] = None
    printTime: Optional[float] = None


class ApiEntryPrints(BaseModel):
    success: int = 0
    failure: int = 0
    last: Optional[ApiEntryLastPrint] = None


class ApiEntryStatistics(BaseModelExtra):
    averagePrintTime: dict[str, float] = {}
    lastPrintTime: dict[str, float] = {}


class ApiStorageEntry(BaseModelExtra):
    name: str
    display: str
    origin: str
    path: str
    user: Optional[str] = None

    date: Optional[int] = None
    size: Optional[int] = None

    type_: str = Field(serialization_alias="type")
    typePath: list[str]

    prints: Optional[ApiEntryPrints] = None

    refs: dict[str, str] = {}


class ApiStorageFolder(ApiStorageEntry):
    children: list[Union["ApiStorageFile", "ApiStorageFolder"]] = []

    type_: str = Field("folder", serialization_alias="type")
    typePath: list[str] = ["folder"]


class ApiStorageFile(ApiStorageEntry):
    gcodeAnalysis: Optional[ApiEntryAnalysis] = None
    statistics: Optional[ApiEntryStatistics] = None
