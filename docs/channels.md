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

## JSON API

```bash
curl -s localhost:8000/v1/ask -H 'Content-Type: application/json' \
  -d '{"text": "how do I store maize", "channel": "sms", "phone": "+254711000000"}'
curl -s localhost:8000/v1/scam -H 'Content-Type: application/json' -d '{"text": "send your PIN"}'
curl -s 'localhost:8000/v1/emergency?queue=gbv'
curl -s localhost:8000/v1/packs
```

Responses carry `text`, `kind` (answer, emergency, scam, clarify, system), `language`, `escalated` and `citations` with source URLs.

## Escalations

Emergency replies call `HandoffSink.raise_handoff(queue, person_key, text, channel)`. The default sink keeps events in memory. Connect it to your nurse helpdesk, extension officer queue or ticketing system by implementing that one method. The person key is pseudonymous; if your helpdesk must call people back, keep the number to key mapping in your own system under your own data protection controls.
