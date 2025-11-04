__author__ = "Gina Häußge <osd@foosel.net>, Lars Norpchen"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import collections
import datetime
import logging
import queue
import re
import shlex
import subprocess
import threading

import octoprint.plugin
from octoprint.settings import settings

# singleton
_instance = None


def all_events():
    return [
        getattr(Events, name)
        for name in Events.__dict__
        if not name.startswith("_") and name not in ("register_event",)
    ]


class Events:
    # server
    STARTUP = "Startup"
    SHUTDOWN = "Shutdown"
    CONNECTIVITY_CHANGED = "ConnectivityChanged"

    # connect/disconnect to printer
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    DISCONNECTING = "Disconnecting"
    DISCONNECTED = "Disconnected"
    CONNECTIONS_AUTOREFRESHED = "ConnectionsAutorefreshed"

    # State changes
    PRINTER_STATE_CHANGED = "PrinterStateChanged"
    PRINTER_RESET = "PrinterReset"
    PRINTER_CONTROLS_CHANGED = "PrinterControlsChanged"

    # connect/disconnect by client
    CLIENT_OPENED = "ClientOpened"
    CLIENT_CLOSED = "ClientClosed"
    CLIENT_AUTHED = "ClientAuthed"
    CLIENT_DEAUTHED = "ClientDeauthed"

    # user login/logout
    USER_LOGGED_IN = "UserLoggedIn"
    USER_LOGGED_OUT = "UserLoggedOut"

    # File management
    UPLOAD = "Upload"
    FILE_SELECTED = "FileSelected"
    FILE_DESELECTED = "FileDeselected"
    UPDATED_FILES = "UpdatedFiles"
    METADATA_ANALYSIS_STARTED = "MetadataAnalysisStarted"
    METADATA_ANALYSIS_FINISHED = "MetadataAnalysisFinished"
    METADATA_STATISTICS_UPDATED = "MetadataStatisticsUpdated"

    FILE_ADDED = "FileAdded"
    FILE_REMOVED = "FileRemoved"
    FILE_MOVED = "FileMoved"
    FOLDER_ADDED = "FolderAdded"
    FOLDER_REMOVED = "FolderRemoved"
    FOLDER_MOVED = "FolderMoved"

    # SD Upload
    TRANSFER_STARTED = "TransferStarted"
    TRANSFER_DONE = "TransferDone"
    TRANSFER_FAILED = "TransferFailed"

    # print job
    PRINT_STARTED = "PrintStarted"
    PRINT_DONE = "PrintDone"
    PRINT_FAILED = "PrintFailed"
    PRINT_CANCELLING = "PrintCancelling"
    PRINT_CANCELLED = "PrintCancelled"
    PRINT_PAUSED = "PrintPaused"
    PRINT_RESUMED = "PrintResumed"
    ERROR = "Error"
    CHART_MARKED = "ChartMarked"

    # print/gcode events
    POWER_ON = "PowerOn"
    POWER_OFF = "PowerOff"
    HOME = "Home"
    Z_CHANGE = "ZChange"
    WAITING = "Waiting"
    DWELL = "Dwelling"
    COOLING = "Cooling"
    ALERT = "Alert"
    CONVEYOR = "Conveyor"
    EJECT = "Eject"
    E_STOP = "EStop"
    POSITION_UPDATE = "PositionUpdate"
    FIRMWARE_DATA = "FirmwareData"
    TOOL_CHANGE = "ToolChange"
    REGISTERED_MESSAGE_RECEIVED = "RegisteredMessageReceived"
    COMMAND_SUPPRESSED = "CommandSuppressed"
    INVALID_TOOL_REPORTED = "InvalidToolReported"
    FILAMENT_CHANGE = "FilamentChange"

    # Timelapse
    CAPTURE_START = "CaptureStart"
    CAPTURE_DONE = "CaptureDone"
    CAPTURE_FAILED = "CaptureFailed"
    POSTROLL_START = "PostRollStart"
    POSTROLL_END = "PostRollEnd"
    MOVIE_RENDERING = "MovieRendering"
    MOVIE_DONE = "MovieDone"
    MOVIE_FAILED = "MovieFailed"

    # Slicing
    SLICING_STARTED = "SlicingStarted"
    SLICING_DONE = "SlicingDone"
    SLICING_FAILED = "SlicingFailed"
    SLICING_CANCELLED = "SlicingCancelled"
    SLICING_PROFILE_ADDED = "SlicingProfileAdded"
    SLICING_PROFILE_MODIFIED = "SlicingProfileModified"
    SLICING_PROFILE_DELETED = "SlicingProfileDeleted"

    # Printer Profiles
    PRINTER_PROFILE_ADDED = "PrinterProfileAdded"
    PRINTER_PROFILE_MODIFIED = "PrinterProfileModified"
    PRINTER_PROFILE_DELETED = "PrinterProfileDeleted"

    # Settings
    SETTINGS_UPDATED = "SettingsUpdated"

    @classmethod
    def register_event(cls, event, prefix=None):
        name = cls._to_identifier(event)
        if prefix:
            event = prefix + event
            name = cls._to_identifier(prefix) + name
        setattr(cls, name, event)
        return name, event

    # based on https://stackoverflow.com/a/1176023
    _first_cap_re = re.compile("([^_])([A-Z][a-z]+)")
    _all_cap_re = re.compile("([a-z0-9])([A-Z])")

    @classmethod
    def _to_identifier(cls, name):
        s1 = cls._first_cap_re.sub(r"\1_\2", name)
        return cls._all_cap_re.sub(r"\1_\2", s1).upper()


def eventManager():
    global _instance
    if _instance is None:
        _instance = EventManager()
    return _instance


class EventManager:
    """
    Handles receiving events and dispatching them to subscribers
    """

    def __init__(self):
        self._registeredListeners = collections.defaultdict(list)
        self._logger = logging.getLogger(__name__)
        self._logger_fire = logging.getLogger(f"{__name__}.fire")

        self._startup_signaled = False
        self._shutdown_signaled = False

        self._queue = queue.Queue()
        self._held_back = queue.Queue()

        self._worker = threading.Thread(target=self._work)
        self._worker.daemon = True
        self._worker.start()

    def _work(self):
        try:
            while not self._shutdown_signaled:
                event, payload = self._queue.get(True)
                if event == Events.SHUTDOWN:
                    # we've got the shutdown event here, stop event loop processing after this has been processed
                    self._logger.info(
                        "Processing shutdown event, this will be our last event"
                    )
                    self._shutdown_signaled = True

                eventListeners = self._registeredListeners[event]
                self._logger_fire.debug(f"Firing event: {event} (Payload: {payload!r})")

                for listener in eventListeners:
                    self._logger.debug(f"Sending action to {listener!r}")
                    try:
                        listener(event, payload)
                    except Exception:
                        self._logger.exception(
                            "Got an exception while sending event {} (Payload: {!r}) to {}".format(
                                event, payload, listener
                            )
                        )

                octoprint.plugin.call_plugin(
                    octoprint.plugin.types.EventHandlerPlugin,
                    "on_event",
                    args=(event, payload),
                )
            self._logger.info("Event loop shut down")
        except Exception:
            self._logger.exception("Ooops, the event bus worker loop crashed")

    def fire(self, event, payload=None):
        """
        Fire an event to anyone subscribed to it

        Any object can generate an event and any object can subscribe to the event's name as a string (arbitrary, but
        case sensitive) and any extra payload data that may pertain to the event.

        Callbacks must implement the signature "callback(event, payload)", with "event" being the event's name and
        payload being a payload object specific to the event.
        """

        send_held_back = False
        if event == Events.STARTUP:
            self._logger.info("Processing startup event, this is our first event")
            self._startup_signaled = True
            send_held_back = True

        self._enqueue(event, payload)

        if send_held_back:
            self._logger.info(
                "Adding {} events to queue that "
                "were held back before startup event".format(self._held_back.qsize())
            )
            while True:
                try:
                    self._queue.put(self._held_back.get(block=False))
                except queue.Empty:
                    break

    def _enqueue(self, event, payload):
        if self._startup_signaled:
            q = self._queue
        else:
            q = self._held_back

        q.put((event, payload))

    def subscribe(self, event, callback):
        """
        Subscribe a listener to an event -- pass in the event name (as a string) and the callback object
        """

        if callback in self._registeredListeners[event]:
            # callback is already subscribed to the event
            return

        self._registeredListeners[event].append(callback)
        self._logger.debug(f"Subscribed listener {callback!r} for event {event}")

    def unsubscribe(self, event, callback):
        """
        Unsubscribe a listener from an event -- pass in the event name (as string) and the callback object
        """

        try:
            self._registeredListeners[event].remove(callback)
        except ValueError:
            # not registered
            pass

    def join(self, timeout=None):
        self._worker.join(timeout)
        return self._worker.is_alive()


class GenericEventListener:
    """
    The GenericEventListener can be subclassed to easily create custom event listeners.
    """

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def subscribe(self, events):
        """
        Subscribes the eventCallback method for all events in the given list.
        """

        for event in events:
            eventManager().subscribe(event, self.eventCallback)

    def unsubscribe(self, events):
        """
        Unsubscribes the eventCallback method for all events in the given list
        """

        for event in events:
            eventManager().unsubscribe(event, self.eventCallback)

    def eventCallback(self, event, payload):
        """
        Actual event callback called with name of event and optional payload. Not implemented here, override in
        child classes.
        """
        pass


class DebugEventListener(GenericEventListener):
    def __init__(self):
        GenericEventListener.__init__(self)

        events = list(filter(lambda x: not x.startswith("__"), dir(Events)))
        self.subscribe(events)

    def eventCallback(self, event, payload):
        GenericEventListener.eventCallback(self, event, payload)
        self._logger.debug(f"Received event: {event} (Payload: {payload!r})")


class CommandTrigger(GenericEventListener):
    def __init__(self, printer):
        GenericEventListener.__init__(self)
        self._printer = printer
        self._subscriptions = collections.defaultdict(list)

        self._init_subscriptions()

    def _init_subscriptions(self):
        """
        Subscribes all events as defined in "events > $triggerType > subscriptions" in the settings with their
        respective commands.
        """
        if not settings().get(["events"]):
            return

        if not settings().getBoolean(["events", "enabled"]):
            return

        eventsToSubscribe = []
        subscriptions = settings().get(["events", "subscriptions"])
        for subscription in subscriptions:
            if not isinstance(subscription, dict):
                self._logger.info(
                    "Invalid subscription definition, not a dictionary: {!r}".format(
                        subscription
                    )
                )
                continue

            events = subscription.pop("event", None)
            commands = subscription.pop("command", None)
            command_type = subscription.pop("type", None)

            if (
                events is None
                or commands is None
                or command_type is None
                or command_type not in ("system", "gcode")
            ):
                self._logger.info(
                    "Invalid command trigger, missing either event, type or command or type is invalid: {!r}".format(
                        subscription
                    )
                )
                continue

            enabled = subscription.pop("enabled", True)
            if not enabled:
                self._logger.info(f"Disabled command trigger: {subscription!r}")
                continue

            if not isinstance(commands, (list, tuple)):
                commands = [commands]

            if command_type == "gcode":
                clz = GcodeEventSubscription
            elif command_type == "system":
                clz = SystemEventSubscription
            else:
                # shouldn't happen
                self._logger.warning(f"Unknown command type: {command_type}")
                continue

            sub = clz(self._printer, *commands, **subscription)

            # "event" in the configuration can be a string, or
            # a list of strings.  If it's the former, convert it
            # into the latter.
            if not isinstance(events, (tuple, list)):
                events = [events]

            for event in events:
                self._subscriptions[event].append(sub)

                if event not in eventsToSubscribe:
                    eventsToSubscribe.append(event)

        self.subscribe(eventsToSubscribe)

    def eventCallback(self, event, payload):
        """
        Event callback, iterates over all subscribed commands for the given event, processes the command
        string and then executes the command via the abstract executeCommand method.
        """

        GenericEventListener.eventCallback(self, event, payload)

        if event not in self._subscriptions:
            return

        for sub in self._subscriptions[event]:
            try:
                sub.handle(event, payload)
            except KeyError:
                self._logger.warning(
                    f"There was an error processing one or more placeholders in the following subscription: {sub}"
                )


class EventSubscription:
    def __init__(self, printer, *commands, debug: bool = False, **kwargs):
        self.printer = printer
        self.commands = commands
        self.debug = debug

        self._logger = logging.getLogger(__name__)

    def handle(self, event: str, payload: dict):
        params = self._generated_params(event, payload)
        prepared = self._prepare_commands(params)
        self._execute(event, prepared)

    def _prepare_commands(self, params: dict):
        escaped = self._escape_params(params)
        return [command.format(**escaped) for command in self.commands]

    def _escape_params(self, params: dict) -> dict:
        return params

    def _execute(self, event: str, commands: str):
        pass

    def _generated_params(self, event: str, payload: dict) -> dict:
        """
        Generates the params for the placeholders in the set commands.

        The following substitutions are currently supported:

          - {__currentZ} : current Z position of the print head, or -1 if not available
          - {__eventname} : the name of the event hook being triggered
          - {__filename} : name of currently selected file, or "NO FILE" if no file is selected
          - {__filepath} : path in origin location of currently selected file, or "NO FILE" if no file is selected
          - {__fileorigin} : origin of currently selected file, or "NO FILE" if no file is selected
          - {__progress} : current print progress in percent, 0 if no print is in progress
          - {__data} : the string representation of the event's payload
          - {__json} : the json representation of the event's payload, "{}" if there is no payload, "" if there was an error on serialization
          - {__now} : ISO 8601 representation of the current date and time

        Additionally, the keys of the event's payload can also be used as placeholder.
        """
        json_string = "{}"
        if payload:
            import json

            try:
                json_string = json.dumps(payload)
            except Exception:
                self._logger.exception(f"JSON: Cannot dump {payload!r}", payload)
                json_string = ""

        params = {
            "__currentZ": "-1",
            "__eventname": event,
            "__filename": "NO FILE",
            "__filepath": "NO PATH",
            "__progress": "0",
            "__data": str(payload),
            "__json": json_string,
            "__now": datetime.datetime.now().isoformat(),
        }

        current_data = self.printer.get_current_data()

        if "currentZ" in current_data and current_data["currentZ"] is not None:
            params["__currentZ"] = str(current_data["currentZ"])

        if (
            "job" in current_data
            and "file" in current_data["job"]
            and "name" in current_data["job"]["file"]
            and current_data["job"]["file"]["name"] is not None
        ):
            params["__filename"] = current_data["job"]["file"]["name"]
            params["__filepath"] = current_data["job"]["file"]["path"]
            params["__fileorigin"] = current_data["job"]["file"]["origin"]
            if (
                "progress" in current_data
                and current_data["progress"] is not None
                and "completion" in current_data["progress"]
                and current_data["progress"]["completion"] is not None
            ):
                params["__progress"] = str(round(current_data["progress"]["completion"]))

        # now add the payload keys as well
        if isinstance(payload, dict):
            params.update(payload)

        return {k: str(v) for k, v in params.items()}


class GcodeEventSubscription(EventSubscription):
    def _execute(self, event, commands):
        if self.debug:
            self._logger.info(
                f"Received event {event}, executing GCode commands: {commands}"
            )
        self.printer.commands(commands)


class SystemEventSubscription(EventSubscription):
    def __init__(self, printer, *commands: str, **kwargs):
        super().__init__(printer, *commands, **kwargs)

        if "shell" not in kwargs:
            self._logger.warning(
                "Deprecation warning: You have a system command event subscription that doesn't define the 'shell' argument. For now this will continue to mean that 'shell' will be set to 'True' on the resulting command call. As that is a potential security issue, OctoPrint 1.13.0 will change this behaviour and default to 'shell=False'. If you don't want this, you have to add 'shell: true' to your event subscription."
            )
        self.shell = kwargs.get("shell", True)
        self.cwd = kwargs.get("cwd", None)

    def _escape_params(self, params):
        if self.shell:
            return {key: shlex.quote(str(value)) for key, value in params.items()}
        return params

    def _execute(self, event, commands):
        def process():
            try:
                for cmd in commands:
                    if self.debug:
                        self._logger.info(
                            f"Received event {event}, executing system command: {cmd}"
                        )
                    else:
                        self._logger.info(
                            f"Received event {event}, executing a system command"
                        )
                    subprocess.check_call(cmd, shell=self.shell, cwd=self.cwd)
            except subprocess.CalledProcessError as e:
                if self.debug:
                    self._logger.warning(
                        "Command failed with return code {}: {}".format(
                            e.returncode, str(e)
                        )
                    )
                else:
                    self._logger.warning(
                        "Command failed with return code {}, enable debug logging on target 'octoprint.events' for details".format(
                            e.returncode
                        )
                    )
            except Exception:
                self._logger.exception("Command failed")

        t = threading.Thread(target=process)
        t.daemon = True
        t.start()
