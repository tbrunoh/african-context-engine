# Safety and privacy

ACE talks to people about their crops, their pregnancies and their money. A wrong answer can cost a harvest, savings or a life. These are the guarantees the code gives, and the work every deployment still has to do.

## What the code guarantees

1. **The safety rail runs first.** Before commands, retrieval or any model, `EscalationPolicy` checks every message against phrase rules for self harm, maternal danger, poisoning, child protection, gender based violence and other urgent health cases, in English, Swahili and French. A match returns verified numbers for that queue from the emergency pack of the caller's own country, picked from the dialling code, and raises a handoff. Nothing else runs. ACE never gives a number from another country; where a country publishes no number for a queue, it says to call the local emergency number or go to the nearest health facility.
2. **Only checked facts are served.** Facts below `sourced`, expired facts and verified tier facts without a licence are filtered out before ranking.
3. **No invention.** The default composer only renders facts. A language model, if added, must cite a given fact in every sentence and may not introduce phone numbers; otherwise ACE falls back.
4. **Safety critical answers carry numbers.** Any answer built on a `safety_critical` fact ends with the numbers to call.
5. **Honest gaps.** No match means ACE says it has no checked guidance, never a guess.
6. **Scam Shield never says safe.** The best verdict is that no known warning signs were found.
7. **Pseudonymous identity.** Profiles are keyed by an HMAC of the normalised phone number with a deployment secret (`ACE_PSEUDONYM_SALT`). Handoffs and tips carry the key, not the number.
8. **Deletion on request.** FORGET or FUTA deletes the profile and every tip from that person. STOP records an opt out.
9. **Minimal memory.** Profiles hold language, last location, last topic and a short history that can be switched off (`ProfileStore(keep_history=False)`).

## What every deployment must do

- **Clinical and language review of the safety rules.** The phrase lists in `safety.py` were written from WHO and Kenyan helpline guidance, but they are a starting point. Have clinicians and fluent speakers review them for each language, and add a classifier on top. Keyword rules are a floor, not a ceiling.
- **Fluent speaker review of translations.** Every Swahili rendering in the starter packs is marked `reviewed: false`. Review and mark them before a public launch.
- **Re-check numbers.** Emergency contact facts expire after a year and are withheld until re-checked.
- **A human on the other end.** Connect `HandoffSink` to people who can act, and publish the hours they cover.
- **Data protection.** Kenya's Data Protection Act 2019 requires consent that is express, unequivocal, free, specific and informed, and limits collection to what is necessary ([ODPC](https://www.odpc.go.ke/wp-content/uploads/2024/02/TheDataProtectionAct__No24of2019.pdf)). ACE's design supports this, but the operator remains the data controller: give a clear notice on first contact, register with the Office of the Data Protection Commissioner where required, and set retention periods. Other countries have their own laws.
- **Channel policies.** Follow each provider's terms, including the WhatsApp Business API restriction on general purpose AI assistants.

## Reporting a safety problem

If ACE gives a harmful or wrong answer, open an issue with the message, the reply and the channel, but never include anyone's phone number or personal details. For security vulnerabilities, follow [SECURITY.md](../SECURITY.md).
