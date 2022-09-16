"solution made with https://pypi.org/project/junitparser/? for combining junit from parallel tests"
from types import SimpleNamespace
from junitparser import JUnitXml
import argparse
import pathlib
from .settings import FolderPath
from . import logger

logger = logger.get_logger(__name__)


def get_args(args=None):
    parser = argparse.ArgumentParser(description="Run tests in parallel")
    parser.add_argument(
        "N",
        type=int,
    )
    parser.add_argument("--folder", type=str, default=FolderPath.reports)
    args = parser.parse_args(args)
    return args


def combine(args: SimpleNamespace):
    xml = JUnitXml()

    for number in range(1, args.N + 1):
        path = str(pathlib.Path(args.folder) / f"junit_{number}.xml")
        logger.info(f"scanning file = {path}")
        xml += JUnitXml.fromfile(path)

    xml.write("unit.xml")


def main(args=None):
    args = get_args(args=args)
    combine(args)


if __name__ == "__main__":
    main()
