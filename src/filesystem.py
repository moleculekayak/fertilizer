import os


def get_filename(path):
    return os.path.basename(path)


def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def get_files(input_folder, extension=".torrent"):
    return [
        os.path.join(input_folder, filename)
        for filename in os.listdir(input_folder)
        if filename.endswith(extension)
    ]
