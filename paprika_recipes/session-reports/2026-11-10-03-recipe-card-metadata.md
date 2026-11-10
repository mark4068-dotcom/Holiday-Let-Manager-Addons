# 10 November 2026 — recipe card thumbnail and attribution


## Follow-on: thumbnail and author cards — 10 November 2026

Owner requested each recipe card show name, picture thumbnail, category and author. Frontend 0.27.1 now uses a side-by-side thumbnail and text layout, preserving all category labels and using Paprika's source field as Author/source. No author is inferred from a domain. Missing values explicitly show No photo, Uncategorised or Author/source not supplied. Three image requests run concurrently; stale replies are discarded after paging/navigation. Images are displayed as thumbnails from the original embedded photo, not resized derivatives. The authenticated fixed-path backend gains a photo action, restricted to JPEG/PNG/WebP and a 2 MB read limit; existing identity/URL/timeout rules remain. Companion 0.2.1 list API includes source metadata and an assertion covers it.

Browser verification at 1280×800 with the actual private collection showed 24 cards, 24 author/source rows and 21 decoded photos (three cards had no embedded photo), with no horizontal overflow. Screenshot is private at /private/tmp/topgallant-recipe-cards.png, not Git. Seven companion tests pass; Topgallant Python suite and HA module import are checked before commit. No live HA/Pi deployment or physical acceptance. Previous source commits b0adf4f (Topgallant) and 57e781d (companion); final follow-on hashes are given in chat. Feature branches are unchanged. Preview server stopped at session close.

Resume from session report02 for full architecture/deployment/rollback instructions. This change does not require a new export or database migration. Canonical source remains the HLM add-ons project; private exports/data stay ignored. Update service API and Topgallant frontend/backend together before live acceptance.

Owner refinement before publication: omit the literal Author/source: prefix; render only the supplied name or website. Missing attribution shows Not supplied.
