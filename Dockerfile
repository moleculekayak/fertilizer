FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt main.py docker_start ./
COPY src src

RUN apt-get update \
  && echo "----- Installing python requirements" \
  && pip install --trusted-host pypi.python.org -r requirements.txt \
  && echo "----- Creating executable" \
  && echo "#!/bin/bash\npython3 /app/main.py \$@" >/bin/fertilizer \
  && chmod +x /bin/fertilizer \
  && echo "----- Preparing directories" \
  && mkdir /config /data /torrents \
  && echo "----- Cleanup" \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

EXPOSE 9713

ENTRYPOINT ["./docker_start"]
