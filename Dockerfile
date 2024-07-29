FROM python:3.11-slim-buster

ARG uid=1000
ARG gid=1000

COPY src /app
WORKDIR /app

COPY docker_start /app/docker_start

RUN apt-get update \
  && echo "----- Installing python requirements" \
  && pip install --trusted-host pypi.python.org -r requirements.txt \
  && echo "----- Adding fertilizer user and group and chown" \
  && groupadd -r fertilizer -g $gid \
  && useradd --no-log-init -MNr -g $gid -u $uid fertilizer \
  && chown fertilizer:fertilizer -R /app \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER fertilizer:fertilizer

CMD ["/app/docker_start"]
