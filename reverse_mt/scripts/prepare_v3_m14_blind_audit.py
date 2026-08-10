from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "frozen_inputs" / "V3_M14_72_CASE_REVERSE_MT_INPUTS_2026-08-09.csv"
TRANSLATIONS = ROOT / "execution_outputs" / "V3_M14_ALL_TRANSLATIONS.csv"
AUDIT_DIR = ROOT / "blind_audit"
AUDIT_JSON = AUDIT_DIR / "V3_M14_BLIND_AUDIT_ROWS_2026-08-09.json"
REVEAL_JSON = AUDIT_DIR / "SEALED_V3_M14_REVEAL_KEY_DO_NOT_OPEN_2026-08-09.json"
REVEAL_CSV = AUDIT_DIR / "SEALED_V3_M14_REVEAL_KEY_DO_NOT_OPEN_2026-08-09.csv"
SOURCE_MANIFEST = AUDIT_DIR / "V3_M14_BLIND_AUDIT_SOURCE_MANIFEST_2026-08-09.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    inputs = read_csv(INPUTS)
    outputs = read_csv(TRANSLATIONS)
    assert len(inputs) == 72, f"Expected 72 frozen cases, found {len(inputs)}"
    assert len(outputs) == 144, f"Expected 144 translations, found {len(outputs)}"

    by_audit: dict[str, dict[str, dict[str, str]]] = {}
    for row in outputs:
        by_audit.setdefault(row["audit_id"], {})[row["candidate_id"]] = row
    assert set(by_audit) == {row["audit_id"] for row in inputs}
    assert all(set(pair) == {"B1", "B3"} for pair in by_audit.values())

    blind_rows: list[dict[str, object]] = []
    reveal_rows: list[dict[str, object]] = []
    count_a = {"B1": 0, "B3": 0}

    for source in inputs:
        audit_id = source["audit_id"]
        pair = by_audit[audit_id]
        assert pair["B1"]["source_english"] == source["sbllm_response_english"]
        assert pair["B3"]["source_english"] == source["sbllm_response_english"]

        assignment_hash = sha256_text(audit_id + "|V3-M14|20260809")
        candidate_a_id = "B1" if int(assignment_hash[-1], 16) % 2 == 0 else "B3"
        candidate_b_id = "B3" if candidate_a_id == "B1" else "B1"
        count_a[candidate_a_id] += 1

        blind_rows.append(
            {
                "audit_id": audit_id,
                "validated_gold_akan": source["validated_gold_akan"],
                "validated_english_reference": source["validated_english_reference"],
                "adapted_mms_twi": source["adapted_mms_twi"],
                "adapted_mms_forward_english": source["adapted_mms_forward_english"],
                "sbllm_response_english": source["sbllm_response_english"],
                "sbllm_disposition": source["sbllm_disposition"],
                "candidate_a_twi": pair[candidate_a_id]["translation_twi"],
                "candidate_b_twi": pair[candidate_b_id]["translation_twi"],
            }
        )

        reveal_rows.append(
            {
                "audit_id": audit_id,
                "assignment_hash": assignment_hash,
                "candidate_a_id": candidate_a_id,
                "candidate_a_model_id": pair[candidate_a_id]["model_id"],
                "candidate_a_revision": pair[candidate_a_id]["revision"],
                "candidate_a_translation_sha256": pair[candidate_a_id]["translation_sha256"],
                "candidate_b_id": candidate_b_id,
                "candidate_b_model_id": pair[candidate_b_id]["model_id"],
                "candidate_b_revision": pair[candidate_b_id]["revision"],
                "candidate_b_translation_sha256": pair[candidate_b_id]["translation_sha256"],
                "record_uid": source["record_uid"],
                "content_group_id": source["content_group_id"],
                "speaker_code": source["speaker_code"],
                "theme_key": source["theme_key"],
                "challenge_stratum": source["challenge_stratum"],
                "protected_categories": source["protected_categories"],
                "protected_case": source["protected_case"],
                "v3m10_e1_upstream_intent": source["v3m10_e1_upstream_intent"],
                "v3m10_e1_upstream_response_safety": source["v3m10_e1_upstream_response_safety"],
                "v3m10_e1_upstream_groundedness": source["v3m10_e1_upstream_groundedness"],
                "upstream_english_useful_safe": source["upstream_english_useful_safe"],
                "mandatory_pattern_probe": source["mandatory_pattern_probe"],
                "source_row_sha256": source["source_row_sha256"],
            }
        )

    AUDIT_JSON.write_text(json.dumps(blind_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REVEAL_JSON.write_text(
        json.dumps(
            {
                "artifact": "v3_m14_sealed_reveal_key_v1",
                "protocol_id": "rnmt-sbllm-v3-m14-end-to-end-reverse-mt-gate-v1",
                "warning": "DO NOT OPEN UNTIL THE COMPLETED BLIND AUDIT WORKBOOK IS LOCKED AND HASHED.",
                "mapping_rule": "SHA256(audit_id + '|V3-M14|20260809') final hexadecimal parity; even => A=B1, odd => A=B3",
                "candidate_a_counts": count_a,
                "rows": reveal_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with REVEAL_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(reveal_rows[0]))
        writer.writeheader()
        writer.writerows(reveal_rows)

    manifest = {
        "artifact": "v3_m14_blind_audit_source_manifest_v1",
        "protocol_id": "rnmt-sbllm-v3-m14-end-to-end-reverse-mt-gate-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": 72,
        "candidate_a_counts": count_a,
        "mapping_method_frozen": True,
        "model_id_visible_in_audit": False,
        "prior_human_outcomes_visible_in_audit": False,
        "automatic_scores_visible_in_audit": False,
        "sealed_test_opened": False,
        "production_changed": False,
        "sha256": {
            "frozen_inputs": sha256_file(INPUTS),
            "execution_reported_all_translations": "61374E484680A7AE26DCDE49B837830CD7D4E2A9AB5FFA52A5CE42E35A6C294E",
            "connector_materialized_all_translations": sha256_file(TRANSLATIONS),
            "blind_audit_rows": sha256_file(AUDIT_JSON),
            "sealed_reveal_json": sha256_file(REVEAL_JSON),
            "sealed_reveal_csv": sha256_file(REVEAL_CSV),
        },
    }
    SOURCE_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
