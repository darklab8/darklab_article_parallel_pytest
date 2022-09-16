import logging
import logging.handlers


def get_logger(
    name: str = "",
    console_level: int = logging.DEBUG,
):
    logger = logging.getLogger("").getChild(name)

    # global level, controlling available levels in handlers
    logger.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(console_level)  # type: ignore
    formatter = logging.Formatter(
        " - ".join(
            [
                "time:%(asctime)s",
                "level:%(levelname)s",
                "name:%(name)s",
                "msg:%(message)s",
            ]
        )
    )
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)
    return logger
