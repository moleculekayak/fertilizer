import os


def mkdir_p(directory_path: str) -> str:
  if not os.path.exists(directory_path):
    os.makedirs(directory_path)

  return directory_path


def assert_path_exists(path: str) -> str:
  if not os.path.exists(path):
    raise FileNotFoundError(f"File or directory not found: {path}")

  return path


def list_files_of_extension(input_directory: str, extension: str = ".torrent") -> list[str]:
  return [
    os.path.join(input_directory, filename) for filename in os.listdir(input_directory) if filename.endswith(extension)
  ]


def replace_extension(filepath: str, new_extension: str) -> str:
  return os.path.splitext(filepath)[0] + new_extension
