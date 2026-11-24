# Changelog

## 1.0.0 (2026-11-23)

The first release people can use and build on.

### Added
- Safety rail with phrase rules in English and Swahili for self harm, maternal danger, poisoning, child protection, gender based violence and urgent health cases; replies with verified numbers and raises a human handoff.
- Scam Shield for mobile money messages, with nine signals grounded in Safaricom's published guidance.
- Retrieval with hard filters (review status, expiry, tier, place, season) and BM25 ranking over claims, translations and keywords; action intent boosting and topic coherence.
- USSD menu app, SMS with GSM-7 handling and Africa's Talking sending, voice IVR, WhatsApp Cloud API with signature checks.
- WSGI server for every webhook, a JSON API and a browser playground.
- Grounded generation for any OpenAI compatible model, with a citation and phone number check and extractive fallback.
- MCP tools: `ask_ace`, `search_context`, `check_message`, `emergency_contacts`, `list_packs`.
- Commands in English and Swahili: HELP, LANG, TIP, SCAM, SOURCES, MORE, STOP, FORGET.
- Pseudonymous profiles, deletion on request, community tip queue.
- Pack specification 1.0 and six sourced Kenya packs with Swahili translations.
- `ace` command line: ask, chat (including a terminal USSD simulator), scam, serve, packs, tips, demo.
- Competitive landscape, architecture, channels, safety and privacy docs; 20 good first issues.

### Changed
- Pack specification moved from 0.1 to 1.0 and added the `sourced` review status.
- The placeholder demo pack was replaced by sourced packs.

### Removed
- The M-PESA payment request builder, to keep payment credentials out of the default install. It returns later as an optional plugin.
