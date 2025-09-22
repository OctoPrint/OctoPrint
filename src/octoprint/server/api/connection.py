__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Optional

from flask import abort, jsonify, request

from octoprint.access.permissions import Permissions
from octoprint.printer.connection import ConnectedPrinter
from octoprint.schema import BaseModel
from octoprint.server import NO_CONTENT, printer, printerProfileManager
from octoprint.server.api import api
from octoprint.server.util.flask import (
    api_version_matches,
    api_versioned,
    get_json_command_from_request,
    no_firstrun_access,
)
from octoprint.settings import settings, valid_boolean_trues

## Schema


class CurrentConnectionState(BaseModel):
    state: str
    connector: Optional[str]
    parameters: Optional[dict]
    capabilities: Optional[dict]
    profile: Optional[str]


class AvailablePrinterProfile(BaseModel):
    id: str
    name: str


class AvailableConnector(BaseModel):
    connector: str
    name: str
    parameters: dict


class PreferredConnectorSettings(BaseModel):
    connector: str
    parameters: dict


class ConnectionOptions(BaseModel):
    connectors: list[AvailableConnector]
    profiles: list[AvailablePrinterProfile]

    preferredConnector: Optional[PreferredConnectorSettings]
    preferredProfile: Optional[str]


class ConnectionStateResponse(BaseModel):
    current: CurrentConnectionState
    options: ConnectionOptions


# pre 1.12.0


class CurrentConnectionState_pre_1_12_0(BaseModel):
    state: str
    printerProfile: Optional[str]
    port: Optional[str]
    baudrate: Optional[int]


class ConnectionOptions_pre_1_12_0(BaseModel):
    ports: list[str]
    baudrates: list[int]
    printerProfiles: list[AvailablePrinterProfile]

    portPreference: Optional[str]
    baudratePreference: Optional[int]
    printerProfilePreference: Optional[str]


class ConnectionStateResponse_pre_1_12_0(BaseModel):
    current: CurrentConnectionState_pre_1_12_0
    options: ConnectionOptions_pre_1_12_0


## API


@api.route("/connection", methods=["GET"])
@api_versioned
@Permissions.STATUS.require(403)
def connectionState():
    connection_state = printer.connection_state

    connector = connection_state.pop("connector", None)
    profile = connection_state.pop("profile", None)
    capabilities = connection_state.pop("printer_capabilities", None)
    state = connection_state.pop("state", "Unknown")

    data = ConnectionStateResponse(
        current=CurrentConnectionState(
            state=state,
            connector=connector,
            parameters=connection_state,
            capabilities=capabilities,
            profile=profile.get("_id") if profile else None,
        ),
        options=_get_options(),
    )

    return jsonify(data.model_dump())


@connectionState.version("<1.12.0")
@Permissions.STATUS.require(403)
def connectionState_pre_1_12_0():
    connection_state = printer.connection_state

    state = connection_state.pop("state")
    profile = connection_state.pop("profile", None)

    data = ConnectionStateResponse_pre_1_12_0(
        current=CurrentConnectionState_pre_1_12_0(
            state=state,
            printerProfile=profile.get("id", None) if profile else None,
            port=connection_state.get("port", ""),
            baudrate=connection_state.get("baudrate", 0),
        ),
        options=_get_options_pre_1_12_0(),
    )

    return jsonify(data.model_dump())


@api.route("/connection", methods=["POST"])
@no_firstrun_access
@Permissions.CONNECTION.require(403)
def connectionCommand():
    valid_commands = {"connect": [], "disconnect": [], "repair": [], "fake_ack": []}

    command, data, response = get_json_command_from_request(request, valid_commands)
    if response is not None:
        return response

    if command == "connect":
        parameters = {}
        printerProfile = None

        if api_version_matches(">=1.12.0"):
            if "connector" not in data:
                abort(400, description='required parameter "connector" is missing')

            connector_name = data["connector"]
            connector = ConnectedPrinter.find(connector_name)
            if not connector:
                abort(400, description=f'unknown connector: "{connector_name}"')

            if "parameters" in data:
                parameters = data["parameters"]
                if not isinstance(parameters, dict):
                    abort(400, description='"parameters" must be a dictionary')

        else:  # pre 1.12.0
            connector_name = "serial"
            connector = ConnectedPrinter.find(connector_name)
            if connector is None:
                abort(400, description=f'unknown connector: "{connector_name}"')

            connection_options = connector.connection_options()

            if "port" in data:
                port = data["port"]
                if port not in connection_options["port"] and port != "AUTO":
                    abort(400, description="port is invalid")
                parameters["port"] = port

            if "baudrate" in data:
                baudrate = data["baudrate"]
                if baudrate not in connection_options["baudrate"] and baudrate != 0:
                    abort(400, description="baudrate is invalid")
                parameters["baudrate"] = baudrate

        if "printerProfile" in data:
            printerProfile = data["printerProfile"]
            if not printerProfileManager.exists(printerProfile):
                abort(400, description="printerProfile is invalid")

        # check if our connection preconditions are met
        if not connector.connection_preconditions_met(parameters):
            abort(
                412,
                description=f"Preconditions for connecting to {connector_name} weren't met by provided parameters",
            )

        # check if we also need to update the settings
        settings_dirty = False

        if "save" in data and data["save"] in valid_boolean_trues:
            settings().set(
                ["printerConnection", "preferred", "connector"], connector_name
            )
            settings().set(["printerConnection", "preferred", "parameters"], parameters)
            printerProfileManager.set_default(printerProfile)
            settings_dirty = True

        if "autoconnect" in data:
            settings().setBoolean(
                ["printerConnection", "autoconnect"], data["autoconnect"]
            )
            settings_dirty = True

        if settings_dirty:
            settings().save()

        # connect
        printer.connect(
            connector=connector_name, parameters=parameters, profile=printerProfile
        )

    elif command == "disconnect":
        printer.disconnect()

    elif command == "repair" or command == "fake_ack":
        printer.repair_communication()

    return NO_CONTENT


def _get_options() -> ConnectionOptions:
    connector_options = ConnectedPrinter.all()
    profile_options = printerProfileManager.get_all()
    default_profile = printerProfileManager.get_default()

    preferred_connection_connector = settings().get(
        ["printerConnection", "preferred", "connector"]
    )
    preferred_connection_params = settings().get(
        ["printerConnection", "preferred", "parameters"]
    )

    return ConnectionOptions(
        connectors=[
            AvailableConnector(
                connector=connector.connector,
                name=connector.name,
                parameters=connector.connection_options(),
            )
            for connector in connector_options
        ],
        profiles=[
            AvailablePrinterProfile(
                id=printer_profile["id"],
                name=printer_profile.get("name", printer_profile["id"]),
            )
            for printer_profile in profile_options.values()
            if "id" in printer_profile
        ],
        preferredConnector=PreferredConnectorSettings(
            connector=preferred_connection_connector,
            parameters=preferred_connection_params,
        ),
        preferredProfile=default_profile["id"] if "id" in default_profile else None,
    )


def _get_options_pre_1_12_0() -> ConnectionOptions_pre_1_12_0:
    profile_options = printerProfileManager.get_all()
    default_profile = printerProfileManager.get_default()

    # we only support the serial connector here
    serial_connector = ConnectedPrinter.find("serial")
    if serial_connector:
        connection_options = serial_connector.connection_options()
    else:
        connection_options = {}

    # preferred
    preferred_connection_connector = settings().get(
        ["printerConnection", "preferred", "connector"]
    )
    preferred_connection_params = {}
    if preferred_connection_connector == "serial":
        preferred_connection_params = settings().get(
            ["printerConnection", "preferred", "parameters"]
        )

    return ConnectionOptions_pre_1_12_0(
        ports=connection_options.get("port", []),
        baudrates=connection_options.get("baudrate", []),
        printerProfiles=[
            AvailablePrinterProfile(
                id=printer_profile["id"],
                name=printer_profile.get("name", printer_profile["id"]),
            )
            for printer_profile in profile_options.values()
            if "id" in printer_profile
        ],
        portPreference=preferred_connection_params.get("port"),
        baudratePreference=preferred_connection_params.get("baudrate"),
        printerProfilePreference=default_profile["id"]
        if "id" in default_profile
        else None,
    )
