from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
METRICS = ROOT / "execution_outputs" / "V3_M13_DEVELOPMENT_UNIT_METRICS.csv"
SCHEMA = ROOT / "frozen_inputs" / "V3_M13_PROTECTED_CONCEPT_SCHEMA_FROZEN_COPY_2026-08-08.json"
OUT = ROOT / "blind_audit"
KEY_DIR = ROOT / "sealed_key_DO_NOT_OPEN_BEFORE_AUDIT"
SELECTION_SEED = 20260809
BLINDING_SEED = 20260810
MODELS = ("B1", "B2", "B3")
STRATUM_SIZE = 10


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^\w\s']+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> set[str]:
    return set(norm(text).split())


def jaccard_distance(a: str, b: str) -> float:
    aa, bb = tokens(a), tokens(b)
    if not aa and not bb:
        return 0.0
    return 1.0 - len(aa & bb) / max(1, len(aa | bb))


def safe_float(value: str | None) -> float:
    try:
        return float(value) if value not in (None, "") else math.nan
    except ValueError:
        return math.nan


def phrase_present(text: str, phrase: str) -> bool:
    normalized = f" {norm(text)} "
    target = f" {norm(phrase)} "
    return target in normalized


def source_protected_categories(source: str, schema: dict) -> list[str]:
    categories: list[str] = []
    skip = {"utterance_force"}
    for category, groups in schema["english_values"].items():
        if category in skip:
            continue
        hit = False
        for phrases in groups.values():
            if any(phrase_present(source, p) for p in phrases):
                hit = True
                break
        if hit:
            categories.append(category)
    if re.search(schema["number_regex"], norm(source)):
        categories.append("number")
    if any(phrase_present(source, p) for p in schema["temporal_english"]):
        categories.append("temporal")
    return sorted(set(categories))


def read_rows() -> list[dict]:
    with METRICS.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    wanted = [r for r in rows if r["candidate_id"] in MODELS]
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in wanted:
        grouped[row["eval_unit_id"]][row["candidate_id"]] = row
    units: list[dict] = []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for unit_id, model_rows in grouped.items():
        if any(m not in model_rows for m in MODELS):
            continue
        anchor = model_rows["B1"]
        outputs = {m: model_rows[m]["translation_twi"] for m in MODELS}
        pairwise = [
            jaccard_distance(outputs["B1"], outputs["B2"]),
            jaccard_distance(outputs["B1"], outputs["B3"]),
            jaccard_distance(outputs["B2"], outputs["B3"]),
        ]
        recalls = [safe_float(model_rows[m]["best_protected_recall"]) for m in MODELS]
        finite_recalls = [v for v in recalls if not math.isnan(v)]
        recall_range = max(finite_recalls) - min(finite_recalls) if finite_recalls else 0.0
        source = anchor["source_english"]
        units.append(
            {
                "eval_unit_id": unit_id,
                "original_content_group_id": anchor["original_content_group_id"],
                "source_english": source,
                "is_question": anchor["is_question"].lower() == "true",
                "outputs": outputs,
                "protected_categories": source_protected_categories(source, schema),
                "protected_recall_range": recall_range,
                "mean_pairwise_jaccard_distance": sum(pairwise) / len(pairwise),
                "max_pairwise_jaccard_distance": max(pairwise),
                "automatic": {
                    m: {
                        "chrf_pp": safe_float(model_rows[m]["best_sentence_chrf_pp"]),
                        "token_f1": safe_float(model_rows[m]["best_token_f1"]),
                        "protected_recall": safe_float(model_rows[m]["best_protected_recall"]),
                    }
                    for m in MODELS
                },
            }
        )
    return units


def select_units(units: list[dict]) -> list[dict]:
    selected: list[dict] = []
    used: set[str] = set()

    protected = [u for u in units if u["protected_categories"]]
    protected.sort(
        key=lambda u: (
            u["protected_recall_range"],
            len(u["protected_categories"]),
            u["mean_pairwise_jaccard_distance"],
            u["eval_unit_id"],
        ),
        reverse=True,
    )
    for unit in protected[:STRATUM_SIZE]:
        unit["audit_stratum"] = "PROTECTED_CONCEPT_CHALLENGE"
        selected.append(unit)
        used.add(unit["eval_unit_id"])

    remaining = [u for u in units if u["eval_unit_id"] not in used]
    remaining.sort(
        key=lambda u: (u["mean_pairwise_jaccard_distance"], u["max_pairwise_jaccard_distance"], u["eval_unit_id"]),
        reverse=True,
    )
    for unit in remaining[:STRATUM_SIZE]:
        unit["audit_stratum"] = "MODEL_DISAGREEMENT_CHALLENGE"
        selected.append(unit)
        used.add(unit["eval_unit_id"])

    pool = [u for u in units if u["eval_unit_id"] not in used]
    rng = random.Random(SELECTION_SEED)
    questions = [u for u in pool if u["is_question"]]
    statements = [u for u in pool if not u["is_question"]]
    rng.shuffle(questions)
    rng.shuffle(statements)
    target_questions = STRATUM_SIZE // 2
    random_sample = questions[:target_questions] + statements[: STRATUM_SIZE - target_questions]
    rng.shuffle(random_sample)
    for unit in random_sample:
        unit["audit_stratum"] = "REPRESENTATIVE_RANDOM"
        selected.append(unit)
        used.add(unit["eval_unit_id"])

    if len(selected) != STRATUM_SIZE * 3:
        raise RuntimeError(f"Expected {STRATUM_SIZE * 3} audit units, found {len(selected)}")
    return selected


def make_blind_rows(selected: list[dict]) -> tuple[list[dict], list[dict]]:
    ordering_rng = random.Random(BLINDING_SEED)
    ordering_rng.shuffle(selected)
    blind_rows: list[dict] = []
    key_rows: list[dict] = []
    for index, unit in enumerate(selected, start=1):
        models = list(MODELS)
        ordering_rng.shuffle(models)
        code_to_model = dict(zip(("A", "B", "C"), models))
        audit_id = f"M13-AUD-{index:03d}"
        blind_rows.append(
            {
                "audit_id": audit_id,
                "source_english": unit["source_english"],
                "candidate_a_twi": unit["outputs"][code_to_model["A"]],
                "candidate_b_twi": unit["outputs"][code_to_model["B"]],
                "candidate_c_twi": unit["outputs"][code_to_model["C"]],
            }
        )
        key_rows.append(
            {
                "audit_id": audit_id,
                "eval_unit_id": unit["eval_unit_id"],
                "original_content_group_id": unit["original_content_group_id"],
                "audit_stratum": unit["audit_stratum"],
                "is_question": unit["is_question"],
                "protected_categories": unit["protected_categories"],
                "mean_pairwise_jaccard_distance": unit["mean_pairwise_jaccard_distance"],
                "protected_recall_range": unit["protected_recall_range"],
                "candidate_a_model": code_to_model["A"],
                "candidate_b_model": code_to_model["B"],
                "candidate_c_model": code_to_model["C"],
                "automatic": unit["automatic"],
            }
        )
    return blind_rows, key_rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    units = read_rows()
    selected = select_units(units)
    blind_rows, key_rows = make_blind_rows(selected)

    blind_path = OUT / "V3_M13_BLIND_AUDIT_ROWS_30.csv"
    key_path = KEY_DIR / "V3_M13_UNBLINDING_KEY_DO_NOT_OPEN.json"
    write_csv(
        blind_path,
        blind_rows,
        ["audit_id", "source_english", "candidate_a_twi", "candidate_b_twi", "candidate_c_twi"],
    )
    key_payload = {
        "artifact": "v3_m13_sealed_unblinding_key_v1",
        "protocol_id": "rnmt-sbllm-v3-m13-reverse-mt-blind-audit-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_seed": SELECTION_SEED,
        "blinding_seed": BLINDING_SEED,
        "models": list(MODELS),
        "audit_rows": key_rows,
        "human_outcomes_read": False,
        "sealed_test_opened": False,
        "production_changed": False,
    }
    key_path.write_text(json.dumps(key_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "artifact": "v3_m13_blind_audit_precommit_v1",
        "protocol_id": "rnmt-sbllm-v3-m13-reverse-mt-blind-audit-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit_row_count": len(blind_rows),
        "development_population_units": len(units),
        "strata": {
            "PROTECTED_CONCEPT_CHALLENGE": STRATUM_SIZE,
            "MODEL_DISAGREEMENT_CHALLENGE": STRATUM_SIZE,
            "REPRESENTATIVE_RANDOM": STRATUM_SIZE,
        },
        "selection_seed": SELECTION_SEED,
        "blinding_seed": BLINDING_SEED,
        "candidate_set": list(MODELS),
        "anchor": "B1",
        "blind_rows_sha256": sha256(blind_path),
        "sealed_key_sha256": sha256(key_path),
        "sealed_key_relative_path": "sealed_key_DO_NOT_OPEN_BEFORE_AUDIT/V3_M13_UNBLINDING_KEY_DO_NOT_OPEN.json",
        "sealed_test_opened": False,
        "human_outcomes_read": False,
        "production_changed": False,
        "claim_boundary": "Development-only, difficulty-enriched single-expert blind audit; not population prevalence, clinical validation, or sealed-test evidence.",
    }
    manifest_path = OUT / "V3_M13_BLIND_AUDIT_PRECOMMIT.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
