FROM python:3.13-alpine

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="addon" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache openssl

WORKDIR /app
COPY rootfs /
COPY hlm_sheets_service /app/hlm_sheets_service

RUN chmod 755 /run.sh

CMD ["/run.sh"]
