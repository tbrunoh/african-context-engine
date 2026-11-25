"""2.2 speech and translation: the support table, the voice line's spoken language, the Google clients and the
back translation report. Fake transports only; nothing here touches the network."""
from __future__ import annotations

import base64
import xml.etree.ElementTree as ET

import pytest

from ace_engine import i18n, speech
from ace_engine.channels import VoiceAdapter, VoiceApp
from ace_engine.cli import main
from ace_engine.speech import google, review
from ace_engine.text import SUPPORTED_LANGUAGES, guess_language


@pytest.fixture(autouse=True)
def no_declared_voices(monkeypatch):
    monkeypatch.delenv(speech.VOICE_LANGUAGES_ENV, raising=False)


def test_support_table_covers_every_language_with_dated_sources():
    data = speech.support()
    assert data["checked_on"] == "2026-11-25"
    assert set(data["languages"]) == set(SUPPORTED_LANGUAGES)
    assert all(url.startswith("https://") for url in data["sources"].values())
    for code in SUPPORTED_LANGUAGES:
        for kind in ("hear", "speak", "translate"):
            entry = speech.capability(code, kind)
            assert entry is None or entry["provider"] in data["sources"]


def test_only_languages_with_a_known_voice_are_spoken():
    assert {c for c in SUPPORTED_LANGUAGES if speech.speakable(c)} == {"en", "sw", "fr", "pt", "ar"}
    assert speech.spoken_language(["am", "om", "so", "en"]) == "en"
    assert speech.spoken_language(["so", "ar", "en"]) == "ar"


def test_operator_can_declare_the_voices_their_provider_has(monkeypatch):
    monkeypatch.setenv(speech.VOICE_LANGUAGES_ENV, "en, am")
    assert speech.speakable("am") and not speech.speakable("sw")
    assert speech.spoken_language(["am", "en"]) == "am"


def test_voice_line_speaks_english_to_an_ethiopian_caller_not_unvoiced_amharic(engine):
    app = VoiceApp(engine)
    assert app.spoken_language("+251911000001", "ET") == "en"
    root = ET.fromstring(app.respond({"callerNumber": "+251911000001", "isActive": "1"}))
    assert root.find("GetDigits/Say").text.startswith("Welcome to ACE.")


def test_voice_line_speaks_portuguese_in_mozambique(engine):
    assert VoiceApp(engine).spoken_language("+258841000001", "MZ") == "pt"


def test_voice_line_follows_a_declared_amharic_voice(engine, monkeypatch):
    monkeypatch.setenv(speech.VOICE_LANGUAGES_ENV, "en,am")
    assert VoiceApp(engine).spoken_language("+251911000002", "ET") == "am"


def test_old_import_path_for_speech_to_text_still_works():
    from ace_engine.channels.voice import SpeechToText
    assert SpeechToText is speech.SpeechToText


class FakePost:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def __call__(self, url, body):
        self.calls.append((url, body))
        return self.reply(body) if callable(self.reply) else self.reply


def test_google_speech_to_text_uses_chirp_3_for_amharic():
    post = FakePost({"results": [{"alternatives": [{"transcript": "ባለቤቴ እርጉዝ ናት"}]}]})
    stt = google.GoogleSpeechToText(project="demo", post=post, fetch=lambda url: b"RIFF")
    text, lang = stt.transcribe("https://example.org/rec.wav", "am")
    url, body = post.calls[0]
    assert text == "ባለቤቴ እርጉዝ ናት" and lang == "am"
    assert url == "https://us-speech.googleapis.com/v2/projects/demo/locations/us/recognizers/_:recognize"
    assert body["config"]["model"] == "chirp_3" and body["config"]["languageCodes"] == ["am-ET"]
    assert base64.b64decode(body["content"]) == b"RIFF"


def test_google_speech_to_text_routes_somali_to_the_first_chirp_region():
    post = FakePost({"results": []})
    google.GoogleSpeechToText(project="demo", post=post).transcribe("gs://bucket/call.wav", "so")
    url, body = post.calls[0]
    assert "asia-southeast1-speech.googleapis.com" in url and body["uri"] == "gs://bucket/call.wav"
    assert body["config"]["model"] == "chirp"


def test_google_speech_to_text_refuses_a_language_with_no_model():
    with pytest.raises(ValueError, match="keypad"):
        google.GoogleSpeechToText(project="demo", post=FakePost({})).transcribe("gs://b/x.wav", "om")


def test_transcript_reaches_the_safety_rail_like_any_text(engine):
    stt = google.GoogleSpeechToText(project="demo", post=FakePost(
        {"results": [{"alternatives": [{"transcript": "my father collapsed and is not breathing"}]}]}),
        fetch=lambda url: b"x")
    msg = VoiceAdapter(stt=stt).parse_inbound({"caller": "+254711000010", "audio_uri": "https://e.org/a", "language": "en"})
    assert engine.handle(msg).kind.value == "emergency"


def test_google_text_to_speech_uses_the_recorded_voice_and_refuses_amharic():
    post = FakePost({"audioContent": base64.b64encode(b"ID3").decode()})
    tts = google.GoogleTextToSpeech(post=post)
    assert tts.synthesize("Karibu ACE.", "sw") == b"ID3"
    assert post.calls[0][1]["voice"] == {"languageCode": "sw-KE"}
    with pytest.raises(ValueError):
        tts.synthesize("እንኳን ደህና መጡ", "am")


def test_google_translator_batches_and_checks_counts():
    post = FakePost(lambda body: {"translations": [{"translatedText": t.upper()} for t in body["contents"]]})
    tr = google.GoogleTranslator(project="demo", post=post, batch=2)
    assert tr.translate(["a", "b", "c"], target="en", source="so") == ["A", "B", "C"]
    assert len(post.calls) == 2 and post.calls[0][1]["sourceLanguageCode"] == "so"
    bad = google.GoogleTranslator(project="demo", post=FakePost({"translations": []}))
    with pytest.raises(RuntimeError):
        bad.translate(["a"], target="en")


def test_project_must_come_from_the_environment(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
        google.GoogleTranslator()


class EchoTranslator:
    """Answers echo for every string, except one safety string it garbles."""

    def __init__(self, garble: str):
        self.garble = garble

    def translate(self, texts, target, source="en"):
        return ["completely different words" if t == self.garble else "echo" for t in texts]


def test_backcheck_puts_drifted_safety_strings_first_and_changes_nothing():
    loc = i18n.locales()["so"]
    garble = loc.templates["safety.OPENERS.self_harm"]
    before = dict(loc.templates)
    rows = review.backcheck("so", EchoTranslator(garble))
    assert len(rows) >= len(loc.templates)
    assert rows[0].overlap == 0.0 and any(r.path == "safety.OPENERS.self_harm" and r.safety for r in rows[:50])
    report = review.markdown("so", rows)
    assert report.startswith("# Back translation check: Somali") and "never a verdict" in report
    assert dict(i18n.locales()["so"].templates) == before and i18n.locales()["so"].reviewed is False


def test_english_sources_cover_every_template_path():
    english = i18n.english_sources()
    for loc in i18n.locales().values():
        assert set(loc.templates) <= set(english)


def test_overlap_ignores_placeholders():
    assert review.overlap("Call {numbers} now", "call numbers now") == 1.0
    assert review.overlap("go to the clinic", "visit a hospital") < 0.3


@pytest.mark.parametrize("text,lang", [("Mtoto wangu ana homa tangu jana", "sw"),
                                       ("Ma fille a de la fièvre depuis hier", "fr"),
                                       ("Wiilkeyga wuxuu qabaa qandho", "so")])
def test_language_guess_after_the_waxal_marker_review(text, lang):
    assert guess_language(text) == lang


def test_short_words_shared_with_other_languages_no_longer_claim_somali():
    # ka and ku are common in Dagbani, Luganda and many other languages; alone they are not Somali.
    assert guess_language("o ka ku nyɛ", default="none") == "none"


def test_cli_voice_and_locales_status(capsys):
    assert main(["voice", "languages"]) == 0
    out = capsys.readouterr().out
    assert "am-ET" in out and "not spoken" in out
    assert main(["locales", "status"]) == 0
    assert "awaiting fluent review" in capsys.readouterr().out
