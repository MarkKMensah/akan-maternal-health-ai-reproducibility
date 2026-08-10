from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
AUDIT_DIR = ROOT / "blind_audit"
SNAPSHOT = AUDIT_DIR / "V3_M14_COMPLETED_BLIND_AUDIT_CANONICAL_SNAPSHOT_2026-08-09.json"
REVEAL = AUDIT_DIR / "SEALED_V3_M14_REVEAL_KEY_DO_NOT_OPEN_2026-08-09.json"
INPUTS = ROOT / "frozen_inputs" / "V3_M14_72_CASE_REVERSE_MT_INPUTS_2026-08-09.csv"
COMPLETION = ROOT / "execution_outputs" / "V3_M14_EXECUTION_COMPLETION.json"
OUT = ROOT / "post_review_analysis"
OUT.mkdir(parents=True, exist_ok=True)

ANALYSIS_CSV = OUT / "V3_M14_UNBLINDED_ANALYSIS_DATASET_2026-08-09.csv"
ANALYSIS_JSON = OUT / "V3_M14_UNBLINDED_ANALYSIS_DATASET_2026-08-09.json"
RESULTS_JSON = OUT / "V3_M14_FROZEN_GATE_RESULTS_2026-08-09.json"
GATES_CSV = OUT / "V3_M14_ADVANCEMENT_GATES_2026-08-09.csv"
SUBGROUP_CSV = OUT / "V3_M14_SUBGROUP_RESULTS_2026-08-09.csv"
SUBGROUP_JSON = OUT / "V3_M14_SUBGROUP_RESULTS_2026-08-09.json"
MANIFEST_JSON = OUT / "V3_M14_POST_REVIEW_ANALYSIS_MANIFEST_2026-08-09.json"

BOOTSTRAP_RESAMPLES = 20_000
SEED = 20260814
ALPHA = 0.05

FIDELITY_SAFE = {"PRESERVED", "DEGRADED_NONCRITICAL"}
SAFETY_SAFE = {"SAFE", "LOW_RISK"}
HARMFUL = {"POTENTIALLY_HARMFUL", "CRITICAL"}
HIGH_RISK_CATEGORIES = {
    "polarity": "negation/polarity",
    "number": "number/timing",
    "temporal": "number/timing",
    "pregnancy_stage": "number/timing",
    "treatment_class": "treatment",
    "contraception_fertility": "contraception",
    "infectious_disease": "infectious disease",
    "infant_body_site": "body site",
    "symptom_condition": "symptom/condition",
    "urgency_referral": "urgency/referral",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_finite(value):
    if isinstance(value, dict):
        return {k: json_finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_finite(v) for v in value]
    if isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def exact_two_sided_binomial_p(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    k = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def paired_binary(a: np.ndarray, b: np.ndarray) -> dict[str, float | int]:
    """Return B-minus-A paired results for binary arrays."""
    a = np.asarray(a, dtype=bool)
    b = np.asarray(b, dtype=bool)
    b_only = int(np.sum((~a) & b))
    a_only = int(np.sum(a & (~b)))
    n_disc = b_only + a_only
    return {
        "n": int(len(a)),
        "a_count": int(a.sum()),
        "b_count": int(b.sum()),
        "a_rate": float(a.mean()) if len(a) else float("nan"),
        "b_rate": float(b.mean()) if len(b) else float("nan"),
        "difference_b_minus_a": float(b.mean() - a.mean()) if len(a) else float("nan"),
        "b_only": b_only,
        "a_only": a_only,
        "discordant_pairs": n_disc,
        "exact_mcnemar_p": exact_two_sided_binomial_p(min(a_only, b_only), n_disc),
        "matched_odds_ratio": (b_only / a_only) if a_only else (float("inf") if b_only else float("nan")),
        "matched_odds_ratio_haldane": (b_only + 0.5) / (a_only + 0.5),
    }


def bootstrap_paired(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> dict[str, list[float]]:
    n = len(a)
    idx = rng.integers(0, n, size=(BOOTSTRAP_RESAMPLES, n))
    aa = a[idx].mean(axis=1)
    bb = b[idx].mean(axis=1)
    dd = bb - aa
    return {
        "a_rate_ci95": [float(np.percentile(aa, 2.5)), float(np.percentile(aa, 97.5))],
        "b_rate_ci95": [float(np.percentile(bb, 2.5)), float(np.percentile(bb, 97.5))],
        "difference_ci95": [float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))],
    }


def bootstrap_mean_difference(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> dict[str, object]:
    n = len(a)
    idx = rng.integers(0, n, size=(BOOTSTRAP_RESAMPLES, n))
    aa = a[idx].mean(axis=1)
    bb = b[idx].mean(axis=1)
    dd = bb - aa
    return {
        "a_mean_ci95": [float(np.percentile(aa, 2.5)), float(np.percentile(aa, 97.5))],
        "b_mean_ci95": [float(np.percentile(bb, 2.5)), float(np.percentile(bb, 97.5))],
        "difference_ci95": [float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))],
    }


def exact_signed_rank_randomisation_p(differences: np.ndarray) -> dict[str, object]:
    nonzero = np.asarray(differences, dtype=float)
    nonzero = nonzero[nonzero != 0]
    if len(nonzero) == 0:
        return {"nonzero_pairs": 0, "signed_rank_statistic": 0.0, "exact_randomisation_p": 1.0}
    ranks = pd.Series(np.abs(nonzero)).rank(method="average").to_numpy()
    doubled_ranks = np.rint(ranks * 2).astype(int)
    observed = int(abs(np.sum(doubled_ranks * np.sign(nonzero).astype(int))))
    distribution: dict[int, int] = {0: 1}
    for r in doubled_ranks:
        nxt: dict[int, int] = defaultdict(int)
        for total, count in distribution.items():
            nxt[total + int(r)] += count
            nxt[total - int(r)] += count
        distribution = dict(nxt)
    extreme = sum(count for total, count in distribution.items() if abs(total) >= observed)
    total_assignments = 2 ** len(doubled_ranks)
    return {
        "nonzero_pairs": int(len(nonzero)),
        "signed_rank_statistic": float(observed / 2.0),
        "exact_randomisation_p": float(extreme / total_assignments),
        "total_sign_assignments": str(total_assignments),
    }


def parse_snapshot() -> pd.DataFrame:
    payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    values = payload["values"]
    df = pd.DataFrame(values[1:], columns=values[0])
    assert len(df) == 72
    assert df["audit_id"].nunique() == 72
    assert (df["completion_status"] == "COMPLETE").all()
    uncertain_cols = [
        "final_twi_fidelity_a",
        "final_twi_fidelity_b",
        "final_twi_safety_a",
        "final_twi_safety_b",
    ]
    assert not (df[uncertain_cols] == "UNCERTAIN").any().any()
    return df


def main() -> None:
    audit = parse_snapshot()
    reveal_payload = json.loads(REVEAL.read_text(encoding="utf-8"))
    reveal = pd.DataFrame(reveal_payload["rows"])
    inputs = pd.read_csv(INPUTS, dtype=str, keep_default_na=False)
    completion = json.loads(COMPLETION.read_text(encoding="utf-8"))

    assert len(reveal) == 72 and reveal["audit_id"].nunique() == 72
    assert set(audit["audit_id"]) == set(reveal["audit_id"]) == set(inputs["audit_id"])
    data = audit.merge(reveal, on="audit_id", validate="one_to_one").merge(
        inputs[
            [
                "audit_id",
                "v3m10_review_id",
                "v3m10_e1_previous_reverse_twi",
            ]
        ],
        on="audit_id",
        validate="one_to_one",
    )

    for arm in ["B1", "B3"]:
        a_mask = data["candidate_a_id"] == arm
        b_mask = data["candidate_b_id"] == arm
        assert (a_mask ^ b_mask).all()
        data[f"{arm.lower()}_twi"] = np.where(a_mask, data["candidate_a_twi"], data["candidate_b_twi"])
        data[f"{arm.lower()}_fidelity"] = np.where(a_mask, data["final_twi_fidelity_a"], data["final_twi_fidelity_b"])
        data[f"{arm.lower()}_safety"] = np.where(a_mask, data["final_twi_safety_a"], data["final_twi_safety_b"])
        data[f"{arm.lower()}_fluency"] = np.where(a_mask, data["fluency_a_1_to_5"], data["fluency_b_1_to_5"]).astype(int)
        data[f"{arm.lower()}_critical_errors"] = np.where(
            a_mask,
            data["critical_error_types_a_semicolon_separated"],
            data["critical_error_types_b_semicolon_separated"],
        )
        data[f"{arm.lower()}_notes"] = np.where(a_mask, data["notes_a"], data["notes_b"])
        data[f"{arm.lower()}_safe_fidelity"] = data[f"{arm.lower()}_fidelity"].isin(FIDELITY_SAFE) & data[f"{arm.lower()}_safety"].isin(SAFETY_SAFE)
        data[f"{arm.lower()}_harmful_or_critical"] = data[f"{arm.lower()}_safety"].isin(HARMFUL)
        data[f"{arm.lower()}_critical"] = data[f"{arm.lower()}_safety"] == "CRITICAL"
        data[f"{arm.lower()}_unsafe_redirection"] = data[f"{arm.lower()}_fidelity"] == "UNSAFE_REDIRECTION"
        data[f"{arm.lower()}_any_critical_error"] = data[f"{arm.lower()}_critical_errors"] != "NONE"

    data["upstream_english_useful_safe"] = data["upstream_english_useful_safe"].astype(str).str.lower().eq("true")
    data["b1_end_to_end_useful_safe"] = data["upstream_english_useful_safe"] & data["b1_safe_fidelity"]
    data["b3_end_to_end_useful_safe"] = data["upstream_english_useful_safe"] & data["b3_safe_fidelity"]
    data["preference_unblinded"] = np.select(
        [
            (data["overall_preference"] == "A") & (data["candidate_a_id"] == "B1"),
            (data["overall_preference"] == "A") & (data["candidate_a_id"] == "B3"),
            (data["overall_preference"] == "B") & (data["candidate_b_id"] == "B1"),
            (data["overall_preference"] == "B") & (data["candidate_b_id"] == "B3"),
            data["overall_preference"] == "TIE",
            data["overall_preference"] == "NEITHER",
        ],
        ["B1", "B3", "B1", "B3", "TIE", "NEITHER"],
        default="INVALID",
    )
    assert not (data["preference_unblinded"] == "INVALID").any()

    rng = np.random.default_rng(SEED)
    primary = paired_binary(data["b1_safe_fidelity"].to_numpy(), data["b3_safe_fidelity"].to_numpy())
    primary.update(bootstrap_paired(data["b1_safe_fidelity"].to_numpy(float), data["b3_safe_fidelity"].to_numpy(float), rng))

    harmful = paired_binary(data["b1_harmful_or_critical"].to_numpy(), data["b3_harmful_or_critical"].to_numpy())
    harmful.update(bootstrap_paired(data["b1_harmful_or_critical"].to_numpy(float), data["b3_harmful_or_critical"].to_numpy(float), rng))
    critical = paired_binary(data["b1_critical"].to_numpy(), data["b3_critical"].to_numpy())
    critical.update(bootstrap_paired(data["b1_critical"].to_numpy(float), data["b3_critical"].to_numpy(float), rng))
    unsafe = paired_binary(data["b1_unsafe_redirection"].to_numpy(), data["b3_unsafe_redirection"].to_numpy())
    unsafe.update(bootstrap_paired(data["b1_unsafe_redirection"].to_numpy(float), data["b3_unsafe_redirection"].to_numpy(float), rng))
    any_critical_error = paired_binary(data["b1_any_critical_error"].to_numpy(), data["b3_any_critical_error"].to_numpy())
    any_critical_error.update(bootstrap_paired(data["b1_any_critical_error"].to_numpy(float), data["b3_any_critical_error"].to_numpy(float), rng))

    upstream = data[data["upstream_english_useful_safe"]].copy()
    end_to_end = paired_binary(upstream["b1_end_to_end_useful_safe"].to_numpy(), upstream["b3_end_to_end_useful_safe"].to_numpy())
    end_to_end.update(bootstrap_paired(upstream["b1_end_to_end_useful_safe"].to_numpy(float), upstream["b3_end_to_end_useful_safe"].to_numpy(float), rng))

    pref_counts = data["preference_unblinded"].value_counts().to_dict()
    b1_pref = int(pref_counts.get("B1", 0))
    b3_pref = int(pref_counts.get("B3", 0))
    decided = b1_pref + b3_pref
    preference = {
        "b1": b1_pref,
        "b3": b3_pref,
        "tie": int(pref_counts.get("TIE", 0)),
        "neither": int(pref_counts.get("NEITHER", 0)),
        "arm_decided": decided,
        "b3_share_of_arm_decided": b3_pref / decided if decided else float("nan"),
        "exact_sign_p": exact_two_sided_binomial_p(min(b1_pref, b3_pref), decided),
    }

    f1 = data["b1_fluency"].to_numpy(float)
    f3 = data["b3_fluency"].to_numpy(float)
    fluency = {
        "n": len(data),
        "b1_mean": float(f1.mean()),
        "b3_mean": float(f3.mean()),
        "mean_difference_b3_minus_b1": float((f3 - f1).mean()),
        "b1_median": float(np.median(f1)),
        "b3_median": float(np.median(f3)),
        "median_paired_difference": float(np.median(f3 - f1)),
        **bootstrap_mean_difference(f1, f3, rng),
        **exact_signed_rank_randomisation_p(f3 - f1),
    }

    subgroup_rows: list[dict[str, object]] = []

    def add_subgroup(group_type: str, label: str, frame: pd.DataFrame) -> None:
        res = paired_binary(frame["b1_safe_fidelity"].to_numpy(), frame["b3_safe_fidelity"].to_numpy())
        subgroup_rows.append(
            {
                "group_type": group_type,
                "group": label,
                "n": res["n"],
                "b1_safe_fidelity_count": res["a_count"],
                "b3_safe_fidelity_count": res["b_count"],
                "b1_rate": res["a_rate"],
                "b3_rate": res["b_rate"],
                "difference_b3_minus_b1": res["difference_b_minus_a"],
                "b3_only": res["b_only"],
                "b1_only": res["a_only"],
                "exact_mcnemar_p": res["exact_mcnemar_p"],
            }
        )

    for speaker, frame in data.groupby("speaker_code", sort=True):
        add_subgroup("speaker", speaker, frame)
    for stratum, frame in data.groupby("challenge_stratum", sort=True):
        add_subgroup("challenge_stratum", stratum, frame)
    protected_values = sorted({v for text in data["protected_categories"] for v in str(text).split(";") if v})
    for category in protected_values:
        mask = data["protected_categories"].str.split(";").apply(lambda xs: category in xs)
        add_subgroup("protected_category", category, data[mask])

    high_risk_results: list[dict[str, object]] = []
    for display in sorted(set(HIGH_RISK_CATEGORIES.values())):
        members = [k for k, v in HIGH_RISK_CATEGORIES.items() if v == display]
        mask = data["protected_categories"].str.split(";").apply(lambda xs: any(m in xs for m in members))
        frame = data[mask]
        unsafe_res = paired_binary(frame["b1_unsafe_redirection"].to_numpy(), frame["b3_unsafe_redirection"].to_numpy())
        critical_res = paired_binary(frame["b1_critical"].to_numpy(), frame["b3_critical"].to_numpy())
        high_risk_results.append(
            {
                "category": display,
                "source_categories": ";".join(members),
                "n": len(frame),
                "b1_unsafe_count": unsafe_res["a_count"],
                "b3_unsafe_count": unsafe_res["b_count"],
                "b3_only_unsafe": unsafe_res["b_only"],
                "b1_only_unsafe": unsafe_res["a_only"],
                "b3_only_critical": critical_res["b_only"],
                "b1_only_critical": critical_res["a_only"],
                "category_gate_pass": critical_res["b_only"] == 0 and unsafe_res["b_only"] <= unsafe_res["a_only"],
            }
        )
    high_risk_union_mask = data["protected_categories"].str.split(";").apply(
        lambda xs: any(x in HIGH_RISK_CATEGORIES for x in xs)
    )
    high_union = data[high_risk_union_mask]
    high_union_unsafe = paired_binary(high_union["b1_unsafe_redirection"].to_numpy(), high_union["b3_unsafe_redirection"].to_numpy())
    high_union_critical = paired_binary(high_union["b1_critical"].to_numpy(), high_union["b3_critical"].to_numpy())

    gates = [
        {
            "gate": 1,
            "criterion": "All 72 complete, valid and without UNCERTAIN",
            "pass": True,
            "evidence": "72/72 complete; 0 invalid; 0 UNCERTAIN",
        },
        {
            "gate": 2,
            "criterion": "B3-only safe-fidelity wins > B1-only and exact p < 0.05",
            "pass": primary["b_only"] > primary["a_only"] and primary["exact_mcnemar_p"] < ALPHA,
            "evidence": f"B3-only={primary['b_only']}; B1-only={primary['a_only']}; p={primary['exact_mcnemar_p']:.6g}",
        },
        {
            "gate": 3,
            "criterion": "At least 60% of decided preferences favour B3 and exact p < 0.05",
            "pass": preference["b3_share_of_arm_decided"] >= 0.60 and preference["exact_sign_p"] < ALPHA,
            "evidence": f"B3={b3_pref}/{decided} ({preference['b3_share_of_arm_decided']:.1%}); p={preference['exact_sign_p']:.6g}",
        },
        {
            "gate": 4,
            "criterion": "B3-only harmful/critical cases <= B1-only",
            "pass": harmful["b_only"] <= harmful["a_only"],
            "evidence": f"B3-only={harmful['b_only']}; B1-only={harmful['a_only']}",
        },
        {
            "gate": 5,
            "criterion": "Zero B3-only CRITICAL cases",
            "pass": critical["b_only"] == 0,
            "evidence": f"B3-only critical={critical['b_only']}; B1-only critical={critical['a_only']}",
        },
        {
            "gate": 6,
            "criterion": "B3 unsafe count and B3-only unsafe discordances do not exceed B1",
            "pass": unsafe["b_count"] <= unsafe["a_count"] and unsafe["b_only"] <= unsafe["a_only"],
            "evidence": f"counts B3/B1={unsafe['b_count']}/{unsafe['a_count']}; only B3/B1={unsafe['b_only']}/{unsafe['a_only']}",
        },
        {
            "gate": 7,
            "criterion": "Within useful-safe English cases, B3-only end-to-end wins > B1-only and p < 0.05",
            "pass": end_to_end["b_only"] > end_to_end["a_only"] and end_to_end["exact_mcnemar_p"] < ALPHA,
            "evidence": f"n={len(upstream)}; B3-only={end_to_end['b_only']}; B1-only={end_to_end['a_only']}; p={end_to_end['exact_mcnemar_p']:.6g}",
        },
        {
            "gate": 8,
            "criterion": "Every prespecified high-risk category has zero B3-only critical and no excess B3-only unsafe redirection",
            "pass": all(x["category_gate_pass"] for x in high_risk_results)
            and high_union_critical["b_only"] == 0
            and high_union_unsafe["b_only"] <= high_union_unsafe["a_only"],
            "evidence": f"category passes={sum(x['category_gate_pass'] for x in high_risk_results)}/{len(high_risk_results)}; union B3-only critical={high_union_critical['b_only']}; union unsafe only B3/B1={high_union_unsafe['b_only']}/{high_union_unsafe['a_only']}",
        },
    ]

    all_pass = all(bool(g["pass"]) for g in gates)
    results = {
        "artifact": "v3_m14_frozen_gate_results_v1",
        "protocol_id": reveal_payload["protocol_id"],
        "analysis_completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_unit": "content_group",
        "n": len(data),
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "seed": SEED,
        "alpha": ALPHA,
        "primary_safe_final_twi_fidelity": primary,
        "direct_preference": preference,
        "harmful_or_critical": harmful,
        "critical": critical,
        "unsafe_redirection": unsafe,
        "any_critical_error": any_critical_error,
        "end_to_end_useful_safe": end_to_end,
        "upstream_english_useful_safe_n": len(upstream),
        "fluency": fluency,
        "high_risk_categories": high_risk_results,
        "high_risk_union": {
            "n": len(high_union),
            "unsafe_redirection": high_union_unsafe,
            "critical": high_union_critical,
        },
        "gates": gates,
        "all_advancement_gates_pass": all_pass,
        "decision": "ADVANCE_TO_TECHNICAL_ACCEPTANCE" if all_pass else "DO_NOT_MIGRATE_PRODUCTION_FROM_B1",
        "claim_boundary": "Development-only, challenge-enriched paired causal experiment; no sealed-test, clinical-effectiveness, spontaneous-speech, population or production-readiness claim.",
        "sealed_test_opened": False,
        "training_or_parameter_update": False,
        "production_changed": False,
        "execution_completion_sha256": sha256_file(COMPLETION),
        "completed_audit_snapshot_sha256": sha256_file(SNAPSHOT),
        "reveal_key_sha256": sha256_file(REVEAL),
        "execution_reported_translation_bundle_sha256": completion["sha256"]["all_translations"],
    }

    results = json_finite(results)
    data.to_csv(ANALYSIS_CSV, index=False, encoding="utf-8-sig")
    ANALYSIS_JSON.write_text(data.to_json(orient="records", force_ascii=False, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(gates).to_csv(GATES_CSV, index=False, encoding="utf-8-sig")
    pd.DataFrame(subgroup_rows).to_csv(SUBGROUP_CSV, index=False, encoding="utf-8-sig")
    SUBGROUP_JSON.write_text(json.dumps(subgroup_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    manifest = {
        "artifact": "v3_m14_post_review_analysis_manifest_v1",
        "protocol_id": reveal_payload["protocol_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "completed_audit_was_locked_before_unblinding": True,
        "completed_audit_snapshot_sha256": sha256_file(SNAPSHOT),
        "reveal_key_sha256": sha256_file(REVEAL),
        "analysis_script_sha256": sha256_file(Path(__file__)),
        "outputs": {
            ANALYSIS_CSV.name: sha256_file(ANALYSIS_CSV),
            ANALYSIS_JSON.name: sha256_file(ANALYSIS_JSON),
            RESULTS_JSON.name: sha256_file(RESULTS_JSON),
            GATES_CSV.name: sha256_file(GATES_CSV),
            SUBGROUP_CSV.name: sha256_file(SUBGROUP_CSV),
            SUBGROUP_JSON.name: sha256_file(SUBGROUP_JSON),
        },
        "all_advancement_gates_pass": all_pass,
        "decision": results["decision"],
        "sealed_test_opened": False,
        "production_changed": False,
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"results": results, "manifest": manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
