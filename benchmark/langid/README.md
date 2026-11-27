# Language profiles

`build.py` builds `src/ace_engine/langid/profiles.json`, the character profiles ACE uses to read a message with no marker word by its letters, and to tell a person when it does not read their language yet. See [docs/languages.md](../../docs/languages.md#languages-ace-does-not-speak) for how ACE uses them.

```bash
python benchmark/langid/build.py fetch   # FLORES-200 and the UDHR texts, each checked against its SHA-256
python benchmark/langid/build.py build   # writes src/ace_engine/langid/profiles.json
```

A profile counts the three letter sequences of a language in folded text, the way ACE reads a message, and keeps the 2,000 most common. ACE's 32 languages are built from ACE's own locale and pack text, the FLORES-200 dev split and translations of the Universal Declaration of Human Rights. The 49 languages ACE does not speak come from FLORES-200 and the UDHR alone. The FLORES-200 archive is the one the tokenizer audit pins; the UDHR texts come from [github.com/eric-muller/udhr](https://github.com/eric-muller/udhr) at commit `e6a1b6f`, and `sources.json` records the SHA-256 of each file. A build from the same sources gives the same file, byte for byte.

No sentence is stored, only counts. Because FLORES-200 is CC BY-SA 4.0, `profiles.json` is shared under CC BY-SA 4.0. No WAXAL text is read here: the WAXAL check in `benchmark/waxal.py` stays a held-out test. Its thresholds, `MIN_GRAMS`, `MARGIN`, `PICK_GRAMS` and `PICK_MARGIN` in `src/ace_engine/langid/__init__.py`, were set on the WAXAL validation split and FLORES-200 dev.
