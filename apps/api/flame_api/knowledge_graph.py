"""The scientific knowledge graph in PostgreSQL (ADR-007, E2-6): build, traverse, check, merge.

    python -m flame_api.knowledge_graph build                 # also run at the end of `python -m flame_api.ingest`
    python -m flame_api.knowledge_graph check                 # consistency report (exit 1 when a check fails)
    python -m flame_api.knowledge_graph merge LOSER WINNER --actor NAME

**What is extracted, and from what.** Only what the ingested tables record, deterministically
(`extraction_method = "table_parse"`, confidence 1.0). Every edge carries the evidence ID of the
table cell (or ISA-Tab passage) it was read from:

| Edge | From | Evidence |
|---|---|---|
| experiment `part_of` investigation | `experiment.investigation` | the row's test-ID cell; for a table without one (SPICE), the row's fuel cell |
| experiment `uses_fuel` fuel | `experiment.fuel_or_material` | the fuel / material cell |
| experiment `has_condition` condition_variable | every `experiment_condition` (value on the edge) | that cell |
| experiment `observed` phenomenon | FLEX `test_end` (Extinction, Disruption, Completion) | that cell |
| document `describes` investigation | the NASA ISA-Tab investigation record of the same PSI source | its first passage |

Nothing is inferred: platforms (e.g. the ISS) and links from NTRS reports to investigations are not
in the tables, so they are not extracted (NLP extraction, D1, is not built).

**Rebuilds are idempotent.** IDs are `stable_ulid(type + ":" + canonical name)` for entities and
`stable_ulid(subject|predicate|object|evidence)` for edges. A rebuild keeps human review state and
merges, follows `merged_into`, and deletes only unreviewed `table_parse` edges it no longer produces, and
entities it no longer produces that have no edges, no review and no part in a merge.

**Traversal** is one recursive CTE (`WITH RECURSIVE`, PostgreSQL and SQLite alike), both edge
directions, rejected edges excluded, depth at most 3.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import bindparam, func, or_, select, text, update
from sqlalchemy.orm import Session

from flame_api.ids import new_ulid, stable_ulid
from flame_api.models import (
    AuditEvent, DocumentRecord, EvidenceRecord, ExperimentCondition, ExperimentRecord, KnowledgeEntity,
    KnowledgeRelation,
)

logger = logging.getLogger("flame_api.knowledge_graph")

EXTRACTOR_VERSION = "psi-tables-graph-1.0.0"
METHOD = "table_parse"
ENTITY_TYPES = ("investigation", "experiment", "fuel", "condition_variable", "phenomenon", "document")
PREDICATES = ("part_of", "uses_fuel", "has_condition", "observed", "describes")
MAX_DEPTH = 3
# The columns that name each table's test (ingest._test_id's order), so `part_of` cites the row's own
# identifier cell. SPICE has none (ingest numbers its rows), so its fuel cell stands for the row.
TEST_ID_VARIABLES = ("flex_identifier", "flex_test", "test", "sample_number")
FUEL_VARIABLES = ("fuel", "fuel_sample_material", "material")
OUTCOME_VARIABLE = "test_end"
LOW_CONFIDENCE = 0.5
# Reviewed resolutions of spelling variants the source tables contain (E2-6 §4), applied by every build so
# that every database resolves them the same way. Keys and values are canonical names; the value is the
# spelling with more tests, and the variant becomes its alias. The tables themselves are never edited.
# Approved by the Lead (Anas) on 2026-11-12, from the duplicate-entity check of the committed tables.
CURATED_ALIASES: dict[tuple[str, str], str] = {
    ("fuel", '1/4 black rod'): '1/4" black rod',     # BASS-II: 2 tests vs 12, inch mark missing
    ("fuel", '1/4 clear rod'): '1/4" clear rod',     # BASS-II: 1 test vs 15, inch mark missing
    ("fuel", '3/8"clear rod'): '3/8" clear rod',     # BASS-II: 2 tests vs 5, space missing
    ("fuel", "75% propylene"): "75 % propylene",     # SPICE: 16 tests vs 115, space before %
    # Added 2026-11-13 with the 16 new PSI investigations, by the same rule; pending the Lead's review.
    ("fuel", "100%c2h4"): "100% c2h4",               # ACME BRE: 3 tests vs 15 (BRE, CLD, E-FIELD, SLICE), space missing
}


class GraphError(ValueError):
    pass


def canonical(name: str) -> str:
    """The E2-6 canonical name: lower-cased, whitespace collapsed."""
    return re.sub(r"\s+", " ", name).strip().lower()


def _collision_key(name: str) -> str:
    """Looser than `canonical`, for the duplicate-entity check only: '75 % propylene' ~ '75% propylene'."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def entity_id(entity_type: str, name: str) -> str:
    return stable_ulid(f"{entity_type}:{canonical(name)}")


def relation_id(subject_id: str, predicate: str, object_id: str, evidence_id: str | None) -> str:
    return stable_ulid(f"{subject_id}|{predicate}|{object_id}|{evidence_id or ''}")


def _now() -> datetime:
    return datetime.now(UTC)


class _Builder:
    def __init__(self, session: Session, knowledge_version: str | None) -> None:
        self.session = session
        self.version = knowledge_version
        self.now = _now()
        self.entities: dict[str, KnowledgeEntity] = {e.entity_id: e for e in session.scalars(select(KnowledgeEntity))}
        self.alias_index: dict[tuple[str, str], str] = {}
        for entity in self.entities.values():
            for alias in entity.aliases or []:
                self.alias_index.setdefault((entity.entity_type, canonical(alias)), entity.entity_id)
        self.edges: dict[str, dict[str, Any]] = {}
        self.touched: set[str] = set()
        self.counts: dict[str, int] = defaultdict(int)

    def _winner(self, identifier: str) -> str:
        seen = set()
        while (entity := self.entities.get(identifier)) is not None and entity.merged_into and identifier not in seen:
            seen.add(identifier)
            identifier = entity.merged_into
        return identifier

    def entity(self, entity_type: str, name: str, *, properties: dict | None = None, source_id: str | None = None,
               evidence_ids: list[str] | None = None, alias: str | None = None) -> str:
        """Resolve by curated alias, canonical name, then alias; create when none matches. Returns the live entity ID."""
        curated = CURATED_ALIASES.get((entity_type, canonical(name)))
        if curated is not None:
            # The variant's own spelling stays as an alias; the entity is the reviewed canonical one.
            alias, name = (alias if alias else name), curated
        identifier = entity_id(entity_type, name)
        if identifier not in self.entities and (entity_type, canonical(name)) in self.alias_index:
            identifier = self.alias_index[(entity_type, canonical(name))]
        record = self.entities.get(identifier)
        if record is None:
            # The spelling the source first used, for display; the canonical name is lower-cased.
            display = {"display_name": re.sub(r"\s+", " ", name).strip()} if alias != "" else {}
            record = KnowledgeEntity(
                entity_id=identifier, entity_type=entity_type, canonical_name=canonical(name), aliases=[],
                properties=display, source_id=source_id, evidence_ids=[], review_status="unreviewed",
                knowledge_version=self.version, created_at=self.now, updated_at=self.now,
            )
            self.session.add(record)
            self.entities[identifier] = record
            self.counts[f"entities_created:{entity_type}"] += 1
        identifier = self._winner(identifier)
        self.touched.add(identifier)
        record = self.entities[identifier]
        spelling = alias if alias is not None else name
        if spelling.strip() and canonical(spelling) != record.canonical_name and spelling.strip() not in (record.aliases or []):
            record.aliases = sorted({*(record.aliases or []), spelling.strip()})
            self.alias_index.setdefault((entity_type, canonical(spelling)), identifier)
        if properties:
            merged = {**(record.properties or {}), **properties}
            if merged != record.properties:
                record.properties = merged
        if evidence_ids:
            wanted = sorted({*(record.evidence_ids or []), *evidence_ids})
            if wanted != record.evidence_ids:
                record.evidence_ids = wanted
        record.knowledge_version = self.version
        record.updated_at = self.now
        return identifier

    def edge(self, subject: str, predicate: str, obj: str, evidence_id: str, properties: dict | None = None) -> None:
        subject, obj = self._winner(subject), self._winner(obj)
        identifier = relation_id(subject, predicate, obj, evidence_id)
        self.edges[identifier] = {"relation_id": identifier, "subject_id": subject, "predicate": predicate,
                                  "object_id": obj, "evidence_id": evidence_id, "properties": properties or {}}

    def write_edges(self) -> None:
        # Matched by the natural key, not the ID: an edge re-pointed by a merge keeps its old relation_id.
        existing = {(r.subject_id, r.predicate, r.object_id, r.evidence_id): r for r in self.session.scalars(
            select(KnowledgeRelation).where(KnowledgeRelation.extraction_method == METHOD))}
        for values in self.edges.values():
            record = existing.pop((values["subject_id"], values["predicate"], values["object_id"], values["evidence_id"]), None)
            if record is None:
                self.session.add(KnowledgeRelation(
                    **values, extraction_method=METHOD, extractor_version=EXTRACTOR_VERSION, confidence=1.0,
                    review_status="unreviewed", knowledge_version=self.version, created_at=self.now))
                self.counts["relations_created"] += 1
            else:   # keep review_status: a human decision survives a rebuild
                if record.properties != values["properties"]:
                    record.properties = values["properties"]
                record.extractor_version = EXTRACTOR_VERSION
                record.knowledge_version = self.version
                self.counts["relations_kept"] += 1
        for record in existing.values():
            if record.review_status == "unreviewed":
                self.session.delete(record)
                self.counts["relations_removed"] += 1
            else:
                self.counts["relations_stale_reviewed"] += 1   # flagged by `check` if its evidence is gone

    def drop_stale_entities(self) -> None:
        """Entities this build no longer produces, if nothing still needs them: no edge, no review, no merge."""
        self.session.flush()
        linked = {row for pair in self.session.execute(select(KnowledgeRelation.subject_id, KnowledgeRelation.object_id))
                  for row in pair}
        merge_targets = {e.merged_into for e in self.entities.values() if e.merged_into}
        for identifier, entity in list(self.entities.items()):
            if (identifier in self.touched or identifier in linked or identifier in merge_targets
                    or entity.merged_into or entity.review_status != "unreviewed"):
                continue
            self.session.delete(entity)
            del self.entities[identifier]
            self.counts["entities_removed"] += 1


def _identity_variables(source_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(test-ID variables, fuel variables) for one investigation, from the same column map the table parser uses
    (flame_api.ingest.TEST_ID_COLUMNS / FUEL_COLUMNS, slugged), so the graph and the parser never disagree.
    Investigations without a mapping fall back to the generic TEST_ID_VARIABLES / FUEL_VARIABLES."""
    from flame_api.ingest import FUEL_COLUMNS, TEST_ID_COLUMNS, _slug

    tests = tuple(_slug(c) for c in TEST_ID_COLUMNS.get(source_id, ())) or TEST_ID_VARIABLES
    fuels = tuple(_slug(c) for c in FUEL_COLUMNS.get(source_id, ())) or FUEL_VARIABLES
    return tests, fuels


def build_graph(session: Session, knowledge_version: str | None = None) -> dict[str, int]:
    """(Re)build the table-derived graph from the ingested experiments and ISA-Tab records. Commits."""
    if knowledge_version is None:
        from flame_api.knowledge_version import current_knowledge_version

        knowledge_version = current_knowledge_version(session)
    builder = _Builder(session, knowledge_version)
    experiments = session.scalars(select(ExperimentRecord).order_by(ExperimentRecord.experiment_id)).all()
    conditions: dict[str, list[ExperimentCondition]] = defaultdict(list)
    for condition in session.scalars(select(ExperimentCondition).order_by(ExperimentCondition.condition_id)):
        conditions[condition.experiment_id].append(condition)
    investigations: dict[str, str] = {}
    for experiment in experiments:
        cells = conditions[experiment.experiment_id]
        test_variables, fuel_variables = _identity_variables(experiment.source_id)
        fuel_cell = next((c for c in cells if c.variable in fuel_variables and c.value_text is not None
                          and experiment.fuel_or_material is not None
                          and c.value_text.strip() == experiment.fuel_or_material.strip()), None)
        test_cell = next((c for v in test_variables for c in cells if c.variable == v), None) or fuel_cell
        if not experiment.investigation or test_cell is None:
            builder.counts["experiments_without_investigation_or_test_cell"] += 1
            continue
        investigation = investigations.get(experiment.investigation)
        if investigation is None:
            investigation = builder.entity("investigation", experiment.investigation, source_id=experiment.source_id,
                                           properties={"psi_id": experiment.source_id}, alias=experiment.investigation)
            investigations[experiment.investigation] = investigation
        node = builder.entity(
            "experiment", experiment.experiment_id, source_id=experiment.source_id,
            properties={"experiment_id": experiment.experiment_id, "test_id": experiment.test_id,
                        "investigation": experiment.investigation, "gravity_regime": experiment.gravity_regime},
            evidence_ids=[test_cell.evidence_id], alias="",
        )
        builder.edge(node, "part_of", investigation, test_cell.evidence_id)
        if fuel_cell is not None:
            fuel = builder.entity("fuel", experiment.fuel_or_material, alias=experiment.fuel_or_material)
            builder.edge(node, "uses_fuel", fuel, fuel_cell.evidence_id)
        elif experiment.fuel_or_material:
            builder.counts["fuels_without_a_cell"] += 1
        for cell in cells:
            if cell.variable in test_variables or cell.variable in fuel_variables:
                continue   # already the experiment's identity and its fuel edge
            variable = builder.entity("condition_variable", cell.variable,
                                      properties={"unit_si": cell.unit_si} if cell.unit_si else None)
            builder.edge(node, "has_condition", variable, cell.evidence_id, {
                "value_si": cell.value_si, "unit_si": cell.unit_si, "value_numeric": cell.value_numeric,
                "value_text": cell.value_text, "unit_original": cell.unit_original, "origin": cell.origin,
            })
            if cell.variable == OUTCOME_VARIABLE and cell.value_text and cell.value_text.strip():
                phenomenon = builder.entity("phenomenon", cell.value_text, alias=cell.value_text)
                builder.edge(node, "observed", phenomenon, cell.evidence_id)
    for document in session.scalars(select(DocumentRecord).where(DocumentRecord.document_type == "dataset_documentation")
                                    .order_by(DocumentRecord.document_id)):
        target = next((identifier for name, identifier in investigations.items()
                       if builder.entities[identifier].source_id == document.source_id), None)
        first = session.scalar(select(EvidenceRecord.evidence_id).where(EvidenceRecord.document_id == document.document_id)
                               .order_by(EvidenceRecord.evidence_id).limit(1))
        if target is None or first is None:
            continue
        node = builder.entity("document", document.document_id, source_id=document.source_id,
                              properties={"document_id": document.document_id, "title": document.title},
                              evidence_ids=[first], alias="")
        builder.edge(node, "describes", target, first)
    builder.write_edges()
    builder.drop_stale_entities()
    session.commit()
    counts = dict(builder.counts)
    counts["entities"] = session.scalar(select(func.count()).select_from(KnowledgeEntity)) or 0
    counts["relations"] = session.scalar(select(func.count()).select_from(KnowledgeRelation)) or 0
    logger.info("knowledge_graph_built %s", json.dumps(counts, sort_keys=True))
    return counts


# --- traversal --------------------------------------------------------------------------------------------

_NEIGHBOURHOOD = """
WITH RECURSIVE walk(entity_id, depth) AS (
    SELECT CAST(:start AS TEXT), 0
    UNION
    SELECT CAST(CASE WHEN r.subject_id = walk.entity_id THEN r.object_id ELSE r.subject_id END AS TEXT), walk.depth + 1
    FROM walk
    JOIN knowledge_relation r ON (r.subject_id = walk.entity_id OR r.object_id = walk.entity_id)
    WHERE walk.depth < :depth AND r.review_status <> 'rejected' {predicate_filter}
)
SELECT entity_id, MIN(depth) AS depth FROM walk GROUP BY entity_id
"""


def resolve(session: Session, identifier: str) -> KnowledgeEntity | None:
    """The live entity for an ID, following `merged_into` (old IDs keep resolving after a merge)."""
    seen = set()
    entity = session.get(KnowledgeEntity, identifier)
    while entity is not None and entity.merged_into and entity.entity_id not in seen:
        seen.add(entity.entity_id)
        entity = session.get(KnowledgeEntity, entity.merged_into)
    return entity


def neighbourhood(session: Session, start: str, *, depth: int = 1, predicates: list[str] | None = None,
                  max_edges: int = 200) -> dict[str, Any]:
    """Entities within `depth` hops of `start` (either direction) and the edges among them, nearest first."""
    if not 1 <= depth <= MAX_DEPTH:
        raise GraphError(f"depth must be 1-{MAX_DEPTH}")
    if predicates and any(p not in PREDICATES for p in predicates):
        raise GraphError(f"predicates must be among {', '.join(PREDICATES)}")
    predicate_filter = "AND r.predicate IN :predicates" if predicates else ""
    statement = text(_NEIGHBOURHOOD.format(predicate_filter=predicate_filter))
    params: dict[str, Any] = {"start": start, "depth": depth}
    if predicates:
        statement = statement.bindparams(bindparam("predicates", expanding=True))
        params["predicates"] = list(predicates)
    depths = {row.entity_id: row.depth for row in session.execute(statement, params)}
    query = select(KnowledgeRelation).where(
        KnowledgeRelation.subject_id.in_(depths), KnowledgeRelation.object_id.in_(depths),
        KnowledgeRelation.review_status != "rejected",
    )
    if predicates:
        query = query.where(KnowledgeRelation.predicate.in_(predicates))
    edges = sorted(session.scalars(query),
                   key=lambda r: (max(depths[r.subject_id], depths[r.object_id]), r.predicate, r.relation_id))
    truncated = len(edges) > max_edges
    edges = edges[:max_edges]
    kept = {start} | {r.subject_id for r in edges} | {r.object_id for r in edges}
    entities = sorted(session.scalars(select(KnowledgeEntity).where(KnowledgeEntity.entity_id.in_(kept))),
                      key=lambda e: (depths.get(e.entity_id, 0), e.entity_type, e.canonical_name))
    by_type = dict(session.execute(select(KnowledgeEntity.entity_type, func.count())
                                   .where(KnowledgeEntity.entity_id.in_(depths)).group_by(KnowledgeEntity.entity_type)).all())
    return {"entities": entities, "depths": depths, "edges": edges, "truncated": truncated,
            "reachable_entities": len(depths), "reachable_by_type": by_type}


# --- consistency (E2-6 §5) ---------------------------------------------------------------------------------

def check_consistency(session: Session, *, sample: int = 20) -> dict[str, Any]:
    """The five E2-6 checks. Each returns a count and up to `sample` examples."""
    results: dict[str, Any] = {}

    def record(name: str, rows: list[dict[str, Any]], *, blocking: bool) -> None:
        results[name] = {"count": len(rows), "blocking": blocking, "examples": rows[:sample]}

    live = select(KnowledgeEntity.entity_id).where(KnowledgeEntity.merged_into.is_(None))
    orphans = session.execute(select(KnowledgeRelation.relation_id, KnowledgeRelation.subject_id, KnowledgeRelation.object_id)
                              .where(or_(KnowledgeRelation.subject_id.notin_(live), KnowledgeRelation.object_id.notin_(live)))).all()
    record("orphan_edges", [dict(r._mapping) for r in orphans], blocking=True)

    dead = session.execute(select(KnowledgeRelation.relation_id, KnowledgeRelation.evidence_id)
                           .where(KnowledgeRelation.evidence_id.is_not(None),
                                  KnowledgeRelation.evidence_id.notin_(select(EvidenceRecord.evidence_id)))).all()
    unsupported = session.execute(select(KnowledgeRelation.relation_id, KnowledgeRelation.extraction_method)
                                  .where(KnowledgeRelation.evidence_id.is_(None), KnowledgeRelation.extraction_method != "manual")).all()
    record("edges_with_dead_evidence", [dict(r._mapping) for r in dead] + [dict(r._mapping) for r in unsupported], blocking=True)

    groups: dict[tuple[str, str], list[KnowledgeEntity]] = defaultdict(list)
    for entity in session.scalars(select(KnowledgeEntity).where(KnowledgeEntity.merged_into.is_(None))):
        if entity.entity_type in {"experiment", "document"}:
            continue   # identified by their own IDs
        keys = {_collision_key(entity.canonical_name), *(_collision_key(a) for a in entity.aliases or [])}
        for key in keys - {""}:
            groups[(entity.entity_type, key)].append(entity)
    duplicates, seen = [], set()
    for (entity_type, key), members in sorted(groups.items()):
        ids = tuple(sorted({m.entity_id for m in members}))
        if len(ids) > 1 and ids not in seen:
            seen.add(ids)
            duplicates.append({"entity_type": entity_type, "collision_key": key,
                               "entities": [{"entity_id": m.entity_id, "canonical_name": m.canonical_name}
                                            for m in sorted({m.entity_id: m for m in members}.values(), key=lambda m: m.entity_id)]})
    # A candidate for a human merge, not an error: the tables really do spell some names differently.
    record("duplicate_entities", duplicates, blocking=False)

    conflicts = []
    values: dict[tuple[str, str], dict[float, str]] = defaultdict(dict)
    for relation in session.scalars(select(KnowledgeRelation).where(KnowledgeRelation.predicate == "has_condition",
                                                                    KnowledgeRelation.review_status != "rejected")):
        value = (relation.properties or {}).get("value_si")
        if value is not None:
            values[(relation.subject_id, relation.object_id)].setdefault(float(value), relation.evidence_id)
    for (subject, variable), by_value in sorted(values.items()):
        if len(by_value) > 1:
            conflicts.append({"experiment": subject, "condition_variable": variable,
                              "values": [{"value_si": v, "evidence_id": e} for v, e in sorted(by_value.items())]})
    record("conflicting_relations", conflicts, blocking=True)

    low = session.execute(select(KnowledgeRelation.relation_id, KnowledgeRelation.confidence)
                          .where(KnowledgeRelation.confidence < LOW_CONFIDENCE, KnowledgeRelation.review_status == "unreviewed")).all()
    record("unreviewed_low_confidence_edges", [dict(r._mapping) for r in low], blocking=False)

    results["ok"] = not any(item["count"] for item in results.values() if isinstance(item, dict) and item["blocking"])
    return results


# --- merge (E2-6 §4) ---------------------------------------------------------------------------------------

def merge_entities(session: Session, loser_id: str, winner_id: str, *, actor: str, request_id: str | None = None) -> AuditEvent:
    """Merge `loser` into `winner` in one transaction: re-point edges, keep the loser row, audit it."""
    loser, winner = session.get(KnowledgeEntity, loser_id), resolve(session, winner_id)
    if loser is None or winner is None:
        raise GraphError("Both entities must exist.")
    if loser.merged_into:
        raise GraphError(f"{loser_id} is already merged into {loser.merged_into}.")
    if loser.entity_id == winner.entity_id or loser.entity_type != winner.entity_type:
        raise GraphError("Only two different entities of the same type can be merged.")
    moved = dropped = 0
    winner_edges = {(r.subject_id, r.predicate, r.object_id, r.evidence_id) for r in session.scalars(
        select(KnowledgeRelation).where(or_(KnowledgeRelation.subject_id == winner.entity_id,
                                            KnowledgeRelation.object_id == winner.entity_id)))}
    for relation in list(session.scalars(select(KnowledgeRelation).where(
            or_(KnowledgeRelation.subject_id == loser.entity_id, KnowledgeRelation.object_id == loser.entity_id)))):
        subject = winner.entity_id if relation.subject_id == loser.entity_id else relation.subject_id
        obj = winner.entity_id if relation.object_id == loser.entity_id else relation.object_id
        key = (subject, relation.predicate, obj, relation.evidence_id)
        if key in winner_edges:
            session.delete(relation)   # the winner already has this exact edge
            dropped += 1
            continue
        session.execute(update(KnowledgeRelation).where(KnowledgeRelation.relation_id == relation.relation_id)
                        .values(subject_id=subject, object_id=obj))
        winner_edges.add(key)
        moved += 1
    before = {"loser": {"canonical_name": loser.canonical_name, "aliases": loser.aliases, "merged_into": None},
              "winner": {"canonical_name": winner.canonical_name, "aliases": winner.aliases}}
    winner.aliases = sorted({*(winner.aliases or []), loser.canonical_name, *(loser.aliases or [])} - {winner.canonical_name})
    winner.evidence_ids = sorted({*(winner.evidence_ids or []), *(loser.evidence_ids or [])})
    winner.updated_at = loser.updated_at = _now()
    loser.merged_into = winner.entity_id
    event = AuditEvent(
        event_id=new_ulid(), occurred_at=_now(), actor=actor, action="graph.entity.merge", target_type="knowledge_entity",
        target_id=loser.entity_id, before=before,
        after={"merged_into": winner.entity_id, "winner_aliases": winner.aliases, "edges_moved": moved,
               "duplicate_edges_dropped": dropped},
        request_id=request_id,
    )
    session.add(event)
    session.commit()
    return event


def main(argv: list[str]) -> int:
    from flame_api.database import SessionLocal

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="python -m flame_api.knowledge_graph", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help="(re)build the table-derived graph")
    commands.add_parser("check", help="run the consistency checks; exit 1 when a blocking check fails")
    merge = commands.add_parser("merge", help="merge LOSER into WINNER (audited)")
    merge.add_argument("loser")
    merge.add_argument("winner")
    merge.add_argument("--actor", required=True, help="who decided the merge (recorded in audit_event)")
    args = parser.parse_args(argv)
    with SessionLocal() as session:
        if args.command == "build":
            print(json.dumps(build_graph(session), sort_keys=True))
            return 0
        if args.command == "check":
            report = check_consistency(session)
            print(json.dumps(report, sort_keys=True, default=str))
            return 0 if report["ok"] else 1
        try:
            event = merge_entities(session, args.loser, args.winner, actor=args.actor)
        except GraphError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        print(json.dumps({"event_id": event.event_id, **(event.after or {})}, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
