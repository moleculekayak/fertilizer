FROM python:3.11-slim-buster

WORKDIR /app

COPY docker_start ./

RUN apt-get update \
  && echo "----- Installing python requirements" \
  && pip install fertilizer \
  && echo "----- Preparing directories" \
  && mkdir /config /data /torrents \
  && echo "----- Cleanup" \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

EXPOSE 9713

ENTRYPOINT ["./docker_start"]
