"""Basic function like running processes and logging."""

import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path
from subprocess import PIPE, CalledProcessError  # noqa: F401
from tempfile import NamedTemporaryFile
from typing import Optional, Sequence

from colorama import Fore, init

_DEFAULT_KEYSERVER: str = "hkps://keys.openpgp.org"
_PYTEST_KEYSERVER: Optional[str] = None

_DEBUG = False
_PYTEST_DEBUG = False

RESULT_LOG = """
Command call
  cmd:         {cmd} {color_begin}-> {returncode}{color_end}
""".strip()
OUTPUT_LOG = "  {out_type}:{white_space}'{output}'"
_indent = " " * 15

_isatty_cache: bool | None = None


lg = logging.getLogger(__name__)


class PyaptlyCliError(Exception):
    pass


def exit_with_error(error):
    lg.error(error)
    raise PyaptlyCliError()


def write_traceback():  # pragma: no cover
    with NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write(traceback.format_exc())
        tmp.close()
    return tmp.name


def isatty():
    global _isatty_cache
    if _isatty_cache is None:
        _isatty_cache = os.isatty(1)
        if _isatty_cache:
            init()  # pragma: no cover
    return _isatty_cache


def unit_or_list_to_list(thingy):
    """Ensure that a toml entry is always a list.

    Used to allow lists and single units in the toml file.

    :param thingy: The data to ensure it is a list
    :type  thingy: list, tuple or other
    """
    if isinstance(thingy, list) or isinstance(thingy, tuple):
        return list(thingy)
    else:
        return [thingy]


def get_default_keyserver():
    """Get default keyseerver."""
    if _PYTEST_KEYSERVER:
        return _PYTEST_KEYSERVER
    else:
        return _DEFAULT_KEYSERVER


def run_command(
    cmd_args: Sequence[str | Path],
    *,
    decode: bool = True,
    hide_error: bool = False,
    **kwargs,
):
    """Instrumented subprocess.run for easier debugging.

    - By default this run command will add `encoding="UTF-8"` to kwargs. Disable
      with `decode=False`.
    - Command that often or normally fail can also set `hide_error=True` to only
      show them in if the loglevel is `INFO` (Logging and output in DEVELOPMENT.md)
    """
    added_stdout = False
    added_stderr = False
    if "stdout" not in kwargs:
        kwargs["stdout"] = PIPE
        added_stdout = True
    else:
        assert kwargs["stdout"] in (PIPE, None)
    if "stderr" not in kwargs:
        kwargs["stderr"] = PIPE
        added_stderr = True
    else:
        assert kwargs["stdout"] in (PIPE, None)  # pragma: no cover
    # If we want to log stdout/err before raising CalledProcessError we have to
    # check ourselves
    check = False
    if "check" in kwargs:
        check = kwargs["check"]
        del kwargs["check"]
    result = None
    tb = ""
    if decode and "encoding" not in kwargs:
        kwargs["encoding"] = "UTF-8"
    try:
        result = subprocess.run(cmd_args, **kwargs)
        if check and result.returncode:
            raise CalledProcessError(
                result.returncode,
                result.args,
                output=result.stdout,
                stderr=result.stderr,
            )
    except Exception:
        if "pytest" not in sys.modules:
            tb = write_traceback()  # pragma: no cover
        raise
    finally:
        if result and lg.getEffectiveLevel() <= logging.DEBUG:
            log_msg = format_run_result(result, result.returncode, tb)
            if result.returncode == 0:
                lg.info(log_msg)
            else:
                if not hide_error or lg.getEffectiveLevel() <= logging.INFO:
                    lg.error(log_msg)
            # This function should not alter the returned result
            if added_stdout:
                delattr(result, "stdout")
            if added_stderr:
                delattr(result, "stderr")
    return result


def indent_out(output: bytes | str) -> str:
    """Indent command output for nicer logging-messages.

    It will convert bytes to strings if need or display the result as bytes if
    decoding fails.
    """
    output = output.strip()
    if not output:
        return ""  # pragma: no cover
    indented = False
    if hasattr(output, "decode"):
        try:
            output = output.decode(encoding="UTF-8")
            lines = output.splitlines()
            result = [lines[0]]
            for line in lines[1:]:
                result.append(f"{_indent}{line}")
            indented = True
        except UnicodeDecodeError:
            pass

    if not indented:
        lines = output.splitlines()
        result = [str(lines[0])]
        for line in lines[1:]:
            result.append(f"{_indent}{str(line)}")
    return "\n".join(result)


def format_run_result(result: subprocess.CompletedProcess, returncode: int, tb: str):
    """Format a CompletedProcess result log."""
    color_begin = ""
    color_end = ""
    if isatty():  # pragma: no cover
        if returncode == 0:
            color_begin = Fore.RED
            color_end = Fore.YELLOW
        else:
            color_begin = Fore.YELLOW
            color_end = Fore.RED
    msg = [
        RESULT_LOG.format(
            cmd=" ".join([str(x) for x in result.args]),
            returncode=result.returncode,
            color_begin=color_begin,
            color_end=color_end,
        )
    ]
    for out_type, output in [
        ("stdout", result.stdout),
        ("stderr", result.stderr),
        ("traceback", tb),
    ]:
        output = output.strip()
        if output:
            output = indent_out(output)
            white_space = " " * (11 - len(out_type))
            msg.append(
                OUTPUT_LOG.format(
                    out_type=out_type, white_space=white_space, output=output
                )
            )
        pass
    return "\n".join(msg)


def parse_aptly_show_command(show: str) -> dict[str, str]:
    """Parse an aptly show command."""
    result = {}
    for line in show.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.lower()
            result[key] = value.strip()
    return result
