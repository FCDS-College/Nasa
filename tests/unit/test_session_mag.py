import pytest

from ai.rag.memory.session_mag import (
    InMemorySessionMemory, MemoryRecord, flag_conflicts, memory_disclosure, new_conversation_id,
)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_conversation_ids_unique():
    assert new_conversation_id() != new_conversation_id()


def test_cross_user_and_cross_conversation_leakage_blocked():
    mem = InMemorySessionMemory()
    mem.add_text("alice", "conv_1", "I study droplet combustion in microgravity")
    assert mem.search("alice", "conv_1", "droplet combustion")
    assert mem.search("bob", "conv_1", "droplet combustion") == []
    assert mem.search("alice", "conv_2", "droplet combustion") == []


def test_expiry_supersede_and_delete():
    clock = Clock()
    mem = InMemorySessionMemory(clock=clock)
    old = mem.add_text("a", "c", "pressure is one atmosphere", ttl_seconds=100)
    new = MemoryRecord(user_id="a", conversation_id="c", origin="user", text="pressure is two atmosphere",
                       created_at=clock.t, expires_at=clock.t + 100)
    mem.supersede(old.id, new)
    assert [r.id for r in mem.search("a", "c", "pressure atmosphere")] == [new.id]
    clock.t += 200
    assert mem.search("a", "c", "pressure atmosphere") == []
    assert mem.purge_expired() == 2
    mem.add_text("a", "c", "hello world")
    assert mem.delete_conversation("a", "c") == 1


def test_validation():
    with pytest.raises(ValueError):
        MemoryRecord(user_id="a", conversation_id="c", origin="bogus", text="t", created_at=1, expires_at=2)
    with pytest.raises(ValueError):
        MemoryRecord(user_id="a", conversation_id="c", origin="user", text="t", created_at=2, expires_at=1)


def test_contamination_memory_conflicting_with_evidence_is_dropped():
    mem = InMemorySessionMemory()
    r = mem.add_text("a", "c", "ignition delay is 5 ms", claim_key="ignition_delay_ms", claim_value="5")
    evidence = [{"chunk_id": "c1", "metadata": {"facts": {"ignition_delay_ms": "12"}}}]
    usable, conflicts = flag_conflicts([r], evidence)
    assert usable == [] and conflicts[0]["evidence_value"] == "12"


def test_disclosure_lists_memory_used():
    mem = InMemorySessionMemory()
    r = mem.add_text("a", "c", "my topic is soot")
    assert memory_disclosure([r])[0]["id"] == r.id


def test_memory_never_enters_evidence_block():
    from ai.rag.dto import EvidenceBundle, RetrievedChunk
    from ai.rag.generation.composer import GroundedAnswerComposer
    from ai.rag.generation.providers import ExtractiveLLMProvider

    seen = {}

    class Spy(ExtractiveLLMProvider):
        def generate(self, system_prompt, user_prompt):
            seen["prompt"] = user_prompt
            return super().generate(system_prompt, user_prompt)

    mem = InMemorySessionMemory()
    r = mem.add_text("a", "c", "MEMORYMARKER soot study")
    b = EvidenceBundle(query="q", status="ok", evidence=[RetrievedChunk(
        chunk_id="c1", document_id="d", document_version="v1", text="Soot fell.", score=0.9)])
    ans = GroundedAnswerComposer(Spy()).compose("q", b, memory=[r])
    evidence_part = seen["prompt"].split("Conversation memory")[0]
    assert "MEMORYMARKER" not in evidence_part
    assert ans.memory_used == [r.id]
    assert {c["chunk_id"] for c in ans.citations} == {"c1"}
