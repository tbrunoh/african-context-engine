# Good first issues

Scoped tasks for a first contribution. Each one is useful on its own and comes with a clear way to check it. Comment on the matching GitHub issue (or open one with this title) before you start, so two people do not do the same work.

## Knowledge (no code needed)

1. **Review the Swahili translations in one pack.** Read each `translations.sw` claim and short form, fix anything unnatural, and set `reviewed: true`. Fluent speakers only. Check: `ace packs validate --strict` shows fewer warnings.
2. **Add Sheng and regional keywords.** Add the words people in your area actually use for armyworm, aflatoxin, M-PESA scams or danger signs to `keywords`. Check: `ace ask "<your phrasing>"` finds the right fact.
3. **County rain onset facts.** Add facts to `ke/rainfall-seasons.yaml` scoped with `admin_areas`, citing the Kenya Meteorological Department county forecast.
4. **A beans or sorghum pest pack.** Fall armyworm also attacks sorghum and millet. Start a pack from FAO or KALRO material, as `draft` if unchecked.
5. **Newborn danger signs.** A WHO sourced, safety critical pack on danger signs in newborns, with the same structure as `maternal-danger-signs.yaml`.
6. **Airtel Money safety.** Mirror the M-PESA pack for Airtel Money, using Airtel Kenya's published guidance.
7. **A first pack for another country.** Emergency numbers and mobile money safety for Uganda, Tanzania, Rwanda, Nigeria or Ghana, each number cited.
8. **Expert review.** If you are an agronomist, midwife or clinician, review a pack, add your name to `reviewed_by` on facts you have checked, and raise them to `expert_reviewed`.

## Code

9. **Kikuyu, Dholuo or Luhya stopwords and markers** in `text.py`, with tests, so language guessing and retrieval work for more speakers.
10. **Swahili prefix aware matching.** Swahili inflects with prefixes (`wanakula`, `anakula`, `kula`). Add a conservative normaliser to `text.py` and show a retrieval test that improves.
11. **Persistent profiles.** A `SqliteProfileStore` with the same methods as `ProfileStore`, plus tests. Keep deletion complete.
12. **Persistent handoffs.** A `HandoffSink` that writes to a JSON lines file or posts to a webhook.
13. **Scam Shield signals.** Add a signal for fake Fuliza limit messages or reversal requests that name a code, mapped to a sourced fact. Include messages that must not trigger it.
14. **A Telegram adapter** under `channels/`, with parse and render tests, following the WhatsApp adapter.
15. **USSD page memory.** Let callers on page two of the main menu choose items without going back, and test every path within 182 characters.
16. **Evaluation set.** A YAML file of real style questions in English and Swahili with the fact ids that should answer them, and a `pytest` that reports retrieval accuracy.
17. **`ace packs stats`.** Coverage by country, vertical, language and review status, for maintainers.
18. **Voice speech input.** A `SpeechToText` implementation for an open model, behind an optional dependency, with a test that uses a recorded fixture.
19. **Playground polish.** Show the USSD character count live and add a language toggle to the SMS tab.
20. **Type checking in CI.** Add mypy or pyright and fix what it finds.

## How to submit

Fork, branch, keep the change focused, run `ruff check src tests`, `pytest` and `ace packs validate`, and open a pull request that explains how you checked it. See [CONTRIBUTING.md](../CONTRIBUTING.md).
