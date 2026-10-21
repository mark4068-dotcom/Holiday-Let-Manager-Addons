# Repository and release policy

Updated 21 October 2026.

Holiday-Let-Manager-Addons is the canonical source for future Home Assistant
add-on fixes and releases: Sheets Service, Guest Guide, iCalendar Aggregator,
and IOW Ferry Status. It also owns the Crossjack kiosk companion agent.
Holiday-Let-Manager owns the HLM custom integration and operational configuration.
Coastal Water Watch remains an independent custom integration.

HLM_iCalendar_Aggregator and IOW_ferry_status retain historical standalone
baselines. They are not automatically synchronised with the Addons repository.
Keep their checks running, but implement future add-on changes in Addons.
Do not install both copies of the same add-on. Existing installations should
record their repository, slug, version, options and data backup before migrating;
validate the replacement on development Home Assistant before production.

## Validation and releases

Run the repository checks before committing. GitHub Actions runs tests and release
metadata validation; add-on repositories also build amd64 containers. This does
not establish aarch64 compatibility or prove live scraper/source behaviour.
Validate those on development Home Assistant before a production release.
Set required branch checks in GitHub after the first successful workflow run.

Keep config.yaml, package.json, package-lock.json and Docker BUILD_VERSION
consistent. Tag reviewed release commits and record deployment and rollback
versions. A source push does not authorise a production update.

Container bases are pinned by digest and JavaScript installs use npm ci.
Review Dependabot updates weekly; browser and Playwright changes require a live
scraping check together. OS package repositories remain external inputs: retain
built image digests for exact deployment rollback.

The HLM and Coastal Water Watch CI baseline is Python 3.13 / Home Assistant
2026.2.3, matching the existing local test environment. This is a tested baseline,
not a claim of compatibility with every newer Home Assistant release. Validate
an upgrade separately before changing production.

HLM lint currently covers its integration and tests. Historical kiosk utilities
have a separate lint backlog; do not apply a blanket automatic rewrite.
