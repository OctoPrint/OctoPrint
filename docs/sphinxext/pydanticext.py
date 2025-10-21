__author__ = "Gina Häußge <gina@octoprint.org>"
__license__ = "The MIT License <http://opensource.org/licenses/MIT>"
__copyright__ = "Copyright (C) 2025 Gina Häußge - Released under terms of the MIT License"


import inspect
import re
from enum import Enum
from typing import Optional, Type, get_type_hints

import yaml
from docutils import nodes
from docutils.parsers.rst import directives
from pydantic import BaseModel
from pydantic.fields import FieldInfo, PydanticUndefined
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective

_logger = logging.getLogger(__name__)


def _load_clz(identifier: str) -> Optional[Type]:
    import importlib

    module_name, class_name = identifier.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
        importlib.reload(module)
        clz = getattr(module, class_name)
    except Exception:
        _logger.exception(f"Could not import {class_name} from {module_name}")
        raise

    return clz


def _prefix_lines(lines: str, prefix="") -> str:
    return "\n".join(f"{prefix}{line}" for line in lines.splitlines())


class PydanticExampleExt(SphinxDirective):
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {"key": directives.unchanged, "limited": directives.flag}
    has_content = False

    def run(self) -> list[nodes.Node]:
        clz_name = self.arguments[0]
        clz = _load_clz(clz_name)

        example_yaml = self._dump_example_yaml(
            clz, key=self.options.get("key"), recursive="limited" not in self.options
        )

        output = (
            ".. code-block:: yaml\n\n"
            + _prefix_lines(example_yaml, prefix="   ")
            + "\n\n"
        )
        return self.parse_text_to_nodes(output)

    def _dump_example_yaml(self, clz, key=None, recursive=True) -> str:
        if inspect.isclass(clz) and issubclass(clz, BaseModel):
            example = clz.model_construct().model_dump(mode="json", by_alias=True)

            if recursive:
                if key:
                    example = {key: example}
                return yaml.dump(example)

            else:
                result = ""

                if key:
                    prefix = "  "
                    result += f"{key}:\n"
                else:
                    prefix = ""

                for k in example.keys():
                    result += f"{prefix}{k}:\n{prefix}  # ...\n"

                return result

        elif isinstance(clz, list):
            example = []
            for item in clz:
                if isinstance(item, BaseModel):
                    example.append(item.model_dump(mode="json", by_alias=True))
                elif isinstance(item, (dict, list, int, float, bool, str)):
                    example.append(item)

            if key:
                example = {key: example}
            return yaml.dump(example)

        else:
            raise ValueError(f"Don't know how to render {clz}")


class PydanticTableExt(SphinxDirective):
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}
    has_content = True

    COLUMN_WIDTHS = "15 5 25 15"
    CONTAINER_TYPES = ("Optional", "Literal")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scanner = self._create_scanner()

    def run(self) -> list[nodes.Node]:
        clz_name = self.arguments[0]
        clz = _load_clz(clz_name)

        subs = self._convert_subs("\n".join(self.content))

        model_doc = self._model_doc(clz, subs=subs)
        output = (
            f".. list-table::\n   :width: 100%\n   :widths: {self.COLUMN_WIDTHS}\n   :header-rows: 1\n\n   * - Name\n     - Type\n     - Description\n     - Default\n"
            + model_doc
            + "\n\n"
        )

        return self.parse_text_to_nodes(output)

    def _create_scanner(self) -> re.Scanner:
        def token_identifier(scanner, token):
            return "IDENTIFIER", token

        def token_lbracket(scanner, token):
            return "LBRACKET", token

        def token_rbracket(scanner, token):
            return "RBRACKET", token

        def token_comma(scanner, token):
            return "COMMA", token

        def token_whitespace(scanner, token):
            return "WHITESPACE", token

        return re.Scanner(
            [
                (r"[a-zA-Z_][a-zA-Z0-9_\.]*", token_identifier),
                (r"\[", token_lbracket),
                (r"\]", token_rbracket),
                (r",", token_comma),
                (r"\s+", token_whitespace),
            ]
        )

    def _convert_subs(self, subs: str) -> dict[str, str]:
        if not subs:
            return {}

        result = {}
        for line in subs.splitlines():
            if not line or "=" not in line:
                continue
            key, value = line.split("=", maxsplit=1)
            result[key.strip()] = value.strip()

        return result

    def _convert_name(self, name: str, subs: dict[str, str] = None) -> str:
        if subs is None:
            subs = {}

        if name.startswith("typing."):
            name = name[len("typing.") :]
        elif name.startswith("typing_extensions."):
            name = name[len("typing_extensions.") :]

        return subs.get(name, name)

    def _convert_enum(self, enum_: Type) -> Type:
        enum_ = self._strip_container_types(enum_)
        bases = [base for base in enum_.__bases__ if not issubclass(base, Enum)]
        if bases:
            return bases[0]
        return enum_

    def _strip_container_types(self, type_: Type) -> Type:
        while any(str(type_).startswith(f"typing.{x}") for x in self.CONTAINER_TYPES):
            args = type_.__args__
            if args:
                type_ = args[0]
            else:
                break

        return type_

    def _type_name(self, type_: Type, subs: dict[str, str] = None) -> str:
        if inspect.isclass(type_) and hasattr(type_, "__name__"):
            name = type_.__name__
        else:
            name = str(type_)

        tokens = self.scanner.scan(name)[0]
        processed = []
        for token in tokens:
            if token[0] == "IDENTIFIER":
                processed.append(("IDENTIFIER", self._convert_name(token[1], subs=subs)))
            else:
                processed.append(token)

        return "".join(token[1] for token in processed)

    def _type_doc(self, type_: Type, subs: dict[str, str] = None) -> str:
        type_ = self._strip_container_types(type_)

        if inspect.isclass(type_) and issubclass(type_, Enum):
            type_ = self._convert_enum(type_)

        name = self._type_name(type_, subs=subs)

        return f"``{name}``"

    def _field_doc(
        self, name: str, field: FieldInfo, t: Type, subs: dict[str, str] = None
    ) -> str:
        type_ = self._type_doc(t, subs=subs)

        default = getattr(field, "default", None)
        if default == PydanticUndefined:
            default = "*required*"
        elif default is None:
            default = "*unset*"
        elif isinstance(default, Enum) and self._convert_enum(t) is not t:
            default = f"``{default.value!r}``"
        else:
            default = f"``{default!r}``"

        description = getattr(field, "description", None)
        if not description:
            description = ""

        if inspect.isclass(t) and issubclass(t, Enum):
            if self._convert_enum(t) is not t:
                choices = [
                    f"`{getattr(t, e).value}`"
                    for e in dir(t)
                    if not e.startswith("_") and hasattr(getattr(t, e), "value")
                ]
            else:
                choices = [
                    f"`{getattr(t, e)}`"
                    for e in dir(t)
                    if not e.startswith("_") and hasattr(getattr(t, e), "value")
                ]

            description += (
                " " if description else ""
            ) + f"Valid values: {', '.join(choices)}."
        elif str(t).startswith("typing.Literal") or str(t).startswith(
            "typing_extensions.Literal"
        ):
            choices = [f"`{c!r}`" for c in t.__args__]
            description += (
                " " if description else ""
            ) + f"Valid values: {', '.join(choices)}."

        description = _prefix_lines(description, prefix="       ").strip()

        return (
            f"   * - ``{name}``\n     - {type_}\n     - {description}\n     - {default}\n"
        )

    def _model_doc(
        self, model: BaseModel, prefix: str = "", subs: dict[str, str] = None
    ) -> str:
        result = ""

        type_hints = get_type_hints(model)

        for name, field in model.__pydantic_fields__.items():
            if hasattr(field, "alias"):
                alias = field.alias
                if alias:
                    name = alias

            if inspect.isclass(field.annotation) and issubclass(
                field.annotation, BaseModel
            ):
                description = field.description
                if not description:
                    description = ""

                description = _prefix_lines(description, prefix="       ").strip()

                type_hint = type_hints.get(name)
                if inspect.isclass(type_hint) and issubclass(type_hint, BaseModel):
                    result += f"   * - ``{prefix}{name}.*``\n"
                    result += "     - \n"
                    result += f"     - {description}\n"
                    result += "     - \n"

                    result += self._model_doc(field.annotation, prefix=f"{prefix}{name}.")

                elif str(type_hint).startswith("typing.List"):
                    result += f"   * - ``{prefix}{name}[]``\n"
                    result += "     - \n"
                    result += f"     - {description}\n"
                    result += "     - \n"

                    result += self._model_doc(
                        field.annotation, prefix=f"{prefix}{name}[]."
                    )

            else:
                result += self._field_doc(
                    prefix + name, field, type_hints.get(name), subs=subs
                )

        return result


def setup(app):
    app.add_directive("pydantic-example", PydanticExampleExt)
    app.add_directive("pydantic-table", PydanticTableExt)

    return {"version": "0.1"}
