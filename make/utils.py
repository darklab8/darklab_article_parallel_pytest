from time import time
import functools
import subprocess
import pathlib
from typing import Dict
from . import exceptions
from . import logger

logger = logger.get_logger(__name__)


def time_measure(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"time_measure - func={func.__name__} - started")
        start = time()
        func(*args, **kwargs)
        logger.info(f"time_measure - func={func.__name__} - elapsed={time()-start}")

    return wrapper


def run_in_shell(cmd: str, check: bool = False) -> subprocess.CompletedProcess:
    logger.info(f"run_in_shell={cmd}")
    return subprocess.run(cmd, shell=True, check=check)


class Compose:
    def __init__(self, name=None, id=None, auto_build=False):
        self._name = name
        self._id = (
            id if id is not None else str(pathlib.Path(".").parent.absolute().name)
        )
        self._auto_build = auto_build

    def __str__(self):
        parts = ["docker-compose"]
        if self._name:
            parts.append(self._name)
        parts.append("yml")
        return ".".join(parts)

    def build(self):
        run_in_shell(f"docker-compose -f {str(self)} -p {self._id} build")

    def down(self):
        command = f"docker-compose -f {str(self)} -p {self._id} down"
        logger.info(f"Compose.down={command}")
        run_in_shell(command)

    def register_run_command(self, *_, cmd: str, envs: Dict[str, str] = {}):
        self._cmd = cmd
        self._env = envs
        return self

    @property
    def run_command(self) -> str:
        env_args = " ".join([f"{name}={value}" for name, value in self._env.items()])

        command = ""
        if self._auto_build:
            command += f"docker-compose -f {str(self)} -p {self._id} build; "
        command += (
            f"{env_args} docker-compose -f {str(self)} -p {self._id}"
            f" run {self._cmd}"
        )
        logger.info(f"Compose.run_command={command}")
        return command

    def run(self, auto_down: bool = False, check: bool = False):
        logger.info(f"Compose.run={self.run_command}")
        try:
            result = run_in_shell(self.run_command)
        finally:
            if auto_down:
                self.down()

            if check and result.returncode != 0:
                raise exceptions.NonZeroCommandReturn()
