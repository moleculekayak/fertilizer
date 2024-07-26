import argparse


def get_formatter(prog):
    return argparse.HelpFormatter(prog)


def get_args():
    name = "fertilizer"
    description = "an open source cross-seeder for RED & OPS - based on crops"
    parser = argparse.ArgumentParser(
        prog=name,
        description=description,
        formatter_class=get_formatter,
        add_help=False,
    )

    support = parser.add_argument_group(title="support")
    directories = parser.add_argument_group(title="directories")
    extras = parser.add_argument_group(title="extras")

    support.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="show this help message and exit",
    )

    directories.add_argument(
        "-i",
        "--folder-in",
        type=str,
        required=True,
        help="folder with the .torrent files to check",
    )
    directories.add_argument(
        "-o",
        "--folder_out",
        type=str,
        required=True,
        help="folder where cross-seedable .torrent files will be saved",
    )

    extras.add_argument(
        "--download",
        action="store_true",
        help="download final .torrent files instead of generating them",
    )

    return parser.parse_args()
