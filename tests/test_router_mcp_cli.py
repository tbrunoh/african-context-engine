from __future__ import annotations

import json

import pytest

from ace_engine.cli import main
from ace_engine.engine import Engine
from ace_engine.mcp_server import build_tools
from ace_engine.models import Channel
from ace_engine.router import Budget, GroundedGenerator, check_grounded


class FakeModel:
    name = "fake"

    def __init__(self, output=None, error=None):
        self.output, self.error, self.prompts = output, error, []

    def generate(self, system, prompt, timeout_s):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.output


def _facts(engine, question="how do I store maize"):
    from ace_engine.context import ContextQuery

    return [s.fact for s in engine.store.query(ContextQuery(text=question, country="KE", limit=3))]


BUDGET = Budget(max_chars=600, short=False, max_facts=3)


def test_grounded_output_is_accepted_and_citations_mapped(engine):
    facts = _facts(engine)
    gen = GroundedGenerator(FakeModel("Dry your maize to about 13 percent moisture [1]. Store it airtight [2]."))
    out = gen.compose(facts, "en", BUDGET, question="how do I store maize")
    assert out.generator == "grounded:fake" and "[" not in out.text
    assert [f.id for f in out.used] == [facts[0].id, facts[1].id]


@pytest.mark.parametrize("output", [
    "Dry your maize well. Store it airtight [1].",       # a sentence without a citation
    "Use a moisture meter [7].",                         # cites a fact it was not given
    "Call 0700123456 for help [1].",                     # invents a phone number
    "NO_ANSWER",
    "",
])
def test_ungrounded_output_falls_back(engine, output):
    out = GroundedGenerator(FakeModel(output)).compose(_facts(engine), "en", BUDGET)
    assert out.generator == "extractive"


def test_model_errors_fall_back(engine):
    out = GroundedGenerator(FakeModel(error=TimeoutError())).compose(_facts(engine), "en", BUDGET)
    assert out.generator == "extractive" and out.text


def test_known_numbers_are_allowed():
    from ace_engine.context.schema import ContextFact

    fact = ContextFact(id="p/f", claim="Forward fake messages to 333.", topic="fraud", vertical="finance")
    ok, text, _ = check_grounded("Forward the message to 333 [1].", [fact], "en")
    assert ok and text == "Forward the message to 333."


def test_engine_with_model(packs_dir):
    model = FakeModel("Dry maize to about 13 percent moisture before storing it [1].")
    engine = Engine.from_packs(packs_dir, composer=GroundedGenerator(model))
    reply = engine.ask("how do I store maize", channel=Channel.WHATSAPP)
    assert reply.text.startswith("Dry maize to about 13 percent") and len(reply.citations) == 1
    assert "FACTS:" in model.prompts[0]


def test_mcp_tools(engine):
    tools = build_tools(engine)
    assert set(tools) == {"ask_ace", "search_context", "check_message", "emergency_contacts", "list_packs"}
    assert tools["ask_ace"]("how do I store maize")["citations"]
    assert tools["search_context"]("armyworm")[0]["review_status"] == "sourced"
    assert tools["check_message"]("send your PIN")["verdict"] == "likely_scam"
    assert "1195" in {c["number"] for c in tools["emergency_contacts"]("gbv")}
    assert len(tools["list_packs"]()) >= 6


def test_cli_validate_list_ask_scam(capsys, packs_dir):
    assert main(["packs", "validate", str(packs_dir)]) == 0
    assert "PASS" in capsys.readouterr().out
    assert main(["packs", "list", "--packs", str(packs_dir)]) == 0
    capsys.readouterr()
    assert main(["ask", "how", "do", "I", "store", "maize", "--packs", str(packs_dir), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "answer"
    assert main(["scam", "send", "your", "PIN", "--packs", str(packs_dir)]) == 0
    assert "likely_scam" in capsys.readouterr().out


def test_cli_validate_fails_on_bad_pack(tmp_path, capsys):
    (tmp_path / "bad.yaml").write_text("spec_version: '1.0'\nid: bad\n")
    assert main(["packs", "validate", str(tmp_path)]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_demo_runs(capsys, packs_dir):
    assert main(["demo", "--packs", str(packs_dir)]) == 0
    out = capsys.readouterr().out
    assert "Profile still held: False" in out and "UTAPELI" in out
