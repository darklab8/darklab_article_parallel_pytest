import argparse
from .settings import CommandName
from . import exceptions
from . import utils
from . import parallel_pytest
from . import logger

logger = logger.get_logger(__name__)


class Makefile:
    def __init__(self, args=None):
        self._get_args(args=args)
        self._run()

    def _get_args(self, args):
        parser = argparse.ArgumentParser(description="Makefile")

        commands = parser.add_subparsers(dest="command", required=True)
        await_db = commands.add_parser(  # noqa: F841
            name=CommandName.await_db,
            help="script to await side car containers initialization",
            # since we invoke parser from different file,
            # we disable help in order to enable their help invoked correctly with --help
            add_help=False,
        )
        combine_junits = commands.add_parser(  # noqa: F841
            name=CommandName.combine_junits,
            help="script to combine multiple junit files into one",
            # since we invoke parser from different file,
            # we disable help in order to enable their help invoked correctly with --help
            add_help=False,
        )
        parallel_pytest = commands.add_parser(  # noqa: F841
            name=CommandName.parallel_pytest,
            help="script to run multiple pytest tests in parallel",
            # since we invoke parser from different file,
            # we disable help in order to enable their help invoked correctly with --help
            add_help=False,
        )

        args, other_args = parser.parse_known_args(args=args)
        self.args = args
        self.other_args = other_args

    def _run(self):
        other_args = self.other_args

        logger.info(f"_run.other_args={other_args}")
        logger.info(f"_run.args={self.args}")

        # we can connect command to root CLI through subprocess.run, or through main import with overriding args
        # first option is preferable for sub commands with installable deps like psycopg2
        # second option is preferable if they are having only python inbuilt deps

        # take a note that each command can be invoked without calling root CLI
        commands = {
            CommandName.await_db: lambda: utils.run_in_shell(
                " ".join([f"python3 -m make.{CommandName.await_db}"] + other_args)
            ),
            CommandName.combine_junits: lambda: utils.run_in_shell(
                " ".join([f"python3 -m make.{CommandName.combine_junits}"] + other_args)
            ),
            CommandName.parallel_pytest: lambda: parallel_pytest.main(args=other_args),
        }

        try:
            commands[self.args.command]()
        except KeyError:
            raise exceptions.NotRegisteredCommand()


def main():
    Makefile()
