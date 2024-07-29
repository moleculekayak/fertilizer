import sys
import argparse

def parse_args(args=None):
  args = sys.argv[1:] if args is None else args

  name = sys.argv[0]
  description = "fertilizer: an open source cross-seeder for RED & OPS based on crops"
  parser = argparse.ArgumentParser(
    prog=name,
    description=description,
    add_help=False,
  )

  support = parser.add_argument_group(title="support")
  directories = parser.add_argument_group(title="directories")
  config = parser.add_argument_group(title="config")

  support.add_argument(
    "-h",
    "--help",
    action="help",
    default=argparse.SUPPRESS,
    help="show this help message and exit",
  )

  directories.add_argument(
    "-i",
    "--input-directory",
    type=str,
    required=True,
    help="folder with the .torrent files to check",
  )
  directories.add_argument(
    "-o",
    "--output-directory",
    type=str,
    required=True,
    help="folder where cross-seedable .torrent files will be saved",
  )

  config.add_argument(
    "-c",
    "--config-file",
    type=str,
    help="path to a configuration file",
    default="src/settings.json"
  )

  return parser.parse_args(args)
