from ai.rag.nlp.figures import FigureTableExtractor, associate_captions
from ai.rag.nlp.records import ChunkInput


def _run(text, chunk_id="c-1", doc="d-1", page=1):
    return FigureTableExtractor().extract(ChunkInput(chunk_id, doc, "v1", page, text))


def test_caption_and_reference_are_distinguished():
    records = _run("Spread rates are in Table 3 and Figs. 2.\nTable 3. Flame spread rates\n")
    kinds = [(r.record_type, r.normalized) for r in records]
    assert kinds == [("table_reference", "table:3"), ("figure_reference", "figure:2"), ("table_caption", "table:3")]
    assert records[2].text == "Table 3. Flame spread rates"


def test_reference_links_to_caption_in_another_chunk_of_the_same_document():
    refs = _run("See Table 3 for rates.", chunk_id="c-1", page=1)
    caps = _run("Table 3. Flame spread rates\n", chunk_id="c-2", page=4)
    other = _run("Table 3. Unrelated\n", chunk_id="c-9", doc="d-2")
    [linked] = [r for r in associate_captions([*refs, *caps, *other]) if r.record_type == "table_reference"]
    assert linked.payload == {"caption_record_id": caps[0].record_id, "caption_chunk_id": "c-2", "ambiguous": False}


def test_two_captions_for_one_label_are_ambiguous():
    refs = _run("See Table 3.", chunk_id="c-1")
    caps = _run("Table 3. First\n", chunk_id="c-2", page=2) + _run("Table 3. Second\n", chunk_id="c-3", page=5)
    [linked] = [r for r in associate_captions([*refs, *caps]) if r.record_type == "table_reference"]
    assert linked.payload["caption_chunk_id"] == "c-2" and linked.payload["ambiguous"] is True


def test_reference_without_a_caption_gets_no_link():
    [ref] = _run("See Table 9.")
    assert "caption_record_id" not in associate_captions([ref])[0].payload
