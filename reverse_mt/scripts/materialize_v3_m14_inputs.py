from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
RAW = ROOT / "frozen_source" / "V3_M14_V3M10_RESPONSE_SOURCE_RAW.csv"
V3M10_INPUTS = WORKSPACE / "work_products" / "nllb_v3_m10_end_to_end" / "frozen_inputs" / "V3_M10_72_CASE_END_TO_END_INPUTS_2026-08-07.csv"
V3M10_LEDGER = WORKSPACE / "work_products" / "nllb_v3_m10_postreview" / "V3_M10_POSTREVEAL_JOINED_72_CASE_ANALYSIS_LEDGER_2026-08-08.csv"
SCHEMA = WORKSPACE / "work_products" / "nllb_v3_m13_reverse_mt_benchmark" / "frozen_inputs" / "V3_M13_PROTECTED_CONCEPT_SCHEMA_FROZEN_COPY_2026-08-08.json"
OUT = ROOT / "frozen_inputs" / "V3_M14_72_CASE_REVERSE_MT_INPUTS_2026-08-09.csv"
MANIFEST = ROOT / "frozen_inputs" / "V3_M14_72_CASE_INPUT_MANIFEST_2026-08-09.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^\w\s'.?-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def phrase_present(text: str, phrase: str) -> bool:
    return f" {norm(phrase)} " in f" {norm(text)} "


def protected_categories(text: str, schema: dict) -> list[str]:
    categories: list[str] = []
    for category, groups in schema["english_values"].items():
        if category == "utterance_force":
            continue
        if any(phrase_present(text, phrase) for phrases in groups.values() for phrase in phrases):
            categories.append(category)
    if re.search(schema["number_regex"], norm(text)):
        categories.append("number")
    if any(phrase_present(text, phrase) for phrase in schema["temporal_english"]):
        categories.append("temporal")
    return sorted(set(categories))


def main() -> None:
    raw = pd.read_csv(RAW, dtype=str).fillna("")
    inputs = pd.read_csv(V3M10_INPUTS, dtype=str).fillna("")
    ledger = pd.read_csv(V3M10_LEDGER, dtype=str).fillna("")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert len(raw) == len(inputs) == len(ledger) == 72
    assert raw["review_id"].nunique() == inputs["review_id"].nunique() == ledger["review_id"].nunique() == 72
    joined = inputs.merge(raw, on="review_id", validate="one_to_one").merge(
        ledger[[
            "review_id", "e1_side", "e1_intent", "e1_safety", "e1_groundedness",
            "e1_disposition", "e1_harmful_or_critical", "e1_critical",
            "e1_semantic_redirection", "e1_unsupported",
        ]], on="review_id", validate="one_to_one"
    )

    rows: list[dict] = []
    for index, row in joined.sort_values("review_id").reset_index(drop=True).iterrows():
        side = row["e1_side"].strip().upper()
        assert side in {"A", "B"}
        prefix = "candidate_a" if side == "A" else "candidate_b"
        response_english = row[f"{prefix}_response_english"].replace("\\n", "\n").strip()
        previous_twi = row[f"{prefix}_response_twi"].replace("\\n", "\n").strip()
        disposition = row[f"{prefix}_disposition"].strip()
        assert response_english and previous_twi and disposition
        assert disposition == row["e1_disposition"].strip()
        upstream_ok = (
            row["e1_intent"] in {"INTENT_PRESERVED", "PARTIAL_NONCRITICAL"}
            and row["e1_safety"] in {"SAFE", "LOW_RISK"}
            and row["e1_groundedness"] in {"SUPPORTED", "PARTIAL"}
        )
        concept_text = " ".join([
            row["validated_english_reference"], row["d1_english"], response_english
        ])
        categories = protected_categories(concept_text, schema)
        record = {
            "audit_id": f"M14-AUD-{index + 1:03d}",
            "v3m10_review_id": row["review_id"],
            "record_uid": row["record_uid"],
            "content_group_id": row["content_group_id"],
            "speaker_code": row["speaker_code"],
            "theme_key": row["theme_key"],
            "challenge_stratum": row["challenge_stratum"],
            "validated_gold_akan": row["validated_gold_akan"],
            "validated_english_reference": row["validated_english_reference"],
            "adapted_mms_twi": row["d1_adapted_mms_twi"],
            "adapted_mms_forward_english": row["d1_english"],
            "sbllm_response_english": response_english,
            "sbllm_disposition": disposition,
            "protected_categories": ";".join(categories),
            "protected_case": bool(categories),
            "v3m10_e1_upstream_intent": row["e1_intent"],
            "v3m10_e1_upstream_response_safety": row["e1_safety"],
            "v3m10_e1_upstream_groundedness": row["e1_groundedness"],
            "upstream_english_useful_safe": upstream_ok,
            "v3m10_e1_previous_reverse_twi": previous_twi,
            "mandatory_pattern_probe": row["content_group_id"] == "CG03172",
            "source_row_sha256": hashlib.sha256(
                (row["review_id"] + "|" + response_english + "|" + disposition).encode("utf-8")
            ).hexdigest().upper(),
        }
        rows.append(record)

    output = pd.DataFrame(rows)
    assert len(output) == 72 and output["audit_id"].nunique() == 72
    assert output["sbllm_response_english"].str.strip().ne("").all()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUT, index=False, encoding="utf-8", lineterminator="\n")

    manifest = {
        "artifact": "v3_m14_72_case_input_manifest_v1",
        "protocol_id": "rnmt-sbllm-v3-m14-end-to-end-reverse-mt-gate-v1",
        "frozen_date": "2026-08-09",
        "rows": 72,
        "unit": "one previously frozen V3-M10 adapted-MMS/E1 content group",
        "source_system": "V3-M10 E1 adapted MMS -> unchanged RNMT -> frozen SBLLM English response",
        "response_selection": "exact E1 response arm recovered by the frozen V3-M10 reveal mapping",
        "speaker_counts": output["speaker_code"].value_counts().sort_index().to_dict(),
        "challenge_stratum_counts": output["challenge_stratum"].value_counts().sort_index().to_dict(),
        "protected_case_count": int(output["protected_case"].sum()),
        "upstream_english_useful_safe_count": int(output["upstream_english_useful_safe"].sum()),
        "mandatory_pattern_probe": {
            "content_group_id": "CG03172",
            "reason": "V3-M13 B3-only semantic-redirection source group; carried into V3-M14 when present in the 72-case E1 cohort",
            "included": bool(output["mandatory_pattern_probe"].any()),
        },
        "sha256": {
            "raw_completed_v3m10_response_extract": sha256(RAW),
            "v3m10_frozen_input_ledger": sha256(V3M10_INPUTS),
            "v3m10_postreview_ledger": sha256(V3M10_LEDGER),
            "protected_concept_schema": sha256(SCHEMA),
            "v3m14_frozen_input_ledger": sha256(OUT),
        },
        "claim_boundary": "Development-only, challenge-enriched, single-expert paired reverse-MT gate; no sealed-test, population, independent-rater, clinical-effectiveness or production claim.",
        "sealed_test_opened": False,
        "production_changed": False,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
