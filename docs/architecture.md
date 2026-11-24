# Architecture

ACE is one pipeline behind many entry points. Channels and models are designed to change; the context compounds.

## Request flow

1. **Adapter** parses the provider payload into a `Message` (`channels/`).
2. **Identity** normalizes the phone number to E.164 and loads the profile, so history, language, location and the last intent carry across channels (`identity.py`).
3. **Safety rail** checks for urgent cases first. A match returns a human handoff before any retrieval or model call (`safety.py`).
4. **Intent** maps the message to a vertical, topic and subject (`engine.KeywordClassifier`, replaceable). An unknown intent never triggers retrieval, so the engine cannot answer with off topic facts.
5. **Context query** retrieves facts scoped to the person's location, altitude, month, country and subject, ranked by specificity and review status (`context/store.py`).
6. **Grounded generation** builds a prompt that contains only retrieved facts and asks the model to cite fact ids (`router.py`). The default `ExtractiveProvider` quotes facts verbatim and is used offline and in tests.
7. **Reply** carries text, citations and any actions (for example a payment request). The adapter renders it within the channel's limits.
8. **Memory** records both turns on the profile.

## Layers and ownership

| Layer | Module | License |
|---|---|---|
| Entry | `channels/*` | Apache 2.0 |
| Engine and identity | `engine.py`, `identity.py` | Apache 2.0 |
| Intelligence | `router.py` | Apache 2.0 |
| Context engine | `context/*` | Apache 2.0 code; data per [DATA_LICENSE.md](../DATA_LICENSE.md) |
| Transactions | `payments/*` | Apache 2.0 |
| Partner access | `mcp_server.py` | Apache 2.0 |

## Design rules

- **Thin adapters.** No business logic in channel code.
- **Model agnostic.** Providers implement one `generate` method. Route speech to open models tuned for African languages, reasoning to frontier models, and offline use to small on-device models.
- **Grounded or silent.** If no fact applies, say so and offer a human.
- **Safety before generation.** Escalation runs first and cannot be skipped by a provider.
- **Consent and deletion built in.** `ProfileStore.forget` deletes a person's data.

## Production gaps in v0.1

Persistent stores, webhook signature checks, a trained intent classifier, speech provider integrations, the agent app, the radio IVR bridge and the smartphone SDK are planned. See [ROADMAP.md](../ROADMAP.md).
