FROM python:3.11-slim-buster

ARG uid=1000
ARG gid=1000

WORKDIR /app

COPY requirements.txt main.py docker_start ./
COPY src src

RUN apt-get update \
  && echo "----- Installing python requirements" \
  && pip install --trusted-host pypi.python.org -r requirements.txt \
  && echo "----- Creating executable" \
  && echo "#!/bin/bash\npython3 /app/main.py \$@" >/bin/fertilizer \
  && chmod +x /bin/fertilizer \
  && echo "----- Adding fertilizer user and group and chown" \
  && groupadd -r fertilizer -g $gid \
  && useradd --no-log-init -MNr -g $gid -u $uid fertilizer \
  && chown fertilizer:fertilizer -R /app \
  && echo "----- Preparing directories" \
  && mkdir -p /config /output \
  && chown fertilizer:fertilizer -R /config /output \
  && echo "----- Cleanup" \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER fertilizer:fertilizer

ENTRYPOINT ["./docker_start"]
