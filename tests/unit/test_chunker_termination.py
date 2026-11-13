"""SimpleChunker must always terminate and make progress (audit finding P-1).

Before the fix, a short word followed by a long unbroken token sent `start` negative and the loop never advanced.
"""
import random
import signal

import pytest

from ai.rag.ingestion.chunker import SimpleChunker


class _Hang(Exception):
    pass


@pytest.fixture(autouse=True)
def _fail_instead_of_hanging():
    """A regression must fail this test, not freeze the suite (POSIX only; CI runs on Linux)."""
    def handler(signum, frame):
        raise _Hang("SimpleChunker did not terminate within 5 s")

    previous = signal.signal(signal.SIGALRM, handler)
    signal.alarm(5)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous)


def _chunk(text, size=500, overlap=50):
    document = {"document_id": "d", "version": "1", "text": text, "metadata": {}}
    return SimpleChunker(chunk_size=size, overlap=overlap).chunk(document)


@pytest.mark.parametrize("label,text", [
    ("short word then a long unbroken token", "ab " + "x" * 700),
    ("early space then a long unbroken token", "a " + "x" * 900),
    ("table-of-contents leader dots", "Contents " + "." * 800 + " 12"),
    ("token longer than the chunk with no spaces at all", "x" * 1200),
])
def test_pathological_inputs_terminate_with_bounded_chunks(label, text):
    chunks = _chunk(text)
    assert chunks, label
    assert all(0 < len(c["text"]) <= 500 for c in chunks), label


def test_every_chunk_makes_progress_on_random_text():
    rng = random.Random(2026)
    alphabet = ["a", "bb", "ccc", "x" * 40, "y" * 300, "z" * 700, " ", "  ", "\n"]
    for _ in range(300):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 60)))
        size = rng.choice([20, 100, 500])
        overlap = rng.choice([0, 5, size // 2, size - 1])
        chunks = _chunk(text, size, overlap)
        assert all(len(c["text"]) <= size for c in chunks)
        assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_no_word_is_lost_on_ordinary_text():
    words = [f"w{i}" for i in range(400)]
    chunks = _chunk(" ".join(words), size=120, overlap=30)
    seen = {w for c in chunks for w in c["text"].split()}
    assert set(words) <= seen
