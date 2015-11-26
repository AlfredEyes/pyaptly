"""Tools for testing pyaptly"""

import contextlib
import os
import shutil
import subprocess
import tempfile

import yaml

import pyaptly


def read_yml(file_):
    """Read and merge a yml file.

    :param file_: file to read
    :type  file_: str"""
    directory = os.path.dirname(file_)
    with open(file_) as f:
        main_yml = dict(yaml.load(f.read()))
    merges = []
    if "merge" in main_yml:
        for merge_path in main_yml['merge']:
            path = os.path.join(
                directory,
                merge_path,
            )
            merges.append(read_yml(path))
        del main_yml['merge']
    for merge_struct in merges:
        main_yml = merge(main_yml, merge_struct)
    return main_yml


def merge(a, b):
    """Merge two dicts.

    :param a: dict a
    :type  a: dict
    :param b: dict b
    :type  b: dict
    :rtype:   dict
    """
    if isinstance(a, dict) and isinstance(b, dict):
        d = dict(a)
        d.update(dict(((k, merge(a.get(k, None), b[k])) for k in b)))
        for k, v in d.items():
            if v == "None":
                del d[k]
        return d
    return b


def execute_and_parse_show_cmd(args):
    """Executes and parses a aptly show command.

    :param args: Command to execute
    :type  args: list
    """
    result = {}
    show, _ = pyaptly.call_output(args)
    for line in show.split('\n'):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.lower()
            result[key] = value.strip()
    return result


def create_config(test_input):
    """Return path to pyaptly config from test input.

    :param test_input: Test input read from test-yml.
    :type  test_input: dict
    :rtype:            str
    """
    input_ = read_yml(test_input)
    if 'mirror' in input_:
        for mirror in input_['mirror'].values():
            if 'components' not in mirror:
                mirror['components'] = "main"
            if 'distribution' not in mirror:
                mirror['distribution'] = "main"
    try:
        file_ = tempfile.NamedTemporaryFile(delete=False)
        yaml.dump(input_, file_)
    finally:
        file_.close()
    return (input_, file_.name)


@contextlib.contextmanager
def clean_and_config(test_input):
    try:
        shutil.rmtree("/home/vagrant/.aptly")
    except OSError:
        pass
    input_, file_ = create_config(test_input)
    if 'mirror' in input_:
        for mirror in input_['mirror'].values():
            if 'gpg-keys' in mirror:
                for key in mirror['gpg-keys']:
                    try:
                        subprocess.check_call([
                            'gpg',
                            '--keyring',
                            'trustedkeys.gpg',
                            '--batch',
                            '--yes',
                            '--delete-key',
                            key,
                        ])
                    except subprocess.CalledProcessError:
                        pass
    yield (input_, file_)
    os.unlink(file_)
