"""Transactional SQLite storage with append-only observations and optimistic edits."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import json
from threading import RLock
from typing import Protocol
from src.domain.models import CatalogEntry, Dataset, Observation, Product


class ConflictError(ValueError):
    """Existing data or a concurrent edit prevents the requested mutation."""


class Repository(Protocol):
    def snapshot(self) -> tuple[list[CatalogEntry], list[Observation]]: ...
    def import_dataset(self, dataset: Dataset, max_products: int | None = None) -> None: ...
    def save_product(self, product: Product, expected_version: int = 0) -> CatalogEntry: ...
    def add_observation(self, observation: Observation, *, expected_product_version: int | None = None, allow_existing: bool = False) -> None: ...
    def audit_log(self, limit: int = 100) -> list[dict]: ...
    def save_review(self, brief: dict, outcome: str, reason: str) -> dict: ...
    def reviews(self) -> list[dict]: ...
    def save_advisory_plan(self, plan_id: str, report: dict) -> dict: ...
    def advisory_plans(self) -> list[dict]: ...
    def advisory_plan(self, plan_id: str) -> dict | None: ...
    def transition_advisory(self, plan_id, expected, status, *, start=None, outcome=None, result=None) -> dict: ...


class SQLiteRepository:
    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False, timeout=10)
        version = self._connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 3:
            self._connection.close()
            raise ValueError("Database schema is newer than this application supports.")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY, payload TEXT NOT NULL, version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS observations (
                observation_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(product_id),
                observed_on TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS observations_product_date ON observations(product_id, observed_on);
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY, recorded_at TEXT NOT NULL, event TEXT NOT NULL,
                entity_id TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS decision_reviews (
                id INTEGER PRIMARY KEY, recorded_at TEXT NOT NULL,
                product_id TEXT NOT NULL REFERENCES products(product_id),
                fingerprint TEXT NOT NULL, outcome TEXT NOT NULL, reason TEXT NOT NULL, snapshot TEXT NOT NULL,
                UNIQUE(fingerprint,outcome,reason));
            CREATE TABLE IF NOT EXISTS advisory_plans (
                id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, status TEXT NOT NULL,
                report TEXT NOT NULL, start_record TEXT, outcome TEXT, result TEXT);
            PRAGMA user_version=3;
        """)

    def _audit(self, event: str, entity_id: str, payload: str):
        self._connection.execute("INSERT INTO audit(recorded_at,event,entity_id,payload) VALUES(?,?,?,?)",
                                 (datetime.now(timezone.utc).isoformat(), event, entity_id, payload))

    def snapshot(self) -> tuple[list[CatalogEntry], list[Observation]]:
        with self._lock, self._connection:
            self._connection.execute("BEGIN")
            products = [CatalogEntry(product=Product.model_validate_json(payload), version=version)
                        for payload, version in self._connection.execute("SELECT payload,version FROM products ORDER BY product_id")]
            observations = [Observation.model_validate_json(row[0]) for row in
                            self._connection.execute("SELECT payload FROM observations ORDER BY observed_on,rowid")]
            return products, observations

    def import_dataset(self, dataset: Dataset, max_products: int | None = None) -> None:
        """Insert a whole validated batch or nothing; never replace existing records."""
        with self._lock, self._connection:
            try:
                if max_products is not None:
                    self._connection.execute("BEGIN IMMEDIATE")
                    count = self._connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
                    if count + len(dataset.products) > max_products:
                        raise ConflictError("This import exceeds the 1,000-product demo limit; no records were changed")
                    existing = {row[0].casefold() for row in self._connection.execute("SELECT product_id FROM products")}
                    incoming = [p.product_id.casefold() for p in dataset.products]
                    if existing.intersection(incoming) or len(set(incoming)) != len(incoming):
                        raise ConflictError("An SKU already exists, ignoring case; no records were changed")
                for product in dataset.products:
                    self._connection.execute("INSERT INTO products VALUES(?,?,1)",
                                             (product.product_id, product.model_dump_json()))
                for observation in dataset.observations:
                    self._connection.execute("INSERT INTO observations VALUES(?,?,?,?)", (
                        observation.observation_id, observation.product_id, observation.observed_on.isoformat(),
                        observation.model_dump_json()))
                self._audit("dataset_imported", dataset.name, dataset.model_dump_json())
            except sqlite3.IntegrityError as exc:
                raise ConflictError("Import conflicts with existing IDs; no records were changed.") from exc

    def save_product(self, product: Product, expected_version: int = 0) -> CatalogEntry:
        with self._lock, self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if expected_version == 0:
                ids = [row[0] for row in self._connection.execute("SELECT product_id FROM products")]
                if len(ids) >= 1000:
                    raise ConflictError("This workspace has reached the 1,000-product limit")
                if product.product_id.casefold() in {pid.casefold() for pid in ids}:
                    raise ConflictError("Product already exists, ignoring case; reload before editing")
                try:
                    self._connection.execute("INSERT INTO products VALUES(?,?,1)",
                                             (product.product_id, product.model_dump_json()))
                except sqlite3.IntegrityError as exc:
                    raise ConflictError("Product already exists; reload its version before editing.") from exc
            else:
                old = self._connection.execute("SELECT payload FROM products WHERE product_id=?", (product.product_id,)).fetchone()
                if old:
                    previous = Product.model_validate_json(old[0])
                    if previous.retail:
                        if not product.retail or previous.data_origin != product.data_origin:
                            raise ConflictError("Preserve this product's retail cost detail and data origin")
                        identity = (previous.retail.gtin,previous.retail.variant)
                        changed = identity != (product.retail.gtin,product.retail.variant)
                        evidence = self._connection.execute("SELECT 1 FROM observations WHERE product_id=? LIMIT 1", (product.product_id,)).fetchone()
                        if changed and evidence:
                            raise ConflictError("This SKU has market evidence; use a new SKU for a different variant or GTIN")
                result = self._connection.execute(
                    "UPDATE products SET payload=?, version=version+1 WHERE product_id=? AND version=?",
                    (product.model_dump_json(), product.product_id, expected_version))
                if result.rowcount != 1:
                    raise ConflictError("Product changed or was not found; reload before saving.")
            self._audit("product_saved", product.product_id, product.model_dump_json())
        return CatalogEntry(product=product, version=expected_version + 1)

    def add_observation(self, observation: Observation, *, expected_product_version: int | None = None, allow_existing: bool = False) -> None:
        with self._lock, self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if expected_product_version is not None:
                version = self._connection.execute("SELECT version FROM products WHERE product_id=?", (observation.product_id,)).fetchone()
                if version != (expected_product_version,):
                    raise ConflictError("Product inputs changed during collection; review the product and refresh again")
            if allow_existing:
                existing = self._connection.execute("SELECT payload FROM observations WHERE observation_id=?", (observation.observation_id,)).fetchone()
                if existing and Observation.model_validate_json(existing[0]) == observation:
                    return
            try:
                self._connection.execute("INSERT INTO observations VALUES(?,?,?,?)", (
                    observation.observation_id, observation.product_id, observation.observed_on.isoformat(),
                    observation.model_dump_json()))
            except sqlite3.IntegrityError as exc:
                raise ConflictError("Observation ID exists or product is unknown.") from exc
            self._audit("observation_added", observation.observation_id, observation.model_dump_json())

    def audit_log(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id,recorded_at,event,entity_id FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(zip(("id", "recorded_at", "event", "entity_id"), row)) for row in rows]

    def close(self):
        with self._lock:
            self._connection.close()

    def save_review(self, brief: dict, outcome: str, reason: str) -> dict:
        """Commit the decision and its evidence only if the read snapshot is current."""
        with self._lock, self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            product_id = brief["product_id"]
            version = self._connection.execute("SELECT version FROM products WHERE product_id=?", (product_id,)).fetchone()
            current_ids = {r[0] for r in self._connection.execute(
                "SELECT observation_id FROM observations WHERE product_id=?", (product_id,))}
            original_ids = {o["observation_id"] for o in brief["snapshot"]["observations"]}
            if version != (brief["product_version"],) or current_ids != original_ids:
                raise ConflictError("Inputs changed during review; refresh before recording your decision")
            existing = self._connection.execute(
                "SELECT id,recorded_at FROM decision_reviews WHERE fingerprint=? AND outcome=? AND reason=?",
                (brief["fingerprint"], outcome, reason)).fetchone()
            if existing:
                return {"id": existing[0], "recorded_at": existing[1], "outcome": outcome, "published": False}
            if self._connection.execute("SELECT COUNT(*) FROM decision_reviews").fetchone()[0] >= 250:
                raise ConflictError("Review log has reached the MVP limit of 250 entries; export it before resetting")
            now = datetime.now(timezone.utc).isoformat()
            row = self._connection.execute(
                "INSERT INTO decision_reviews(recorded_at,product_id,fingerprint,outcome,reason,snapshot) VALUES(?,?,?,?,?,?)",
                (now, product_id, brief["fingerprint"], outcome, reason, json.dumps(brief)))
            self._audit("decision_reviewed", product_id, json.dumps({"review_id": row.lastrowid, "outcome": outcome}))
            return {"id": row.lastrowid, "recorded_at": now, "outcome": outcome, "published": False}

    def reviews(self) -> list[dict]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id,recorded_at,product_id,fingerprint,outcome,reason,snapshot FROM decision_reviews ORDER BY id DESC").fetchall()
        return [{"id": r[0], "recorded_at": r[1], "product_id": r[2], "fingerprint": r[3],
                 "outcome": r[4], "reason": r[5], "brief": json.loads(r[6]), "published": False} for r in rows]

    def save_advisory_plan(self, plan_id: str, report: dict) -> dict:
        with self._lock, self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            existing = self._advisory_plan(plan_id)
            if existing:
                if existing["report"]["fingerprint"] != report["fingerprint"]:
                    raise ConflictError("This request ID already belongs to a different consultation")
                return existing
            source = report["source_snapshot"]
            if source["product_id"]:
                version = self._connection.execute("SELECT version FROM products WHERE product_id=?", (source["product_id"],)).fetchone()
                ids = sorted(r[0] for r in self._connection.execute("SELECT observation_id FROM observations WHERE product_id=?", (source["product_id"],)))
                if version != (source["product_version"],) or ids != source["observation_ids"]:
                    raise ConflictError("Evidence changed while saving; refresh the consultation")
            if self._connection.execute("SELECT COUNT(*) FROM advisory_plans").fetchone()[0] >= 250:
                raise ConflictError("The workspace has reached 250 plans. Export before resetting.")
            now = datetime.now(timezone.utc).isoformat()
            self._connection.execute("INSERT INTO advisory_plans(id,recorded_at,status,report) VALUES(?,?,?,?)",
                                     (plan_id, now, "planned", json.dumps(report)))
            self._audit("consultation_saved", plan_id, json.dumps({"fingerprint": report["fingerprint"]}))
            return self._advisory_plan(plan_id)

    def _advisory_plan(self, plan_id):
        row = self._connection.execute("SELECT id,recorded_at,status,report,start_record,outcome,result FROM advisory_plans WHERE id=?", (plan_id,)).fetchone()
        if not row:
            return None
        return dict(id=row[0], recorded_at=row[1], status=row[2], report=json.loads(row[3]),
                    start=json.loads(row[4]) if row[4] else None, outcome=json.loads(row[5]) if row[5] else None,
                    result=json.loads(row[6]) if row[6] else None, published=False)

    def advisory_plans(self):
        with self._lock:
            ids = [r[0] for r in self._connection.execute("SELECT id FROM advisory_plans ORDER BY recorded_at DESC")]
            return [self._advisory_plan(i) for i in ids]

    def advisory_plan(self, plan_id):
        with self._lock:
            return self._advisory_plan(plan_id)

    def transition_advisory(self, plan_id, expected, status, *, start=None, outcome=None, result=None):
        with self._lock, self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if expected == "planned" and status == "active":
                plan = self._advisory_plan(plan_id)
                source = plan["report"]["source_snapshot"] if plan else {}
                if source.get("product_id"):
                    active = self._connection.execute("SELECT report FROM advisory_plans WHERE status='active'").fetchall()
                    if any(json.loads(row[0])["source_snapshot"].get("product_id") == source["product_id"] for row in active):
                        raise ConflictError("This SKU already has an active trial; record its outcome before starting another")
                    version = self._connection.execute("SELECT version FROM products WHERE product_id=?", (source["product_id"],)).fetchone()
                    ids = sorted(r[0] for r in self._connection.execute("SELECT observation_id FROM observations WHERE product_id=?", (source["product_id"],)))
                    if version != (source["product_version"],) or ids != source["observation_ids"]:
                        raise ConflictError("Product inputs or market evidence changed after planning; review a fresh consultation before starting")
            row = self._connection.execute("UPDATE advisory_plans SET status=?,start_record=COALESCE(?,start_record),outcome=?,result=? WHERE id=? AND status=?",
                (status, json.dumps(start) if start else None, json.dumps(outcome) if outcome else None,
                 json.dumps(result) if result else None, plan_id, expected))
            if row.rowcount != 1:
                raise ConflictError("This plan changed; reload its current state")
            self._audit("consultation_" + status, plan_id, json.dumps({"outcome":outcome,"result":result} if outcome else result or start))
            return self._advisory_plan(plan_id)
