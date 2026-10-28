FROM ghcr.io/home-assistant/base@sha256:880016115f356afc814398e17ba68a7ee66dfc1b4eaef09755ea2c9fa18ea481

ARG BUILD_VERSION=0.5.1
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
