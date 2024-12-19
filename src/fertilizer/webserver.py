import logging
import os

from flask import Flask, request

from fertilizer.errors import TorrentAlreadyExistsError, TorrentNotFoundError
from fertilizer.parser import is_valid_infohash
from fertilizer.scanner import scan_torrent_file

app = Flask(__name__)


@app.before_request
def log_request_info():
  app.logger.info(f"Incoming webhook with body: {request.get_data()}")


@app.after_request
def log_response_info(response):
  app.logger.info(f"Responding: {response.get_data()}")
  return response


@app.route("/api/webhook", methods=["POST"])
def webhook():
  config = app.config
  request_form = request.form.to_dict()
  infohash = request_form.get("infohash")
  # NOTE: always ensure safety checks are done before this filepath is ever used
  filepath = f"{config['input_dir']}/{infohash}.torrent"

  if infohash is None:
    return http_error("Request must include an 'infohash' parameter", 400)
  if not is_valid_infohash(infohash):
    return http_error("Invalid infohash", 400)
  if not os.path.exists(filepath):
    return http_error(f"No torrent found at {filepath}", 404)

  try:
    new_filepath = scan_torrent_file(
      filepath,
      config["output_dir"],
      config["red_api"],
      config["ops_api"],
      config["injector"],
    )

    return http_success(new_filepath, 201)
  except TorrentAlreadyExistsError as e:
    return http_error(str(e), 409)
  except TorrentNotFoundError as e:
    return http_error(str(e), 404)
  except Exception as e:
    return http_error(str(e), 500)


@app.errorhandler(404)
def page_not_found(_e):
  return http_error("Not found", 404)


def http_success(message, code):
  return {"status": "success", "message": message}, code


def http_error(message, code):
  return {"status": "error", "message": message}, code


def run_webserver(input_dir, output_dir, red_api, ops_api, injector, host="0.0.0.0", port=9713):
  app.logger.setLevel(logging.INFO)
  app.config.update(
    {
      "input_dir": input_dir,
      "output_dir": output_dir,
      "red_api": red_api,
      "ops_api": ops_api,
      "injector": injector,
    }
  )

  app.run(debug=False, host=host, port=port)
