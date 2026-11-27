# Connecting real channels

`ace serve` runs one web server for every channel. Put it behind HTTPS (a reverse proxy, a platform such as Cloud Run or Fly, or a tunnel while testing) and point each provider at the matching path.

```bash
export ACE_PSEUDONYM_SALT="a long random secret"    # required in production; keeps phone numbers unlinkable
export ACE_WEBHOOK_SECRET="another random secret"   # add ?key=<secret> to every provider callback URL
export ACE_API_TOKEN="a token for /v1/*"            # optional, protects the JSON API
ace serve --host 0.0.0.0 --port 8000 --tips-file /data/tips.jsonl
```

Or with Docker: `docker build -t ace . && docker run -p 8000:8000 -e ACE_PSEUDONYM_SALT=... ace`.

## USSD (Africa's Talking)

1. Create a USSD channel in the Africa's Talking dashboard (start in the sandbox).
2. Set the callback URL to `https://your-host/ussd?key=<ACE_WEBHOOK_SECRET>`.
3. Dial the code from the sandbox simulator.

ACE replies with `CON` or `END` in plain text. Every screen is kept within 182 characters and is composed locally, because networks time out quickly: on Kenyan networks a session lasts up to 180 seconds, Safaricom drops it after 30 seconds without input, and Airtel gives the application 15 seconds to respond ([Africa's Talking](https://help.africastalking.com/en/articles/1284071-what-is-the-duration-of-a-ussd-session-for-kenyan-telcos)). The app is stateless, so you can run several instances.

## SMS (Africa's Talking)

1. Set the incoming messages callback to `https://your-host/sms?key=<ACE_WEBHOOK_SECRET>`.
2. To send replies, set `AT_USERNAME`, `AT_API_KEY` and optionally `AT_SENDER_ID`, and construct the server with an `AfricasTalkingSms` sender:

```python
from ace_engine import Engine
from ace_engine.channels import AfricasTalkingSms
from ace_engine.server import serve

serve(Engine.from_packs("context_packs"), host="0.0.0.0", sms_sender=AfricasTalkingSms())
```

Replies in Latin script are folded into the GSM-7 alphabet (typographic marks to plain ones, accents GSM-7 lacks dropped) and limited to three segments. Arabic and Amharic replies travel as UCS-2 and are composed for its smaller segments. The username `sandbox` targets the sandbox API.

## Voice (Africa's Talking)

Set the voice callback to `https://your-host/voice?key=<ACE_WEBHOOK_SECRET>`. Callers hear a keypad menu of the loaded packs and the short form of each fact. The line speaks a language only where a voice is known to exist for it. The Say action reads English, Swahili, French, Portuguese and Arabic with Google Cloud voices. Set `GEMINI_API_KEY` and `ACE_VOICE_AUDIO_URL` and the line also speaks Amharic and Somali: ACE synthesises the audio with Gemini 3.8 Flash TTS, caches it, serves it at `/voice/audio/`, and the call plays it. Afaan Oromo has no voice yet, so Oromo callers hear the next language of their country that has one, then English, and get the full reply in their own language on SMS and USSD. If your provider has checked voices for more languages, list them in `ACE_VOICE_LANGUAGES` (for example `en,sw,am`). To accept spoken questions, pass a speech to text engine to `VoiceAdapter`; `GoogleSpeechToText` from `ace_engine.speech.google` is ready to use. See [speech.md](speech.md).

## WhatsApp (Cloud API)

1. Set `WHATSAPP_VERIFY_TOKEN` and `WHATSAPP_APP_SECRET`, then register `https://your-host/whatsapp` as the webhook. ACE answers the verification request and rejects calls without a valid signature.
2. To send replies, set `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` and `WHATSAPP_API_VERSION`, and pass a `WhatsAppCloudSender` to the server.

Since 15 January 2026 the WhatsApp Business API bars general purpose AI assistants. Run ACE on WhatsApp only as a scoped service operated by or for a named organisation, answering from its own packs.

## RCS with SMS fallback

RCS gives people with a capable phone suggested replies (More, Sources, Help, in their language) and the sources under every answer, in the messaging app they already have. It runs over mobile data or Wi-Fi and only where a carrier has launched it, so ACE treats it as a richer layer over SMS, never a replacement. Every RCS reply is composed to the SMS budget, so a fallback never cuts an answer or an emergency number.

1. Register an RCS for Business agent and have it launched on each carrier you plan to use. Agents need approval before they can message people outside a test list.
2. Set `RBM_CLIENT_TOKEN` to the webhook client token, then register `https://your-host/rcs` as the webhook. ACE answers the verification request and rejects messages without a valid `X-Goog-Signature`. Until the token is set, `/rcs` answers 503, so an unsigned message can never trigger a text.
3. Switch RCS on country by country with `ACE_RCS_COUNTRIES`, for example `NG,ZA`. Left empty, the default, RCS stays off and every reply goes by SMS.
4. To send, set `RBM_AGENT_ID` and give an OAuth access token for a service account with RBM access. A static `RBM_ACCESS_TOKEN` expires within about an hour, after which every reply falls back to SMS, so in production pass a callable that returns a fresh token, for example from google-auth. Pass an `RbmSender` and an SMS sender to the server. Set `RBM_REGION=europe` for African numbers: Google's best practices route numbers that start with +2 or +3 to the europe endpoint. `RBM_TRAFFIC_TYPE` sets `messageTrafficType` where a carrier bills by traffic type.

```python
from ace_engine import Engine
from ace_engine.channels import AfricasTalkingSms, RbmSender
from ace_engine.server import serve

serve(Engine.from_packs("context_packs"), host="0.0.0.0",
      sms_sender=AfricasTalkingSms(), rcs_sender=RbmSender())
```

Before each reply ACE asks the RBM API whether the person can receive RCS. A 404 means they cannot: their phone lacks RCS or has it switched off, or the agent is not launched on their network. The reply then goes by SMS, and so does any reply that RCS refuses or cannot start. A send that times out after Google may have accepted it is not repeated by SMS, so nobody gets the same reply twice. Every reply ends with suggested reply chips except an emergency reply, which keeps the numbers as the only focus. Opt in alerts can use the same `RcsWithSmsFallback` delivery.

## JSON API

```bash
curl -s localhost:8000/v1/ask -H 'Content-Type: application/json' \
  -d '{"text": "how do I store maize", "channel": "sms", "phone": "+254711000000"}'
curl -s localhost:8000/v1/scam -H 'Content-Type: application/json' -d '{"text": "send your PIN"}'
curl -s 'localhost:8000/v1/emergency?queue=gbv'
curl -s localhost:8000/v1/packs
```

Responses carry `text`, `kind` (answer, emergency, scam, clarify, system), `language`, `escalated` and `citations` with source URLs.

`phone` sets the caller's country from its dialling code; without it, `country` (for example `"country": "NG"`) does the same. A request with neither is read as coming from outside ACE's 34 countries, so it gets only guidance that applies everywhere and is told to call the local emergency number, never another country's lines.

The MCP tools follow the same rule. `ask_ace` and `check_message` take the country when the assistant knows it, and with none they answer as for a caller outside ACE's 34 countries; `pest_check`, like the other service tools, requires it. No tool falls back to Kenya or any other country. A number in local format, such as 0712345678, carries no country either, so ACE gives it a private key and no country unless the deployment pins one with `--country`, which also gives local numbers that country's dialling code.

## Escalations

Emergency replies call `HandoffSink.raise_handoff(queue, person_key, text, channel)`. The default sink keeps events in memory. Connect it to your nurse helpdesk, extension officer queue or ticketing system by implementing that one method. The person key is pseudonymous; if your helpdesk must call people back, keep the number to key mapping in your own system under your own data protection controls.
