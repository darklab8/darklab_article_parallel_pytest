"solution to run docker-compose with being sure side car containers are up"
from asyncio import subprocess
import time
import psycopg2
from dataclasses import dataclass
from contextlib import contextmanager
import argparse
import subprocess
from .settings import AppPath
from . import logger

logger = logger.get_logger(__name__)


def get_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_name", type=str, default="default")
    parser.add_argument("--user", type=str, default="postgres")
    parser.add_argument("--password", type=str, default="postgres")
    parser.add_argument("--host", type=str, default="db")
    parser.add_argument("--port", type=str, default="5432")
    parser.add_argument("--timeout", type=int, default=90)
    args, other_args = parser.parse_known_args(args)
    return args, other_args


default_args, _ = get_args(args=[])


@dataclass
class DatabaseParams:
    db_name: str = default_args.db_name
    user: str = default_args.user
    password: str = default_args.password
    host: str = default_args.host
    port: str = default_args.port


@contextmanager
def open_database(params: DatabaseParams):
    database = psycopg2.connect(
        " ".join(
            [
                f"dbname={params.db_name}",
                f"user={params.user}",
                f"password={params.password}",
                f"host={params.host}",
                f"port={params.port}",
            ]
        )
    )
    try:
        yield database
    finally:
        database.close()


@contextmanager
def open_cursor(database):
    with database.cursor() as cursor:
        yield cursor
        database.commit()


def wait_for_db(timeout: int):
    loop_delay = 3
    for i in range(int(timeout / loop_delay)):
        try:
            with open_database(DatabaseParams()) as database:
                with open_cursor(database) as cursor:
                    cursor.execute("select 1;")
                    logger.info("await_db: db is ready to accept connections")
                    return
        except psycopg2.OperationalError:
            logger.info(
                "await_db: db is not available yet. "
                f"waited {i*loop_delay} "
                f"Sleeping 3 seconds more. Timeout {timeout} seconds."
            )
            time.sleep(loop_delay)

    raise Exception("non zero exit")


def main(args=None):
    args, other_args = get_args(args=args)

    subprocess.run(
        f"{AppPath.wait_for_it} db:5432 -t {args.timeout}", shell=True, check=True
    )
    subprocess.run(
        f"{AppPath.wait_for_it} redis:6379 -t {args.timeout}", shell=True, check=True
    )

    wait_for_db(timeout=args.timeout)

    # allow other command to run after that
    logger.info(f"running chained command with args: {other_args}")
    subprocess.run(" ".join(other_args), shell=True, check=True)


if __name__ == "__main__":
    main()
