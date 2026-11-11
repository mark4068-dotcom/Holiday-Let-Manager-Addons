FROM ghcr.io/home-assistant/base@sha256:58422480a299b16b6ea376c2167463206d430619ed02b40cd687c8bd6875519e

ARG BUILD_VERSION=0.1.12
ARG BUILD_ARCH

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache \
    chromium \
    nodejs \
    npm \
    nss \
    freetype \
    harfbuzz \
    ttf-freefont

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY src ./src
COPY run.sh /
RUN chmod a+x /run.sh
CMD ["/run.sh"]
