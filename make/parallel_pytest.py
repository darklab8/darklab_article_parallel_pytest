from subprocess import Popen, PIPE
import subprocess
from enum import Enum, auto
import secrets
import argparse
from multiprocessing import cpu_count
import pathlib
from typing import List, Union
from .settings import FolderPath, AppPath
from . import utils
from . import exceptions
from . import logger

logger = logger.get_logger(__name__)


class Args:
    def __init__(self, args=None):
        self._get_args(args=args)

    def _get_args(self, args):
        parser = argparse.ArgumentParser(description="Run tests in parallel")
        parser.add_argument(
            "--first-n",
            dest="only_first_n_tests",
            type=int,
            help="Run only first N tests out of number of test splits",
        )
        parser.add_argument(
            "--image",
            type=str,
            help="using for CI already built image",
            default="clearly_undefined_image",
        )
        parser.add_argument(
            "--attached-volume",
            type=str,
            default=str(pathlib.Path().absolute()),
        )
        parser.add_argument(
            "--n",
            dest="number_of_splits",
            type=int,
            help="amount of runs in parallel, to how many numbers of splits to split tests",
            default=int(cpu_count() / 2),
        )
        parser.add_argument(
            "--dry",
            type=str,
            help="print commands only, add any value to invoke",
            default="",
        )

        args, other_args = parser.parse_known_args(args)
        self._args = args
        self.other_args = other_args

    @property
    def only_first_n_tests(self) -> Union[str, None]:
        return self._args.only_first_n_tests

    @property
    def attached_volume(self):
        return self._args.attached_volume

    @property
    def dry(self) -> bool:
        return bool(self._args.dry)

    @property
    def number_of_splits(self) -> int:
        return self._args.number_of_splits

    @property
    def random_session_id(self) -> str:
        return secrets.token_hex(4)

    @property
    def testpath(self) -> str:
        return "."

    @property
    def image(self) -> str:
        return self._args.image

    @property
    def compose_app(self) -> str:
        return "ci_app"


class Pipe(Enum):
    stdout = auto()
    stderr = auto()


def run_commands(composes: List[utils.Compose]):
    procs = [
        Popen(compose.run_command, shell=True, stdout=PIPE, stderr=PIPE)
        for compose in composes
    ]

    logger.info("================STDOUT=================")
    for proc in procs:
        for line in proc.stdout:
            print(line.decode("utf-8"))  # noqa: PW01

    logger.info("================STDERR=================")
    for proc in procs:
        for line in proc.stderr:
            print(line.decode("utf-8"))  # noqa: PW01

    for p in procs:
        p.wait()

    for proc in procs:
        if proc.returncode != 0:
            logger.error("One of test runs returned non zero exit")
            raise exceptions.NonZeroCommandReturn(
                "One of test runs returned non zero exit"
            )


def combine_coverage_and_junit(attached_volume: str, number_of_composes: int, args):
    utils.Compose(name="", id=secrets.token_hex(4),).register_run_command(
        envs={
            "IMAGE": args.image,
        },
        cmd=(
            f"--no-deps -u 0 -v {attached_volume}:/code {args.compose_app}"
            " sh -c 'coverage combine --keep " +
            " ".join(
                [
                    f"{FolderPath.reports}/.coverage_{number}"
                    for number in range(1, number_of_composes + 1)
                ]
            ) +
            f" ; coverage report ; coverage xml; python3 {AppPath.combine_junits} {number_of_composes}" +
            f" ; rm -R {FolderPath.reports}'"
        ),
    ).run(auto_down=True)


@utils.time_measure
def main(args=None):
    args = Args(args=args)

    session_ids = []
    for number in range(0, args.number_of_splits):
        session_ids.append(args.random_session_id)

    composes: List[utils.Compose] = []
    for number, session_id in enumerate(session_ids, start=1):

        composes.append(
            utils.Compose(name="", id=session_id,).register_run_command(
                envs={
                    "IMAGE": args.image,
                },
                cmd=(
                    f"-v {args.attached_volume}/{FolderPath.reports}:/code/{FolderPath.reports} -u 0"
                    f" {args.compose_app} python3 {AppPath.await_db}"
                    f" COVERAGE_FILE={FolderPath.reports}/.coverage_{number} pytest"
                    f" --cov=. --junit-xml={FolderPath.reports}/junit_{number}.xml"
                    f" --splits {args.number_of_splits} --group {number}"
                    f" {args.testpath}"
                ),
            )
        )

    logger.info(f"composes_init={composes}")
    if args.only_first_n_tests is not None:
        composes = composes[: args.only_first_n_tests]
    logger.info(f"composes_final={composes}")

    if args.dry:
        logger.info([compose.run_command for compose in composes])
        return

    try:
        subprocess.run(f"docker build --tag {args.image} .", shell=True, check=True)

        run_commands(composes)
    finally:
        for compose in composes:
            compose.down()

        combine_coverage_and_junit(
            attached_volume=args.attached_volume,
            number_of_composes=len(composes),
            args=args,
        )

        print("=======STDERR_SIMULATION=======")  # noqa: PW01
        with open("unit.xml", "r") as file_:
            print(file_.read())  # noqa: PW01


if __name__ == "__main__":
    main()
