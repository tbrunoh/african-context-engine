# Safety and privacy

ACE talks to people about their crops, their pregnancies and their money. A wrong answer can cost a harvest, savings or a life. These are the guarantees the code gives, and the work every deployment still has to do.

## What the code guarantees

1. **The safety rail runs first.** Before commands, retrieval or any model, `EscalationPolicy` checks every message against phrase rules for self harm, maternal danger, poisoning, child protection, gender based violence and other urgent health cases, in all 32 languages ACE speaks. A match returns verified numbers for that queue from the emergency pack of the caller's own country, picked from the dialling code, and raises a handoff. Nothing else runs. ACE never gives a number from another country; where a country publishes no number for a queue, including Guinea and South Sudan, which have no national emergency number, it says to call the local emergency number or go to the nearest health facility, and so does a message from a dialling code outside ACE's 34 countries. A snake bite is a snake word and a bite word anywhere in the message, because verbs inflect in too many ways to list. A breathing alarm about a farm animal, such as a goat that is not breathing well, still gets the emergency reply: the rail never stays quiet to spare a false alarm.
2. **Only checked facts are served.** Facts below `sourced`, expired facts and verified tier facts without a licence are filtered out before ranking.
3. **No invention.** The default composer only renders facts. A language model, if added, must cite a given fact in every sentence and may not introduce phone numbers; otherwise ACE falls back.
4. **Safety critical answers carry numbers.** Any answer built on a `safety_critical` fact ends with the numbers to call.
5. **Honest gaps.** No match means ACE says it has no checked guidance, never a guess.
6. **Scam Shield never says safe.** The best verdict is that no known warning signs were found.
7. **Pseudonymous identity.** Profiles are keyed by an HMAC of the normalised phone number with a deployment secret (`ACE_PSEUDONYM_SALT`). Handoffs and tips carry the key, not the number.
8. **Deletion on request.** FORGET or FUTA deletes the profile and every tip from that person. STOP records an opt out.
9. **Minimal memory.** Profiles hold language, last location, last topic and a short history that can be switched off (`ProfileStore(keep_history=False)`).
10. **Honest about languages, with a number to call.** A message plainly in a language ACE does not speak is not answered in the wrong language: ACE says it does not read the language yet, names the languages it reads in the caller's country, and gives the country's urgent health numbers, because a message ACE cannot read may still be an emergency. The check runs after the safety rail, commands and Scam Shield, never on a person who chose a language or is answering ACE's question, and it reads the message on the server with no network call, unless the operator turns on the optional language identifier below. See [languages.md](languages.md#languages-ace-does-not-speak).

## What every deployment must do

- **Fire, drowning, stabbing and road accidents.** The safety rail has no phrases for them yet, so a message about a house fire or a crash gets an ordinary reply, with the country's numbers only where a fact carries them. They are the next categories to add.
- **Clinical and language review of the safety rules.** The phrase lists in `safety.py` were written from WHO and Kenyan helpline guidance, but they are a starting point. Have clinicians and fluent speakers review them for each language, and add a classifier on top. Keyword rules are a floor, not a ceiling.
- **Fluent speaker review of translations.** Every Swahili and French rendering in the packs, every rendering in the 29 languages added since 2.1, and every added language file is marked `reviewed: false`. The 2.3 drafts in Bemba, Dyula, Pular, Wolof and, above all, Mooré are the least certain, so their safety phrases come first. Review and mark them before a public launch, safety phrases first.
- **Re-check numbers.** Emergency contact facts expire after a year and are withheld until re-checked.
- **A human on the other end.** Connect `HandoffSink` to people who can act, and publish the hours they cover.
- **Data protection.** Kenya's Data Protection Act 2019 requires consent that is express, unequivocal, free, specific and informed, and limits collection to what is necessary ([ODPC](https://www.odpc.go.ke/wp-content/uploads/2024/02/TheDataProtectionAct__No24of2019.pdf)). ACE's design supports this, but the operator remains the data controller: give a clear notice on first contact, register with the Office of the Data Protection Commissioner where required, and set retention periods. Other countries have their own laws.
- **Channel policies.** Follow each provider's terms, including the WhatsApp Business API restriction on general purpose AI assistants and the approval each carrier gives an RCS agent before it can message people.
- **Say if you send messages to a language identifier.** The optional `GoogleLanguageDetector` sends up to 500 characters of a message ACE would turn away to Google Cloud Translation under your project. Leave it off, run GlotLID on your own server instead, or name it in your privacy notice.
- **RCS webhook token.** Set `RBM_CLIENT_TOKEN` before exposing `/rcs`. Without it the route answers 503, so nobody can make ACE send texts by posting unsigned messages.

## Reporting a safety problem

If ACE gives a harmful or wrong answer, open an issue with the message, the reply and the channel, but never include anyone's phone number or personal details. For security vulnerabilities, follow [SECURITY.md](../SECURITY.md).
