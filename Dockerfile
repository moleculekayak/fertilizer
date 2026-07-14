FROM python:3.11-alpine AS builder

RUN echo "----- Installing build dependencies" \
  && apk add --no-cache \
    linux-headers \
    build-base

COPY . .

RUN echo '----- Making wheels dir in builder' \
  && pip wheel --no-cache-dir --wheel-dir=/wheels .




FROM python:3.11-alpine

WORKDIR /app

COPY --from=builder /wheels /wheels

RUN echo "----- Installing wheels" \
  && pip install --no-cache-dir /wheels/* \
  && rm -rf /wheels \
  && echo "----- Preparing directories" \
  && mkdir /config /data /torrents

COPY ./docker_start .

RUN chmod +x ./docker_start

EXPOSE 9713
ENTRYPOINT ["./docker_start"]
