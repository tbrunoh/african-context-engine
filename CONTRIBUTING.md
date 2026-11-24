# Contributing to ACE

Thank you for helping build the African Context Engine. There are four ways to contribute.

## 1. Code

1. Open an issue first for anything larger than a small fix, so maintainers can confirm the approach.
2. Fork, create a branch, and keep changes focused.
3. Run `ruff check src tests` and `pytest` before opening a pull request.
4. Every pull request needs tests for new behavior and a short note on how it was verified.
5. Sign off each commit (`git commit -s`) to certify the [Developer Certificate of Origin](https://developercertificate.org/).

## 2. Channel adapters

A new entry point is a class that implements `ChannelAdapter.parse_inbound` and `ChannelAdapter.render`. Keep adapters thin: no business logic, no model calls. Include fixture payloads from the provider's documentation in the tests and respect the channel's limits (screen length, segment size, policy terms).

## 3. Languages

Speech and text support for a new language needs: an evaluation set of real questions with reference answers reviewed by native speakers, results for the router's candidate models, and safety trigger terms reviewed by a clinician who speaks the language.

## 4. Context packs

Context packs carry the knowledge ACE grounds its answers in. The specification lives in [docs/context-packs.md](docs/context-packs.md) and [spec/context-pack.schema.json](spec/context-pack.schema.json).

- Every fact starts as `draft`. Never mark a fact `expert_reviewed` or `outcome_verified` yourself unless you are the named reviewer.
- Every fact names a source. Open packs only use sources you have the right to publish under CC BY 4.0.
- Mark facts that could cause harm if wrong as `safety_critical: true`.
- Do not include personal data about any individual.

### The path to the verified tier

1. **Community draft**: anyone submits a fact.
2. **Expert review**: a credentialed reviewer checks accuracy and safety for the stated place and season, and is named on the fact.
3. **Outcome check**: results from real sessions confirm the advice works where it is given.
4. **Verified tier**: the fact joins the licensed tier. Contributors and reviewers of verified facts earn a share of verified tier licensing revenue under the published contributor terms.

## Reporting problems

Use the issue templates. For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
