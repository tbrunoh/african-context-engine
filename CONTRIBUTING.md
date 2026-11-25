# Contributing to ACE

Thank you for helping build the African Context Engine. ACE is only as good as the knowledge in its packs and the care in its code, so both kinds of contribution count equally.

New here? Pick a task from [docs/good-first-issues.md](docs/good-first-issues.md).

Using an AI coding agent? It must follow [AGENTS.md](AGENTS.md). The V2 plan is in [docs/v2](docs/v2/README.md).

## Set up

```bash
git clone https://github.com/tbrunoh/african-context-engine.git
cd african-context-engine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check src tests benchmark && ace packs validate && python -m benchmark.run --quick
```

## 1. Knowledge: context packs

Packs are YAML files under `context_packs/<country>/`. You can contribute through the GitHub web editor without installing anything.

- Read [docs/context-packs.md](docs/context-packs.md) first.
- Every fact names its source. Use `draft` if you have not compared the claim with the source yourself, and `sourced` only when you have, with `source_url` and `checked_on`.
- Never mark a fact `expert_reviewed` or `outcome_verified` unless you are the named reviewer or the reviewer agrees on the pull request.
- Mark facts that could cause harm if wrong as `safety_critical: true` and list the numbers to call.
- Translations start as `reviewed: false`. Fluent speakers can review and set `reviewed: true`.
- Do not include personal data about anyone.
- If your source comes from an organisation not yet listed in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md), add it there in the same pull request.

## 2. Code

1. Open or comment on an issue first for anything larger than a small fix.
2. Keep pull requests focused. Add tests for new behaviour.
3. Run `ruff check src tests benchmark`, `pytest`, `ace packs validate` and `python -m benchmark.run --quick` before you push.
4. Sign off each commit (`git commit -s`) to certify the [Developer Certificate of Origin](https://developercertificate.org/).

Principles that reviewers will hold you to:

- **Safety first.** Nothing may run before the safety rail or weaken it. Changes to `safety.py` need tests for both new catches and things that must not trigger.
- **Grounded or silent.** No code path may send a person text that is neither a checked fact nor a fixed system message.
- **Fits the phone.** Respect channel budgets: 182 characters per USSD screen, three SMS segments, short spoken turns.
- **Privacy.** Never log or store phone numbers in clear. Use the profile key.
- **Few dependencies.** The core runs on the standard library plus PyYAML. Put anything heavier behind an optional extra.

### Adding a channel

Implement `ChannelAdapter.parse_inbound` and `ChannelAdapter.render` in `channels/`, keep business logic out of the adapter, add fixture payloads from the provider's documentation to the tests, and add a route in `server.py` if the channel uses webhooks.

### Adding a language

Add stopwords and marker words in `text.py`, system texts in `commands.py`, safety wording in `safety.py`, USSD and voice prompts in `channels/`, and translations to packs. Safety phrases must be reviewed by a clinician who speaks the language before they are merged.

## 3. Review

Maintainers review knowledge pull requests for sourcing and safety, and code pull requests for the principles above. Expert reviewers are named on the facts they review, so their work is visible to everyone who uses the pack.

## Reporting problems

Use the issue templates. For a harmful or wrong answer, include the message, the reply and the channel, but never anyone's phone number. For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
