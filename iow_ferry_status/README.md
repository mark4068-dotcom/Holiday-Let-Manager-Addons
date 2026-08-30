# IOW Ferry Status

Independent ferry-data integration for Holiday Let Manager. It collects official live status for six services: Red Funnel's Southampton–East Cowes vehicle ferry and Southampton–West Cowes Red Jet; Wightlink's Portsmouth Harbour–Ryde Pier Head FastCat, Portsmouth–Fishbourne vehicle ferry, and Lymington–Yarmouth vehicle ferry; plus Hovertravel's Southsea–Ryde hovercraft.

HLM consumes `GET /api/v1/status`. The versioned response exposes stable service IDs, current status and operator advisories; it intentionally omits timetables and sailing times. It retains the last successful payload when an operator cannot be reached. Set `api_token` to require `Authorization: Bearer …`. The dashboard at `/` groups routes into car-ferry and foot-passenger cards.

The official service-status pages are authoritative. Operator X feeds and interactive vessel maps remain outside the core status path so their failure cannot interrupt HLM updates. HLM provides separate touch launchers for the official Red Funnel and Wightlink live maps.

Operator extraction is deliberately contained here; HLM consumers depend only on the JSON contract, never the ferry websites.
