FROM python:3.11-slim-bookworm

WORKDIR /app

COPY docker_start pyproject.toml README.md ./
COPY src ./src

RUN echo "----- Installing build dependencies" \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    build-essential \
    gcc

# Install fertilizer from the repository source so the image always ships
# the code of the tagged commit (installing from PyPI raced the PyPI release
# and could bake a stale, cached version into the image)
RUN echo "----- Installing fertilizer Python package" \
  && pip install --no-cache-dir . \
  && echo "----- Preparing directories" \
  && mkdir /config /data /torrents \
  && echo "----- Cleanup" \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

EXPOSE 9713

ENTRYPOINT ["./docker_start"]
