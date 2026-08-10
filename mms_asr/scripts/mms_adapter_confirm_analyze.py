"""Aggregate the frozen three-seed MMS maternal-health confirmation."""

import csv
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROTOCOL_ID = "mms-maternal-adapter-confirm-dev-v1"
SEEDS = [20260807, 20260808, 20260809]
BOOTSTRAP_DRAWS = 5000
BOOTSTRAP_SEED = 20261807
DRIVE_ROOT = Path("/content/drive/MyDrive/Akan_ASR_PhD_Experiments")
EXP_ROOT = DRIVE_ROOT / "03_Adaptation/mms_maternal_adaptation_2026-08-06"
RUN_ROOT = EXP_ROOT / "runs"
JOINT_RUN = RUN_ROOT / "20260807_mms_maternal_adapter_confirm_3seed_joint"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def quantile(sorted_values, probability):
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def aggregate(rows):
    totals = defaultdict(int)
    for row in rows:
        for field in [
            "reference_words",
            "reference_chars",
            "baseline_word_errors",
            "baseline_char_errors",
            "adapted_word_errors",
            "adapted_char_errors",
        ]:
            totals[field] += int(row[field])
    return {
        "baseline_wer": totals["baseline_word_errors"] / totals["reference_words"],
        "adapted_wer": totals["adapted_word_errors"] / totals["reference_words"],
        "baseline_cer": totals["baseline_char_errors"] / totals["reference_chars"],
        "adapted_cer": totals["adapted_char_errors"] / totals["reference_chars"],
    }


seed_records = []
seed_rows = {}
seed_groups = {}
input_hashes = {}

for seed in SEEDS:
    run_dir = RUN_ROOT / f"20260807_mms_maternal_adapter_confirm_seed{seed}"
    decision_path = run_dir / "MMS_ADAPTER_CONFIRMATION_SEED_DECISION.json"
    manifest_path = run_dir / "SHA256_MANIFEST.json"
    predictions_path = run_dir / "predictions/mms_adapter_confirm_best_epoch_full_dev_paired.csv"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    assert decision["protocol"] == PROTOCOL_ID
    assert decision["seed"] == seed
    assert decision["sealed_test_opened"] is False
    assert decision["test_rows_read"] == 0
    assert decision["rnmt_human_outcomes_read"] is False
    assert decision["sbllm_run"] is False
    assert decision["production_changed"] is False
    rows = read_csv(predictions_path)
    assert len(rows) == 1558
    groups = defaultdict(list)
    for row in rows:
        groups[row["content_group_id"]].append(row)
    assert len(groups) == 458
    seed_rows[seed] = rows
    seed_groups[seed] = groups
    seed_records.append(decision)
    input_hashes[str(seed)] = {
        "decision": sha256_file(decision_path),
        "manifest": sha256_file(manifest_path),
        "paired_predictions": sha256_file(predictions_path),
        "selected_adapter": decision["output_sha256_before_decision"]["selected_adapter"],
    }

reference_uids = {row["record_uid"] for row in seed_rows[SEEDS[0]]}
for seed in SEEDS[1:]:
    assert {row["record_uid"] for row in seed_rows[seed]} == reference_uids

seed_summaries = []
for decision in seed_records:
    baseline = decision["overall"]["baseline"]
    adapted = decision["overall"]["adapted"]
    seed_summaries.append({
        "seed": decision["seed"],
        "automatic_pass": decision["automatic_pass"],
        "selected_epoch": decision["selected_epoch"],
        "baseline_wer": baseline["wer"],
        "adapted_wer": adapted["wer"],
        "wer_delta": decision["overall"]["wer_delta"],
        "relative_wer_improvement": (baseline["wer"] - adapted["wer"]) / baseline["wer"],
        "baseline_cer": baseline["cer"],
        "adapted_cer": adapted["cer"],
        "cer_delta": decision["overall"]["cer_delta"],
        "relative_cer_improvement": (baseline["cer"] - adapted["cer"]) / baseline["cer"],
        "output_failure_rate": max(record["output_failure_rate"] for record in decision["epoch_records"]),
        "training_seconds": decision["training_seconds"],
        "peak_gpu_memory_bytes": decision["peak_gpu_memory_bytes"],
        "by_speaker": decision["by_speaker"],
        "clustered_bootstrap": decision["clustered_bootstrap"],
    })

rng = random.Random(BOOTSTRAP_SEED)
wer_deltas = []
cer_deltas = []
for _ in range(BOOTSTRAP_DRAWS):
    sampled_rows = []
    for seed in rng.choices(SEEDS, k=len(SEEDS)):
        group_ids = sorted(seed_groups[seed])
        for group_id in rng.choices(group_ids, k=len(group_ids)):
            sampled_rows.extend(seed_groups[seed][group_id])
    rates = aggregate(sampled_rows)
    wer_deltas.append(rates["adapted_wer"] - rates["baseline_wer"])
    cer_deltas.append(rates["adapted_cer"] - rates["baseline_cer"])
wer_deltas.sort()
cer_deltas.sort()
hierarchical_bootstrap = {
    "draws": BOOTSTRAP_DRAWS,
    "seed": BOOTSTRAP_SEED,
    "seed_count": len(SEEDS),
    "content_groups_per_seed": 458,
    "wer_delta_ci95": [quantile(wer_deltas, 0.025), quantile(wer_deltas, 0.975)],
    "cer_delta_ci95": [quantile(cer_deltas, 0.025), quantile(cer_deltas, 0.975)],
}

metric_fields = [
    "adapted_wer",
    "wer_delta",
    "relative_wer_improvement",
    "adapted_cer",
    "cer_delta",
    "relative_cer_improvement",
    "training_seconds",
    "peak_gpu_memory_bytes",
]
summary = {}
for field in metric_fields:
    values = [record[field] for record in seed_summaries]
    summary[field] = {
        "mean": statistics.mean(values),
        "sample_sd": statistics.stdev(values),
        "min": min(values),
        "max": max(values),
    }

speaker_regression_ok = all(
    speaker["wer_delta"] <= 0.03 and speaker["cer_delta"] <= 0.02
    for decision in seed_records
    for speaker in decision["by_speaker"].values()
)

gate_checks = {
    "all_seed_decisions_pass": all(record["automatic_pass"] for record in seed_records),
    "wer_and_cer_improve_every_seed": all(
        record["wer_delta"] < 0 and record["cer_delta"] < 0 for record in seed_summaries
    ),
    "mean_relative_wer_improvement_at_least_5pct": summary["relative_wer_improvement"]["mean"] >= 0.05,
    "no_seed_speaker_regression_beyond_limits": speaker_regression_ok,
    "all_output_failure_rates_at_most_1pct": all(record["output_failure_rate"] <= 0.01 for record in seed_summaries),
    "hierarchical_ci_upper_below_zero": (
        hierarchical_bootstrap["wer_delta_ci95"][1] < 0
        or hierarchical_bootstrap["cer_delta_ci95"][1] < 0
    ),
    "integrity_pass": True,
}

decision = {
    "artifact": "mms_maternal_adapter_three_seed_confirmation_decision_v1",
    "protocol": PROTOCOL_ID,
    "seeds": SEEDS,
    "seed_summaries": seed_summaries,
    "summary": summary,
    "hierarchical_bootstrap": hierarchical_bootstrap,
    "gate_checks": gate_checks,
    "automatic_pass": all(gate_checks.values()),
    "input_sha256": input_hashes,
    "sealed_test_opened": False,
    "test_rows_read": 0,
    "rnmt_human_outcomes_read": False,
    "sbllm_run": False,
    "production_changed": False,
    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
}

JOINT_RUN.mkdir(parents=True, exist_ok=True)
decision_path = JOINT_RUN / "MMS_ADAPTER_THREE_SEED_CONFIRMATION_DECISION.json"
decision_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
manifest = [
    {"path": decision_path.name, "sha256": sha256_file(decision_path), "bytes": decision_path.stat().st_size}
]
(JOINT_RUN / "SHA256_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(decision, indent=2, ensure_ascii=False), flush=True)
