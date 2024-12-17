import argparse
import sys


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
  inputs = directories.add_mutually_exclusive_group(required=True)
  options = parser.add_argument_group(title="options")
  config = parser.add_argument_group(title="config")

  support.add_argument(
    "-h",
    "--help",
    action="help",
    default=argparse.SUPPRESS,
    help="show this help message and exit",
  )

  inputs.add_argument(
    "-i",
    "--input-directory",
    type=str,
    help="directory with the .torrent files to check",
  )
  inputs.add_argument(
    "-f",
    "--input-file",
    type=str,
    help="filepath of the single .torrent file to check",
  )
  directories.add_argument(
    "-o",
    "--output-directory",
    type=str,
    required=True,
    help="directory where cross-seedable .torrent files will be saved",
  )

  options.add_argument(
    "-s",
    "--server",
    action="store_true",
    help="starts fertizer in server mode. Requires -i/--input-directory",
    default=False,
  )

  options.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="enables verbose output",
    default=False,
  )

  config.add_argument(
    "-c",
    "--config-file",
    type=str,
    help="path to a configuration file",
    default="src/fertilizer/config.json",
  )

  parsed = parser.parse_args(args)

  if parsed.server and not parsed.input_directory:
    parser.error("--server requires --input-directory")

  return parsed
