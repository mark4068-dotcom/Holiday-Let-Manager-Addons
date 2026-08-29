FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION=0.1.5
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
COPY package.json ./
RUN npm install --omit=dev
COPY src ./src
COPY run.sh /
RUN chmod a+x /run.sh
CMD ["/run.sh"]
