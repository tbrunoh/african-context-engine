# Entry points

| # | Entry point | Payload in | Rendering out | Status |
|---|---|---|---|---|
| 1 | Voice call | Transcript or audio URI plus caller number | Short spoken turns of up to three sentences | Adapter ready; speech providers pluggable |
| 2 | USSD | Gateway callback: `sessionId`, `serviceCode`, `phoneNumber`, `text` | `CON` or `END` screen within 182 characters | Adapter ready |
| 3 | SMS | Sender and text | GSM-7 or UCS-2 aware segments, capped per reply | Adapter ready |
| 4 | WhatsApp | Business Platform (Cloud API) webhook: text, image, audio, document, location | Text with sources appended | Adapter ready |
| 5 | Smartphone app | SDK calls | Native UI | Planned |
| 6 | Trusted agent | Agent app session on behalf of a client, with client consent | Native UI plus SMS receipt to the client | Planned |
| 7 | Interactive radio | IVR call-ins during broadcasts | Answers read on air, follow-up by SMS | Planned |
| 8 | API and MCP | MCP tool call `query_context` or REST | Structured facts with sources and review status | MCP server ready |

## Channel policy notes

- **WhatsApp**: from 15 January 2026 the Business API terms bar general purpose AI assistants. Run ACE on WhatsApp as a vertical expert service operated by or for a named business.
- **USSD and shortcodes**: require agreements with each mobile operator or an aggregator. Plan for several operators so no single one is essential.
- **Outbound messages**: alerts and follow-ups need prior opt-in and must respect each channel's template and quiet hour rules.
