__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import hashlib
import logging
import os
import threading
from collections.abc import Iterable
from urllib.parse import quote as urlquote

import psutil
from flask import abort, jsonify, make_response, request, url_for
from werkzeug.exceptions import HTTPException

import octoprint.filemanager
import octoprint.filemanager.storage
import octoprint.filemanager.util
import octoprint.slicing
from octoprint.access.permissions import Permissions
from octoprint.events import Events
from octoprint.filemanager.destinations import FileDestinations
from octoprint.filemanager.storage import (
    AnalysisDimensions,
    AnalysisFilamentUse,
    AnalysisVolume,
    StorageEntry,
    StorageError,
    StorageFile,
    StorageFolder,
)
from octoprint.schema.api import files as apischema
from octoprint.server import (
    NO_CONTENT,
    current_user,
    eventManager,
    fileManager,
    printer,
    slicingManager,
)
from octoprint.server.api import api
from octoprint.server.util.flask import (
    get_json_command_from_request,
    no_firstrun_access,
    with_revalidation_checking,
)
from octoprint.settings import settings, valid_boolean_trues
from octoprint.util import time_this

# ~~ GCODE file handling

_file_cache = {}
_file_cache_mutex = threading.RLock()

_DATA_FORMAT_VERSION = "v3"

_logger = logging.getLogger(__name__)


def _create_lastmodified(path, recursive):
    path = path[len("/api/files") :]
    if path.startswith("/"):
        path = path[1:]

    if path == "":
        # all storages involved
        lms = [0]
        for storage in fileManager.registered_storages:
            try:
                lms.append(fileManager.last_modified(storage, recursive=recursive))
            except octoprint.filemanager.NoSuchStorage:
                pass
            except Exception:
                _logger.exception(
                    "There was an error retrieving the last modified data from storage {}".format(
                        storage
                    )
                )

        lms = filter(lambda x: x is not None, lms)
        if not lms:
            return None

        # return the maximum of all dates
        return max(lms)

    else:
        if "/" in path:
            storage, path_in_storage = path.split("/", 1)
        else:
            storage = path
            path_in_storage = None

        try:
            return fileManager.last_modified(
                storage, path=path_in_storage, recursive=recursive
            )
        except octoprint.filemanager.NoSuchStorage:
            pass
        except Exception:
            _logger.exception(
                "There was an error retrieving the last modified data from storage {} and path {}".format(
                    storage, path_in_storage
                )
            )
        return None


def _create_etag(path, filter=None, recursive=False, lm=None):
    if lm is None:
        lm = _create_lastmodified(path, recursive)

    if lm is None:
        return None

    path = path[len("/api/files") :]
    if path.startswith("/"):
        path = path[1:]

    storage_hashes = []
    if path == "":
        # all storages involved
        for storage in sorted(fileManager.registered_storages):
            try:
                storage_hashes.append(fileManager.hash(storage, recursive=recursive))
            except octoprint.filemanager.NoSuchStorage:
                pass
            except Exception:
                _logger.exception(
                    f"There was an error retrieving the hash from storage {storage}"
                )

    else:
        if "/" in path:
            storage, path_in_storage = path.split("/", 1)
        else:
            storage = path
            path_in_storage = None

        try:
            storage_hashes.append(
                fileManager.hash(storage, path=path_in_storage, recursive=recursive)
            )
        except octoprint.filemanager.NoSuchStorage:
            pass
        except Exception:
            _logger.exception(
                f"There was an error retrieving the hash from storage {storage} and path {path}"
            )

    hash = hashlib.sha1()

    def hash_update(value):
        value = value.encode("utf-8")
        hash.update(value)

    hash_update(str(lm))
    hash_update(",".join(storage_hashes))
    hash_update(str(filter))
    hash_update(str(recursive))

    hash_update(_DATA_FORMAT_VERSION)  # increment version if we change the API format

    return hash.hexdigest()


@api.route("/files", methods=["GET"])
@Permissions.FILES_LIST.require(403)
@with_revalidation_checking(
    etag_factory=lambda lm=None: _create_etag(
        request.path,
        request.values.get("filter", False),
        request.values.get("recursive", False),
        lm=lm,
    ),
    lastmodified_factory=lambda: _create_lastmodified(
        request.path, request.values.get("recursive", False)
    ),
    unless=lambda: request.values.get("force", False)
    or request.values.get("_refresh", False),
)
def readGcodeFiles():
    filter = request.values.get("filter", False)
    recursive = request.values.get("recursive", "false") in valid_boolean_trues
    force = request.values.get("force", "false") in valid_boolean_trues

    files = []
    storages = {}
    for storage, meta in fileManager.registered_storage_meta.items():
        try:
            files.extend(
                _getFileList(
                    storage,
                    filter=filter,
                    recursive=recursive,
                    allow_from_cache=not force,
                )
            )
            storages[meta.key] = {
                "key": meta.key,
                "name": meta.name,
                "capabilities": meta.capabilities.model_dump(by_alias=True),
            }
        except octoprint.filemanager.NoSuchStorage:
            pass

    usage = psutil.disk_usage(settings().getBaseFolder("uploads", check_writable=False))

    return jsonify(files=files, free=usage.free, total=usage.total, storages=storages)


@api.route("/files/test", methods=["POST"])
@Permissions.FILES_LIST.require(403)
def runFilesTest():
    valid_commands = {
        "sanitize": ["storage", "path", "filename"],
        "exists": ["storage", "path", "filename"],
    }

    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    def sanitize(storage, path, filename):
        sanitized_path = fileManager.sanitize_path(storage, path)
        sanitized_name = fileManager.sanitize_name(storage, filename)
        joined = fileManager.join_path(storage, sanitized_path, sanitized_name)
        return sanitized_path, sanitized_name, joined

    try:
        if command == "sanitize":
            _, _, sanitized = sanitize(data["storage"], data["path"], data["filename"])
            return jsonify(sanitized=sanitized)

        elif command == "exists":
            storage = data["storage"]
            path = data["path"]
            filename = data["filename"]

            sanitized_path, sanitized_name, sanitized = sanitize(storage, path, filename)

            exists = _getFileDetails(storage, sanitized)
            if exists:
                suggestion = sanitized_name
                name, ext = os.path.splitext(sanitized_name)
                counter = 0
                while fileManager.file_exists(
                    storage,
                    fileManager.join_path(
                        storage,
                        sanitized_path,
                        suggestion,
                    ),
                ):
                    counter += 1
                    suggestion = fileManager.sanitize_name(
                        storage, f"{name}_{counter}{ext}"
                    )
                return jsonify(
                    exists=True,
                    suggestion=suggestion,
                    size=exists.get("size"),
                    date=exists.get("date"),
                )
            else:
                return jsonify(exists=False)

    except octoprint.filemanager.NoSuchStorage:
        abort(400)


@api.route("/files/<string:origin>", methods=["GET"])
@Permissions.FILES_LIST.require(403)
@with_revalidation_checking(
    etag_factory=lambda lm=None: _create_etag(
        request.path,
        request.values.get("filter", False),
        request.values.get("recursive", False),
        lm=lm,
    ),
    lastmodified_factory=lambda: _create_lastmodified(
        request.path, request.values.get("recursive", False)
    ),
    unless=lambda: request.values.get("force", False)
    or request.values.get("_refresh", False),
)
def readGcodeFilesForOrigin(origin):
    try:
        filter = request.values.get("filter", False)
        recursive = request.values.get("recursive", "false") in valid_boolean_trues
        force = request.values.get("force", "false") in valid_boolean_trues

        files = _getFileList(
            origin, filter=filter, recursive=recursive, allow_from_cache=not force
        )

        if origin == FileDestinations.LOCAL:
            usage = psutil.disk_usage(
                settings().getBaseFolder("uploads", check_writable=False)
            )
            return jsonify(files=files, free=usage.free, total=usage.total)
        else:
            return jsonify(files=files)

    except octoprint.filemanager.NoSuchStorage:
        abort(404)


@api.route("/files/<string:target>/<path:filename>", methods=["GET"])
@Permissions.FILES_LIST.require(403)
@with_revalidation_checking(
    etag_factory=lambda lm=None: _create_etag(
        request.path,
        lm=lm,
    ),
    lastmodified_factory=lambda: _create_lastmodified(request.path, False),
    unless=lambda: request.values.get("force", False)
    or request.values.get("_refresh", False),
)
def readGcodeFile(target, filename):
    try:
        if not _validate_filename(target, filename):
            abort(404)

        file = _getFileDetails(target, filename)
        if not file:
            abort(404)

        return jsonify(file.model_dump(by_alias=True, exclude_none=True))

    except octoprint.filemanager.NoSuchStorage:
        abort(404)


def _getFileDetails(origin, path):
    if "/" in path:
        parent, _ = path.rsplit("/", 1)
    else:
        parent = None

    data = fileManager.get_storage_entry(origin, path)
    if not data:
        return None

    return _analyse_and_convert_recursively(origin, [data], path=parent)[0]


@time_this(
    logtarget=__name__ + ".timings",
    message="{func}({func_args},{func_kwargs}) took {timing:.2f}ms",
    incl_func_args=True,
    log_enter=True,
    message_enter="Entering {func}({func_args},{func_kwargs})...",
)
def _getFileList(
    origin, path=None, filter=None, recursive=False, level=0, allow_from_cache=True
):
    # PERF: Only retrieve the extension tree once
    extension_tree = octoprint.filemanager.full_extension_tree()

    filter_func = None
    if filter:
        filter_func = lambda entry: octoprint.filemanager.valid_file_type(
            entry.name, type=filter, tree=extension_tree
        )

    with _file_cache_mutex:
        cache_key = f"{origin}:{path}:{recursive}:{filter}"
        files, lastmodified, storage_hash = _file_cache.get(cache_key, ([], None, None))
        # recursive needs to be True for so we get lastmodified & hash of whole subtree - #3422
        if (
            not allow_from_cache
            or storage_hash is None
            or storage_hash != fileManager.hash(origin, path=path, recursive=True)
            or lastmodified is None
            or lastmodified < fileManager.last_modified(origin, path=path, recursive=True)
        ):
            files = list(
                fileManager.list_storage_entries(
                    locations=[origin],
                    path=path,
                    filter=filter_func,
                    recursive=recursive,
                    level=level,
                    force_refresh=not allow_from_cache,
                )
                .get(origin, {})
                .values()
            )
            lastmodified = fileManager.last_modified(origin, path=path, recursive=True)
            _file_cache[cache_key] = (files, lastmodified, storage_hash)

    result = _analyse_and_convert_recursively(
        origin, files, extension_tree=extension_tree
    )
    return [x.model_dump(by_alias=True, exclude_none=True) for x in result]


def _analyse_and_convert_recursively(
    origin: str, files: Iterable[StorageEntry], path: str = None, extension_tree=None
) -> list[apischema.ApiStorageEntry]:
    if path is None:
        path = ""

    if extension_tree is None:
        extension_tree = octoprint.filemanager.full_extension_tree()

    result = []
    for entry in files:
        if isinstance(entry, StorageFolder):
            children = []
            prints = None

            if entry.children:
                children = _analyse_and_convert_recursively(
                    origin,
                    entry.children.values(),
                    path=path + entry.name + "/",
                )

                latest_print: apischema.ApiEntryLastPrint = None
                success = 0
                failure = 0
                for child in children:
                    if not child.prints or not child.prints.last:
                        continue
                    success += child.prints.success
                    failure += child.prints.failure

                    if latest_print is None or child.prints.last.date > latest_print.date:
                        latest_print = child.prints.last

                prints = apischema.ApiEntryPrints(
                    success=success, failure=failure, last=latest_print
                )

            result.append(
                apischema.ApiStorageFolder(
                    name=entry.name,
                    display=entry.display,
                    origin=entry.origin,
                    path=entry.path,
                    user=entry.user,
                    date=entry.date,
                    size=entry.size,
                    children=children,
                    prints=prints,
                    refs={
                        "resource": url_for(
                            ".readGcodeFile",
                            target=origin,
                            filename=path + entry.name,
                            _external=True,
                        )
                    },
                )
            )

        elif isinstance(entry, StorageFile):
            analysis: apischema.ApiEntryAnalysis = None
            prints: apischema.ApiEntryPrints = None
            metadata: apischema.ApiEntryStatistics = None

            additional = {}

            if entry.metadata and octoprint.filemanager.valid_file_type(
                entry.name, type="gcode", tree=extension_tree
            ):
                # convert metadata
                metadata = apischema.ApiEntryStatistics()

                if entry.metadata.statistics:
                    metadata.averagePrintTime = entry.metadata.statistics.averagePrintTime
                    metadata.lastPrintTime = entry.metadata.statistics.lastPrintTime

                # convert analysis
                if entry.metadata.analysis:

                    def _to_volume(val: AnalysisVolume) -> apischema.ApiAnalysisVolume:
                        if val is None:
                            return None
                        return apischema.ApiAnalysisVolume(
                            minX=val.minX,
                            minY=val.minY,
                            minZ=val.minZ,
                            maxX=val.maxX,
                            maxY=val.maxY,
                            maxZ=val.maxZ,
                        )

                    def _to_dimensions(
                        val: AnalysisDimensions,
                    ) -> apischema.ApiAnalysisDimensions:
                        if val is None:
                            return None
                        return apischema.ApiAnalysisDimensions(
                            width=val.width, height=val.height, depth=val.depth
                        )

                    def _to_filament_use(
                        val: dict[str, AnalysisFilamentUse],
                    ) -> dict[str, apischema.ApiAnalysisFilamentUse]:
                        if val is None:
                            return None
                        result = {}
                        for t, d in val.items():
                            result[t] = apischema.ApiAnalysisFilamentUse(
                                length=d.length, volume=d.volume, weight=d.weight
                            )
                        return result

                    analysis = apischema.ApiEntryAnalysis(
                        printingArea=_to_volume(entry.metadata.analysis.printingArea),
                        dimensions=_to_dimensions(entry.metadata.analysis.dimensions),
                        travelArea=_to_volume(entry.metadata.analysis.travelArea),
                        travelDimensions=_to_dimensions(
                            entry.metadata.analysis.travelDimensions
                        ),
                        estimatedPrintTime=entry.metadata.analysis.estimatedPrintTime,
                        filament=_to_filament_use(entry.metadata.analysis.filament),
                        **entry.metadata.analysis.additional,
                    )

                # convert history
                if entry.metadata.history:
                    success = 0
                    failure = 0
                    last = None

                    for h in entry.metadata.history:
                        if h.success:
                            success += 1
                        else:
                            failure += 1

                        if not last or h.timestamp > last.date:
                            last = apischema.ApiEntryLastPrint(
                                success=h.success,
                                date=h.timestamp,
                                printerProfile=h.printerProfile,
                                printTime=h.printTime,
                            )

                    prints = apischema.ApiEntryPrints(
                        success=success, failure=failure, last=last
                    )

                # fetch additional data
                additional = entry.metadata.additional

            # create refs
            refs = {
                "resource": url_for(
                    ".readGcodeFile",
                    target=origin,
                    filename=entry.path,
                    _external=True,
                )
            }

            if fileManager.capabilities(origin).read_file:
                quoted_path = urlquote(entry.path)
                url = (
                    url_for("index", _external=True)
                    + f"downloads/files/{origin}/{quoted_path}"
                )
                refs["download"] = url

            if fileManager.capabilities(origin).thumbnails and len(entry.thumbnails):
                quoted_path = urlquote(entry.path)
                url = (
                    url_for("index", _external=True)
                    + f"downloads/thumbs/{origin}/{quoted_path}"
                )

                for size in entry.thumbnails:
                    refs[f"thumbnail_{size}"] = url + "?size=" + size
                refs["thumbnail"] = url

            result.append(
                apischema.ApiStorageFile(
                    name=entry.name,
                    display=entry.display,
                    origin=entry.origin,
                    path=entry.path,
                    user=entry.user,
                    date=entry.date,
                    size=entry.size,
                    type_=entry.entry_type,
                    typePath=entry.type_path,
                    prints=prints,
                    refs=refs,
                    gcodeAnalysis=analysis,
                    **additional,
                )
            )

    return result


def _verifyFileExists(origin, filename):
    return fileManager.file_exists(origin, filename)


def _verifyFolderExists(origin, foldername):
    return fileManager.folder_exists(origin, foldername)


def _isBusy(target, path):  # TODO
    currentOrigin, currentPath = _getCurrentFile()
    if (
        currentPath is not None
        and currentOrigin == target
        and fileManager.file_in_path(FileDestinations.LOCAL, path, currentPath)
        and (printer.is_printing() or printer.is_paused())
    ):
        return True

    return any(
        target == x[0] and fileManager.file_in_path(FileDestinations.LOCAL, path, x[1])
        for x in fileManager.get_busy_files()
    )


@api.route("/files/<string:target>", methods=["POST"])
@no_firstrun_access
@Permissions.FILES_UPLOAD.require(403)
def uploadGcodeFile(target):
    input_name = "file"
    input_upload_name = (
        input_name + "." + settings().get(["server", "uploads", "nameSuffix"])
    )
    input_upload_path = (
        input_name + "." + settings().get(["server", "uploads", "pathSuffix"])
    )

    user = current_user.get_name()

    try:
        if input_upload_name in request.values and input_upload_path in request.values:
            upload_name = request.values[input_upload_name]
            upload_path = request.values[input_upload_path]

            if not fileManager.capabilities(target).write_file:
                abort(400, description="storage does not support adding new files")

            # Store any additional user data the caller may have passed.
            userdata = None
            if "userdata" in request.values:
                import json

                try:
                    userdata = json.loads(request.values["userdata"])
                except Exception:
                    abort(400, description="userdata contains invalid JSON")

            # evaluate select and print parameter and if set check permissions & preconditions
            # and adjust as necessary
            #
            # we do NOT abort(409) here since this would be a backwards incompatible behaviour change
            # on the API, but instead return the actually effective select and print flags in the response
            #
            # note that this behaviour might change in a future API version
            select_request = (
                "select" in request.values
                and request.values["select"] in valid_boolean_trues
                and Permissions.FILES_SELECT.can()
            )
            print_request = (
                "print" in request.values
                and request.values["print"] in valid_boolean_trues
                and Permissions.PRINT.can()
            )

            to_select = select_request
            to_print = print_request
            if (to_select or to_print) and not (
                printer.is_operational()
                and not (printer.is_printing() or printer.is_paused())
            ):
                # can't select or print files if not operational or ready
                to_select = to_print = False

            # determine future filename of file to be uploaded, abort if it can't be uploaded
            try:
                canonicalizedPath, canonFilename = fileManager.canonicalize(
                    target, upload_name
                )
                if request.values.get("path"):
                    canonicalizedPath = request.values.get("path")
                if request.values.get("filename"):
                    canonFilename = request.values.get("filename")

                futurePath = fileManager.sanitize_path(target, canonicalizedPath)
                futureFilename = fileManager.sanitize_name(
                    FileDestinations.LOCAL, canonFilename
                )
            except Exception:
                _logger.exception(f"Error canonicalizing {upload_name} against {target}")
                canonFilename = None
                futurePath = None
                futureFilename = None

            if futureFilename is None:
                abort(400, description="Can not upload file, invalid file name")

            # prohibit overwriting currently selected file while it's being printed
            futureFullPath = fileManager.join_path(target, futurePath, futureFilename)
            futureFullPathInStorage = fileManager.path_in_storage(target, futureFullPath)

            if (
                str(printer.active_job) == f"{target}:{futureFullPathInStorage}"
            ):  # this should no longer require to be a full path in storage
                abort(
                    409,
                    description="Trying to overwrite file that is currently being printed",
                )

            if (
                fileManager.file_exists(target, futureFullPathInStorage)
                and request.values.get("noOverwrite") in valid_boolean_trues
            ):
                abort(409, description="File already exists and noOverwrite was set")

            if (
                fileManager.file_exists(target, futureFullPathInStorage)
                and not Permissions.FILES_DELETE.can()
            ):
                abort(
                    403,
                    description="File already exists, cannot overwrite due to a lack of permissions",
                )

            reselect = str(printer.active_job) == f"{target}:{futureFullPathInStorage}"

            upload_done = False

            def progress_callback(progress=None, done=False, failed=False):
                nonlocal upload_done
                upload_done = done or failed

            try:
                upload = octoprint.filemanager.util.DiskFileWrapper(
                    upload_name, upload_path
                )

                added_file = fileManager.add_file(
                    target,
                    futureFullPathInStorage,
                    upload,
                    allow_overwrite=True,
                    display=canonFilename,
                    user=user,
                    progress_callback=progress_callback,
                )
            except (OSError, StorageError) as e:
                _abortWithException(e)

            if octoprint.filemanager.valid_file_type(added_file, "gcode") and (
                to_select or to_print or reselect
            ):
                job = fileManager.create_job(target, added_file, owner=user)
                printer.set_job(job, printer_after_select=to_print)

            if userdata is not None:
                # upload included userdata, add this now to the metadata
                fileManager.set_additional_metadata(
                    target, added_file, "userdata", userdata
                )

            payload = {
                "name": futureFilename,
                "path": added_file,
                "target": target,
                "select": select_request,
                "print": print_request,
                "effective_select": to_select,
                "effective_print": to_print,
            }
            if userdata is not None:
                payload["userdata"] = userdata
            eventManager.fire(Events.UPLOAD, payload)

            entry = {
                "name": futureFilename,
                "path": added_file,
                "origin": target,
                "refs": {
                    "resource": url_for(
                        ".readGcodeFile",
                        target=target,
                        filename=added_file,
                        _external=True,
                    ),
                },
            }
            if fileManager.capabilities(target).read_file:
                quoted_name = urlquote(added_file)
                entry["refs"]["download"] = (
                    url_for("index", _external=True)
                    + f"downloads/files/{target}/{quoted_name}"
                )

            r = make_response(
                jsonify(
                    files={target: entry},
                    done=upload_done,
                    effectiveSelect=to_select,
                    effectivePrint=to_print,
                ),
                201,
            )
            r.headers["Location"] = entry["refs"]["resource"]
            return r

        elif "foldername" in request.values:
            foldername = request.values["foldername"]

            if (
                target not in fileManager.registered_storages
                or not fileManager.capabilities(target).add_folder
            ):
                abort(400, description="target is invalid")

            canonicalizedPath, canonicalizedName = fileManager.canonicalize(
                target, foldername
            )
            futurePath = fileManager.sanitize_path(target, canonicalizedPath)
            futureName = fileManager.sanitize_name(target, canonicalizedName)
            if not futureName or not futurePath:
                abort(400, description="folder name is empty")

            if "path" in request.values and request.values["path"]:
                futurePath = fileManager.sanitize_path(target, request.values["path"])

            futureFullPath = fileManager.join_path(target, futurePath, futureName)
            if octoprint.filemanager.valid_file_type(futureName):
                abort(409, description="Can't create folder, please try another name")

            try:
                added_folder = fileManager.add_folder(
                    target,
                    futureFullPath,
                    display=canonicalizedName,
                    user=user,
                )
            except (OSError, StorageError) as e:
                _abortWithException(e)

            folder = {
                "name": futureName,
                "path": added_folder,
                "origin": target,
                "refs": {
                    "resource": url_for(
                        ".readGcodeFile",
                        target=target,
                        filename=added_folder,
                        _external=True,
                    )
                },
            }

            r = make_response(jsonify(folder=folder, done=True), 201)
            r.headers["Location"] = folder["refs"]["resource"]
            return r

        else:
            abort(400, description="No file to upload and no folder to create")

    except octoprint.filemanager.NoSuchStorage:
        abort(404)


@api.route("/files/<string:storage>/<path:path>", methods=["POST"])
@no_firstrun_access
def gcodeFileCommand(storage, path):
    try:
        if not _validate_filename(storage, path):
            abort(404)

        # valid file commands, dict mapping command name to mandatory parameters
        valid_commands = {
            "select": [],
            "unselect": [],
            "slice": [],
            "analyse": [],
            "copy": ["destination"],
            "move": ["destination"],
            "copy_storage": ["storage", "destination"],
            "move_storage": ["storage", "destination"],
            "uploadSd": [],
        }

        command, data, response = get_json_command_from_request(request, valid_commands)
        if response is not None:
            return response

        if command == "uploadSd":
            command = "copy_storage"
            data["storage"] = "printer"
            data["destination"] = path
            _logger.warning(
                "File command 'uploadSD' is outdated, use 'copy_storage' with storage 'printer' instead"
            )

        user = current_user.get_name()

        if command == "select":
            with Permissions.FILES_SELECT.require(403):
                if not _verifyFileExists(storage, path):
                    abort(404)

                # selects/loads a file
                if not octoprint.filemanager.valid_file_type(path, type="machinecode"):
                    abort(
                        415,
                        description="Cannot select file for printing, not a machinecode file",
                    )

                if not printer.is_ready():
                    abort(
                        409,
                        description="Printer is already printing, cannot select a new file",
                    )

                start_print = False
                if "print" in data and data["print"] in valid_boolean_trues:
                    with Permissions.PRINT.require(403):
                        if not printer.is_operational():
                            abort(
                                409,
                                description="Printer is not operational, cannot directly start printing",
                            )
                        start_print = True

                params = data.get("params", {})
                job = fileManager.create_job(storage, path, owner=user, params=params)
                printer.set_job(job, print_after_select=start_print)

        elif command == "unselect":
            with Permissions.FILES_SELECT.require(403):
                if not printer.is_ready():
                    return make_response(
                        "Printer is already printing, cannot unselect current file", 409
                    )

                _, currentFilename = _getCurrentFile()
                if currentFilename is None:
                    return make_response(
                        "Cannot unselect current file when there is no file selected", 409
                    )

                if path != currentFilename and path != "current":
                    return make_response(
                        "Only the currently selected file can be unselected", 400
                    )

                printer.set_job(None)

        elif command == "slice":
            with Permissions.SLICE.require(403):
                if not fileManager.capabilities(storage).path_on_disk:
                    abort(
                        400, description=f"Slicing is not supported on storage {storage}"
                    )

                if not _verifyFileExists(storage, path):
                    abort(404)

                try:
                    if "slicer" in data:
                        slicer = data["slicer"]
                        del data["slicer"]
                        slicer_instance = slicingManager.get_slicer(slicer)

                    elif "cura" in slicingManager.registered_slicers:
                        slicer = "cura"
                        slicer_instance = slicingManager.get_slicer("cura")

                    else:
                        abort(415, description="Cannot slice file, no slicer available")
                except octoprint.slicing.UnknownSlicer:
                    abort(404)

                if not any(
                    octoprint.filemanager.valid_file_type(path, type=source_file_type)
                    for source_file_type in slicer_instance.get_slicer_properties().get(
                        "source_file_types", ["model"]
                    )
                ):
                    abort(415, description="Cannot slice file, not a model file")

                cores = psutil.cpu_count()
                if (
                    slicer_instance.get_slicer_properties().get("same_device", True)
                    and (printer.is_printing() or printer.is_paused())
                    and (cores is None or cores < 2)
                ):
                    # slicer runs on same device as OctoPrint, slicing while printing is hence disabled
                    abort(
                        409,
                        description="Cannot slice on this slicer while printing on single core systems or systems of unknown core count due to performance reasons",
                    )

                if "destination" in data and data["destination"]:
                    destination = data["destination"]
                    del data["destination"]
                elif "gcode" in data and data["gcode"]:
                    destination = data["gcode"]
                    del data["gcode"]
                else:
                    import os

                    name, _ = os.path.splitext(path)
                    destination = (
                        name
                        + "."
                        + slicer_instance.get_slicer_properties().get(
                            "destination_extensions", ["gco", "gcode", "g"]
                        )[0]
                    )

                full_path = destination
                if "path" in data and data["path"]:
                    full_path = fileManager.join_path(storage, data["path"], destination)
                else:
                    path, _ = fileManager.split_path(storage, path)
                    if path:
                        full_path = fileManager.join_path(storage, path, destination)

                canon_path, canon_name = fileManager.canonicalize(storage, full_path)
                sanitized_name = fileManager.sanitize_name(storage, canon_name)

                if canon_path:
                    full_path = fileManager.join_path(storage, canon_path, sanitized_name)
                else:
                    full_path = sanitized_name

                # prohibit overwriting the file that is currently being printed
                currentOrigin, currentFilename = _getCurrentFile()
                if (
                    currentFilename == full_path
                    and currentOrigin == storage
                    and (printer.is_printing() or printer.is_paused())
                ):
                    abort(
                        409,
                        description="Trying to slice into file that is currently being printed",
                    )

                if "profile" in data and data["profile"]:
                    profile = data["profile"]
                    del data["profile"]
                else:
                    profile = None

                if "printerProfile" in data and data["printerProfile"]:
                    printerProfile = data["printerProfile"]
                    del data["printerProfile"]
                else:
                    printerProfile = None

                if (
                    "position" in data
                    and data["position"]
                    and isinstance(data["position"], dict)
                    and "x" in data["position"]
                    and "y" in data["position"]
                ):
                    position = data["position"]
                    del data["position"]
                else:
                    position = None

                select_after_slicing = False
                if "select" in data and data["select"] in valid_boolean_trues:
                    if not printer.is_operational():
                        abort(
                            409,
                            description="Printer is not operational, cannot directly select for printing",
                        )
                    select_after_slicing = True

                print_after_slicing = False
                if "print" in data and data["print"] in valid_boolean_trues:
                    if not printer.is_operational():
                        abort(
                            409,
                            description="Printer is not operational, cannot directly start printing",
                        )
                    select_after_slicing = print_after_slicing = True

                override_keys = [
                    k for k in data if k.startswith("profile.") and data[k] is not None
                ]
                overrides = {}
                for key in override_keys:
                    overrides[key[len("profile.") :]] = data[key]

                def slicing_done(target, path, select_after_slicing, print_after_slicing):
                    if select_after_slicing or print_after_slicing:
                        job = fileManager.create_job(target, path, owner=user)
                        printer.set_job(job, print_after_select=print_after_slicing)

                try:
                    fileManager.slice(
                        slicer,
                        storage,
                        path,
                        storage,
                        full_path,
                        profile=profile,
                        printer_profile_id=printerProfile,
                        position=position,
                        overrides=overrides,
                        display=canon_name,
                        callback=slicing_done,
                        callback_args=(
                            storage,
                            full_path,
                            select_after_slicing,
                            print_after_slicing,
                        ),
                    )
                except octoprint.slicing.UnknownProfile:
                    abort(404, description="Unknown profile")

                location = url_for(
                    ".readGcodeFile",
                    target=storage,
                    filename=full_path,
                    _external=True,
                )
                result = {
                    "name": destination,
                    "path": full_path,
                    "display": canon_name,
                    "origin": storage,
                    "refs": {
                        "resource": location,
                        "download": url_for("index", _external=True)
                        + "downloads/files/"
                        + storage
                        + "/"
                        + urlquote(full_path),
                    },
                }

                r = make_response(jsonify(result), 202)
                r.headers["Location"] = location
                return r

        elif command == "analyse":
            with Permissions.FILES_UPLOAD.require(403):
                if not _verifyFileExists(storage, path):
                    abort(404)

                printer_profile = None
                if "printerProfile" in data and data["printerProfile"]:
                    printer_profile = data["printerProfile"]

                if not fileManager.analyse(
                    storage, path, printer_profile_id=printer_profile
                ):
                    abort(400, description="No analysis possible")

        elif command == "copy" or command == "move":
            with Permissions.FILES_UPLOAD.require(403):
                if not _verifyFileExists(storage, path) and not _verifyFolderExists(
                    storage, path
                ):
                    abort(404)

                path, name = fileManager.split_path(storage, path)

                destination = data["destination"]
                dst_path, dst_name = fileManager.split_path(storage, destination)
                sanitized_destination = fileManager.join_path(
                    storage, dst_path, fileManager.sanitize_name(storage, dst_name)
                )

                # Check for exception thrown by _verifyFolderExists, if outside the root directory
                try:
                    if (
                        _verifyFolderExists(storage, destination)
                        and sanitized_destination != path
                    ):
                        # destination is an existing folder and not ourselves (= display rename), we'll assume we are supposed
                        # to move filename to this folder under the same name
                        destination = fileManager.join_path(storage, destination, name)

                    if _verifyFileExists(storage, destination) or _verifyFolderExists(
                        storage, destination
                    ):
                        abort(409, description="File or folder does already exist")

                except HTTPException:
                    raise
                except Exception:
                    abort(
                        409,
                        description="Exception thrown by storage, bad folder/file name?",
                    )

                is_file = fileManager.file_exists(storage, path)
                is_folder = fileManager.folder_exists(storage, path)

                if not (is_file or is_folder):
                    abort(400, description=f"Neither file nor folder, can't {command}")

                try:
                    if command == "copy":
                        if (
                            is_file and not fileManager.capabilities(storage).copy_file
                        ) or (
                            is_folder
                            and not fileManager.capabilities(storage).copy_folder
                        ):
                            abort(
                                400, description="Storage does not support this operation"
                            )

                        # destination already there? error...
                        if _verifyFileExists(storage, destination) or _verifyFolderExists(
                            storage, destination
                        ):
                            abort(409, description="File or folder does already exist")

                        if is_file:
                            fileManager.copy_file(storage, path, destination)
                        else:
                            fileManager.copy_folder(storage, path, destination)

                    elif command == "move":
                        with Permissions.FILES_DELETE.require(403):
                            if _isBusy(storage, path):
                                abort(
                                    409,
                                    description="Trying to move a file or folder that is currently in use",
                                )

                            # destination already there AND not ourselves (= display rename)? error...
                            if (
                                _verifyFileExists(storage, destination)
                                or _verifyFolderExists(storage, destination)
                            ) and sanitized_destination != path:
                                abort(
                                    409, description="File or folder does already exist"
                                )

                            if (
                                is_file
                                and not fileManager.capabilities(storage).move_file
                            ) or (
                                is_folder
                                and not fileManager.capabilities(storage).move_folder
                            ):
                                abort(
                                    400,
                                    description="Storage does not support this operation",
                                )

                            # deselect the file if it's currently selected
                            currentOrigin, currentFilename = _getCurrentFile()
                            if (
                                currentOrigin is not None
                                and currentOrigin == storage
                                and currentFilename is not None
                                and path == currentFilename
                            ):
                                printer.set_job(None)

                            if is_file:
                                fileManager.move_file(storage, path, destination)
                            else:
                                fileManager.move_folder(storage, path, destination)

                except octoprint.filemanager.storage.StorageError as e:
                    if e.code == octoprint.filemanager.storage.StorageError.INVALID_FILE:
                        abort(
                            415,
                            description=f"Could not {command} {path} to {destination}, invalid type",
                        )
                    else:
                        abort(
                            500,
                            description=f"Could not {command} {path} to {destination}, unknown error",
                        )

                location = url_for(
                    ".readGcodeFile",
                    target=storage,
                    filename=destination,
                    _external=True,
                )
                result = {
                    "name": name,
                    "path": destination,
                    "origin": storage,
                    "refs": {"resource": location},
                }
                if is_file and fileManager.capabilities(storage).read_file:
                    result["refs"]["download"] = (
                        url_for("index", _external=True)
                        + "downloads/files/"
                        + storage
                        + "/"
                        + urlquote(destination)
                    )

                r = make_response(jsonify(result), 201)
                r.headers["Location"] = location
                return r

        elif command == "copy_storage" or command == "move_storage":
            with Permissions.FILES_UPLOAD.require(403):
                if not fileManager.file_exists(storage, path):
                    abort(400, description=f"{command} is only supported for files")

                if not _verifyFileExists(storage, path) and not _verifyFolderExists(
                    storage, path
                ):
                    abort(404)

                if not fileManager.capabilities(storage).read_file or (
                    command == "move_storage"
                    and not fileManager.capabilities(storage).remove_file
                ):
                    abort(
                        400,
                        description=f"Storage {storage} does not support this operation",
                    )

                dst_storage = data["storage"]
                if dst_storage not in fileManager.registered_storages:
                    abort(400, f"Target storage {dst_storage} is not available")

                if not fileManager.capabilities(dst_storage).write_file:
                    abort(
                        400,
                        description=f"Target storage {dst_storage} does not support this operation",
                    )

                path, name = fileManager.split_path(storage, path)

                destination = data["destination"]
                dst_path, dst_name = fileManager.split_path(dst_storage, destination)
                sanitized_destination = fileManager.join_path(
                    dst_storage,
                    dst_path,
                    fileManager.sanitize_name(dst_storage, dst_name),
                )

                # Check for exception thrown by _verifyFolderExists, if outside the root directory
                try:
                    if (
                        _verifyFolderExists(dst_storage, destination)
                        and sanitized_destination != path
                    ):
                        # destination is an existing folder and not ourselves (= display rename), we'll assume we are supposed
                        # to move filename to this folder under the same name
                        destination = fileManager.join_path(
                            dst_storage, destination, name
                        )

                    if _verifyFileExists(dst_storage, destination) or _verifyFolderExists(
                        dst_storage, destination
                    ):
                        abort(409, description="File or folder does already exist")

                except HTTPException:
                    raise
                except Exception:
                    abort(
                        409,
                        description="Exception thrown by storage, bad folder/file name?",
                    )

                upload_done = False

                def progress_callback(progress=None, done=False, failed=False):
                    nonlocal upload_done
                    upload_done = done or failed

                try:
                    if command == "copy_storage":
                        if not fileManager.capabilities(dst_storage).write_file:
                            abort(
                                400, description="Storage does not support this operation"
                            )

                        # destination already there? error...
                        if _verifyFileExists(
                            dst_storage, destination
                        ) or _verifyFolderExists(dst_storage, destination):
                            abort(409, description="File or folder does already exist")

                        fileManager.copy_file_across_storage(
                            storage,
                            path,
                            dst_storage,
                            destination,
                            progress_callback=progress_callback,
                        )

                    elif command == "move_storage":
                        with Permissions.FILES_DELETE.require(403):
                            if _isBusy(storage, path):
                                abort(
                                    409,
                                    description="Trying to move a file or folder that is currently in use",
                                )

                            # destination already there? error...
                            if _verifyFileExists(
                                dst_storage, destination
                            ) or _verifyFolderExists(dst_storage, destination):
                                abort(
                                    409, description="File or folder does already exist"
                                )

                            # deselect the file if it's currently selected
                            currentOrigin, currentFilename = _getCurrentFile()
                            if (
                                currentOrigin is not None
                                and currentOrigin == storage
                                and currentFilename is not None
                                and path == currentFilename
                            ):
                                printer.set_job(None)

                            fileManager.move_file_across_storage(
                                storage,
                                path,
                                dst_storage,
                                destination,
                                progress_callback=progress_callback,
                            )

                except octoprint.filemanager.storage.StorageError as e:
                    if e.code == octoprint.filemanager.storage.StorageError.UNSUPPORTED:
                        abort(
                            415,
                            description=f"Could not {command} {storage}:{path} to {dst_storage}:{destination}, unsupported",
                        )
                    elif (
                        e.code == octoprint.filemanager.storage.StorageError.INVALID_FILE
                    ):
                        abort(
                            415,
                            description=f"Could not {command} {storage}:{path} to {dst_storage}:{destination}, invalid type",
                        )
                    else:
                        abort(
                            500,
                            description=f"Could not {command} {storage}:{path} to {dst_storage}:{destination}, unknown error",
                        )

                location = url_for(
                    ".readGcodeFile",
                    target=dst_storage,
                    filename=destination,
                    _external=True,
                )
                result = {
                    "name": dst_name,
                    "path": dst_path,
                    "origin": dst_storage,
                    "done": upload_done,
                    "refs": {"resource": location},
                }
                if fileManager.capabilities(dst_storage).read_file:
                    result["refs"]["download"] = (
                        url_for("index", _external=True)
                        + f"downloads/files/{dst_storage}/{urlquote(destination)}"
                    )

                r = make_response(jsonify(result), 201)
                r.headers["Location"] = location
                return r
    except octoprint.filemanager.NoSuchStorage:
        abort(404)

    return NO_CONTENT


@api.route("/files/<string:target>/<path:filename>", methods=["DELETE"])
@no_firstrun_access
@Permissions.FILES_DELETE.require(403)
def deleteGcodeFile(filename, target):
    if not _validate_filename(target, filename):
        abort(404)

    if not _verifyFileExists(target, filename) and not _verifyFolderExists(
        target, filename
    ):
        abort(404)

    if target not in fileManager.registered_storages:
        abort(404)

    if _verifyFileExists(target, filename):
        if not fileManager.capabilities(target).remove_file:
            abort(400, description=f"Files on {target} cannot be deleted")

        if _isBusy(target, filename):
            abort(409, description="Trying to delete a file that is currently in use")

        # deselect the file if it's currently selected
        currentOrigin, currentPath = _getCurrentFile()
        if (
            currentPath is not None
            and currentOrigin == target
            and filename == currentPath
        ):
            printer.set_job(None)

        # delete it
        try:
            fileManager.remove_file(target, filename)
        except (OSError, StorageError) as e:
            _abortWithException(e)

    elif _verifyFolderExists(target, filename):
        if not fileManager.capabilities(target).remove_folder:
            abort(400, description=f"Folders on {target} cannot be deleted")

        if _isBusy(target, filename):
            abort(
                409,
                description="Trying to delete a folder that contains a file that is currently in use",
            )

        # deselect the file if it's currently selected
        currentOrigin, currentPath = _getCurrentFile()
        if (
            currentPath is not None
            and currentOrigin == target
            and fileManager.file_in_path(target, filename, currentPath)
        ):
            printer.set_job(None)

        # delete it
        try:
            fileManager.remove_folder(target, filename, recursive=True)
        except (OSError, StorageError) as e:
            _abortWithException(e)

    return NO_CONTENT


def _abortWithException(error):
    if type(error) is StorageError:
        _logger.error(f"{error}: {error.code}", exc_info=error.cause)
        if error.code == StorageError.INVALID_DIRECTORY:
            abort(400, description="Could not create folder, invalid directory")
        elif error.code == StorageError.INVALID_FILE:
            abort(415, description="Could not upload file, invalid type")
        elif error.code == StorageError.INVALID_SOURCE:
            abort(404, description="Source path does not exist, invalid source")
        elif error.code == StorageError.INVALID_DESTINATION:
            abort(400, description="Destination is invalid")
        elif error.code == StorageError.DOES_NOT_EXIST:
            abort(404, description="Does not exit")
        elif error.code == StorageError.ALREADY_EXISTS:
            abort(409, description="File or folder already exists")
        elif error.code == StorageError.SOURCE_EQUALS_DESTINATION:
            abort(400, description="Source and destination are the same folder")
        elif error.code == StorageError.NOT_EMPTY:
            abort(409, description="Folder is not empty")
        elif error.code == StorageError.UNSUPPORTED:
            abort(400, description="Operation is unsupported on this storage type")
        elif error.code == StorageError.UNKNOWN:
            _logger.exception(error)
            abort(500, description=str(error.cause).split(":")[0])
        else:
            _logger.exception(error)
            abort(500, description=error)
    else:
        _logger.exception(error)
        abort(500, description=str(error).split(":")[0])


def _getCurrentFile():
    currentJob = printer.get_current_job()
    if (
        currentJob is not None
        and "file" in currentJob
        and "path" in currentJob["file"]
        and "origin" in currentJob["file"]
    ):
        return currentJob["file"]["origin"], currentJob["file"]["path"]
    else:
        return None, None


def _validate_filename(target, filename):
    return fileManager.join_path(target, *fileManager.sanitize(target, filename))


def _verify_sd_upload_preconditions():
    # validate that all preconditions for SD upload are met before attempting it
    if not (
        printer.is_operational() and not (printer.is_printing() or printer.is_paused())
    ):
        abort(
            409,
            description="Can not upload to SD card, printer is either not operational or already busy",
        )
    if not printer.is_sd_ready():
        abort(409, description="Can not upload to SD card, not yet initialized")


class WerkzeugFileWrapper(octoprint.filemanager.util.AbstractFileWrapper):
    """
    A wrapper around a Werkzeug ``FileStorage`` object.

    Arguments:
        file_obj (werkzeug.datastructures.FileStorage): The Werkzeug ``FileStorage`` instance to wrap.

    .. seealso::

       `werkzeug.datastructures.FileStorage <http://werkzeug.pocoo.org/docs/0.10/datastructures/#werkzeug.datastructures.FileStorage>`_
            The documentation of Werkzeug's ``FileStorage`` class.
    """

    def __init__(self, file_obj):
        octoprint.filemanager.util.AbstractFileWrapper.__init__(self, file_obj.filename)
        self.file_obj = file_obj

    def save(self, path):
        """
        Delegates to ``werkzeug.datastructures.FileStorage.save``
        """
        self.file_obj.save(path)

    def stream(self):
        """
        Returns ``werkzeug.datastructures.FileStorage.stream``
        """
        return self.file_obj.stream
