from html import unescape
import os


def get_torrent_id(torrent_details):
    return torrent_details["response"]["torrent"]["id"]


def get_torrent_url(site_url, torrent_id):
    return f"{site_url}/torrents.php?torrentid={torrent_id}"


def get_torrent_filepath(torrent_details, source, folder_out):
    filename = (
        f'{unescape(torrent_details["response"]["torrent"]["filePath"])} '
        f'[{source}].torrent'
    )
    torrent_filepath = os.path.join(folder_out, filename)
    if os.path.isfile(torrent_filepath):
        return None
    return torrent_filepath


def download_torrent(api, torrent_filepath, torrent_id):
    with open(torrent_filepath, "wb") as f:
        r = api.download_torrent(torrent_id)
        f.write(r.content)
