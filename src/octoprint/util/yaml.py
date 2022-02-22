from typing import Any, Dict, Hashable, TextIO, Union


def load_from_file(
    file: TextIO = None, path: str = None
) -> Union[Dict[Hashable, Any], list, None]:
    """
    Safely and performantly loads yaml data from the given source. Either a
    path or a file must be passed in.
    """
    if path is not None:
        assert file is None
        with open(path, encoding="utf-8-sig") as f:
            return load_from_file(file=f)

    if file is not None:
        assert path is None

    assert path is not None or file is not None, "this function requires an input file"

    import yaml

    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:
        from yaml import SafeLoader

    return yaml.load(file, Loader=SafeLoader)


def _save_to_file_base(data, file=None, path=None, pretty=False, **kwargs):
    if path is not None:
        assert file is None
        with open(path, "wt", encoding="utf-8") as f:
            return _save_to_file_base(data, file=f, pretty=pretty, **kwargs)

    if file is not None:
        assert path is None

    import yaml

    try:
        from yaml import CSafeDumper as SafeDumper
    except ImportError:
        from yaml import SafeDumper

    if pretty:
        # make each element go on a new line and indent by 2
        kwargs.update(default_flow_style=False, indent=2)

    return yaml.dump(
        data,
        stream=file,
        Dumper=SafeDumper,
        allow_unicode=True,  # no good reason not to allow it these days
        **kwargs
    )


def save_to_file(data, file=None, path=None, pretty=False, **kwargs):
    """
    Safely and performantly dumps the `data` to yaml.

    To dump to a string, use `yaml.dump()`.

    :type data: object
    :param data: the data to be serialized
    :type file: typing.TextIO | None
    :type path: str | None
    :type pretty: bool
    :param pretty: formats the output yaml into a more human-friendly format
    """
    assert file is not None or path is not None, "this function requires an output file"
    _save_to_file_base(data, file=file, path=path, pretty=pretty, **kwargs)


def dump(data, pretty=False, **kwargs):
    """
    Safely and performantly dumps the `data` to a yaml string.

    :param data: the data to be serialized
    :param pretty: formats the output yaml into a more human-friendly format
    :param kwargs: any other args to be passed to the internal yaml.dump() call.
    :return: yaml-serialized data
    :rtype: str
    """
    return _save_to_file_base(data, file=None, pretty=pretty, **kwargs)
