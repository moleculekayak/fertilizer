import os
from flask import Flask, request

from src.torrent import generate_new_torrent_from_file
from src.errors import TorrentAlreadyExistsError, TorrentNotFoundError

app = Flask(__name__)

# TODO: hook up args for server mode


@app.route("/api/webhook", methods=["POST"])
def webhook():
  request_form = request.form.to_dict()
  filepath = request_form.get("path")

  if filepath is None:
    return http_error("Request must include a 'path' parameter", 400)

  if not filepath.endswith(".torrent"):
    return http_error("'path' must point to a .torrent file", 400)

  if not os.path.exists(filepath):
    return http_error(f"No torrent found at {filepath}", 404)

  try:
    config = app.config
    _, new_filepath = generate_new_torrent_from_file(
      filepath,
      config["output_dir"],
      config["red_api"],
      config["ops_api"],
    )

    return http_success(new_filepath, 201)
  except TorrentAlreadyExistsError as e:
    return http_error(str(e), 409)
  except TorrentNotFoundError as e:
    return http_error(str(e), 404)
  except Exception as e:
    return http_error(str(e), 500)


def http_success(message, code):
  return {"status": "success", "message": message}, code


def http_error(message, code):
  return {"status": "error", "message": message}, code


def run_webserver(output_dir, red_api, ops_api, host="0.0.0.0", port=9713):
  app.config.update(
    {
      "output_dir": output_dir,
      "red_api": red_api,
      "ops_api": ops_api,
    }
  )

  app.run(debug=True, host=host, port=port)
