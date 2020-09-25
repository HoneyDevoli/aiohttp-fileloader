import os
from pathlib import Path

from argparse import ArgumentTypeError
from typing import Callable, Optional


def validate(type: Callable, constrain: Optional[Callable] = None):
    """Validate input args"""
    def wrapper(value):
        value = type(value)
        if not constrain(value):
            raise ArgumentTypeError
        return value

    return wrapper


def create_dirs(path: Path):
    path.mkdir(parents=True, exist_ok=True)


positive_int = validate(int, constrain=lambda x: x > 0)


def clear_environ(rule: Callable):
    """Clears environment variables, variables for clearing are
     determined by the passed rule function
    """
    for name in filter(rule, tuple(os.environ)):
        os.environ.pop(name)
