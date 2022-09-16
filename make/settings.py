import pathlib


class CommandName:
    await_db = "await_db"
    combine_junits = "combine_junits"
    parallel_pytest = "parallel_pytest"


class FolderPath:
    scripts = pathlib.Path(__file__).parent.name

    # with results from parallel tests junit_{number}.xml and .coverage_{number}
    reports = "reports"


# path to
class AppPath:
    wait_for_it = str(pathlib.Path(FolderPath.scripts) / "wait_for_it.sh")
    await_db = f"-m {FolderPath.scripts}.{CommandName.await_db}"
    combine_junits = f"-m {FolderPath.scripts}.{CommandName.combine_junits}"
