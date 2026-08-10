"""Run the frozen, development-only MMS maternal-health adaptation preflight."""

# Import CSV parsing from the standard library to avoid notebook package-state drift.
import csv
# Import hashing so every materialized input and output can be identified exactly.
import hashlib
# Import JSON so the audit is written in a machine-readable form.
import json
# Import counters for deterministic per-speaker summaries.
from collections import Counter
# Import UTC timestamps for an unambiguous execution record.
from datetime import datetime, timezone
# Import Path for explicit, platform-independent Drive paths.
from pathlib import Path


# Pin the experiment root inside the already mounted Google Drive.
DRIVE_ROOT = Path("/content/drive/MyDrive/Akan_ASR_PhD_Experiments")
# Pin the new experiment directory created for this adaptation study.
EXP_ROOT = DRIVE_ROOT / "03_Adaptation/mms_maternal_adaptation_2026-08-06"
# Pin the uploaded train-only manifest within the experiment directory.
TRAIN_MANIFEST = EXP_ROOT / "V3_M5_TRAIN_AUDIO_MANIFEST_v1.csv"
# Record the frozen manifest digest declared before this execution.
EXPECTED_TRAIN_SHA256 = "1EBC4FF1D7F668AD28BA7262DD4CB143264F39906CF98B3B11806A9BCCDB5633"
# Pin the expected train-only cardinalities declared before execution.
EXPECTED_ROWS = 7240
EXPECTED_GROUPS = 2139
# Pin the only expected speaker codes in the controlled corpus.
EXPECTED_SPEAKERS = ["BT", "HA", "IM", "PT"]


# Define a streaming SHA-256 helper so large files do not need to fit in memory.
def sha256_file(path: Path) -> str:
    # Start a new SHA-256 digest.
    digest = hashlib.sha256()
    # Open the file as raw bytes.
    with path.open("rb") as handle:
        # Read the file in bounded chunks until no bytes remain.
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            # Add this chunk to the digest.
            digest.update(chunk)
    # Return a canonical uppercase hexadecimal digest.
    return digest.hexdigest().upper()


# Define a strict CSV reader that preserves all text fields exactly.
def read_csv_rows(path: Path):
    # Open with newline control so quoted Twi fields remain correctly parsed.
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        # Create a header-aware dictionary reader.
        reader = csv.DictReader(handle)
        # Materialize the rows because this audit is small enough for memory.
        rows = list(reader)
        # Preserve the original column order for the provenance report.
        columns = list(reader.fieldnames or [])
    # Return both rows and columns.
    return rows, columns


# Create the experiment directory if Drive has not materialized it locally yet.
EXP_ROOT.mkdir(parents=True, exist_ok=True)
# Fail before reading data if the frozen train manifest is absent.
assert TRAIN_MANIFEST.exists(), f"Missing frozen training manifest: {TRAIN_MANIFEST}"
# Hash the train manifest before parsing it.
observed_train_sha256 = sha256_file(TRAIN_MANIFEST)
# Enforce the precommitted train-manifest identity.
assert observed_train_sha256 == EXPECTED_TRAIN_SHA256, {
    "expected": EXPECTED_TRAIN_SHA256,
    "observed": observed_train_sha256,
}

# Read the verified train-only manifest with no third-party data-frame dependency.
train, train_columns = read_csv_rows(TRAIN_MANIFEST)
# Require the columns needed for split, leakage, provenance and audio checks.
required_train_columns = {
    "record_uid",
    "content_group_id",
    "speaker_code",
    "audio_path_frozen",
    "audio_sha256",
    "audio_bytes",
    "duration_seconds",
    "split",
}
# Identify any missing required fields before continuing.
missing_train_columns = sorted(required_train_columns.difference(train_columns))
# Stop if the train manifest does not satisfy the frozen schema.
assert not missing_train_columns, f"Missing train columns: {missing_train_columns}"
# Enforce the frozen train-row count.
assert len(train) == EXPECTED_ROWS, {"expected_rows": EXPECTED_ROWS, "observed_rows": len(train)}
# Collect immutable record IDs.
train_record_ids = [row["record_uid"] for row in train]
# Enforce one row per frozen audio record.
assert len(set(train_record_ids)) == EXPECTED_ROWS, "Training record_uid values are not unique"
# Collect immutable semantic-group IDs.
train_groups = {row["content_group_id"] for row in train}
# Enforce the frozen semantic-group count.
assert len(train_groups) == EXPECTED_GROUPS, {
    "expected_groups": EXPECTED_GROUPS,
    "observed_groups": len(train_groups),
}
# Enforce the train-only partition boundary.
assert {row["split"].strip().lower() for row in train} == {"train"}, "A non-train row entered the training manifest"
# Enforce the four declared speaker codes and no others.
assert sorted({row["speaker_code"] for row in train}) == EXPECTED_SPEAKERS, "Unexpected speaker codes"
# Require every recorded audio byte count to be positive.
assert all(int(row["audio_bytes"]) > 0 for row in train), "Non-positive audio byte count detected"
# Require every recorded duration to be positive.
assert all(float(row["duration_seconds"]) > 0 for row in train), "Non-positive audio duration detected"

# Check every frozen Drive audio path without opening or decoding test audio.
audio_exists = [Path(row["audio_path_frozen"]).exists() for row in train]
# Collect any missing train-only audio paths for a transparent stop report.
missing_audio_paths = [row["audio_path_frozen"] for row, exists in zip(train, audio_exists) if not exists]
# Enforce complete train-audio availability before training is considered.
assert not missing_audio_paths, f"Missing {len(missing_audio_paths)} training audio files"

# Search only for the completed full-development baseline input by exact filename.
dev_candidates = sorted(DRIVE_ROOT.rglob("evaluated_records_full_dev.csv"))
# Exclude any accidental paths whose names indicate a test partition.
safe_dev_candidates = [
    path
    for path in dev_candidates
    if "test" not in "/".join(part.lower() for part in path.parts)
]
# Require one unambiguous development source rather than guessing among copies.
assert len(safe_dev_candidates) == 1, {
    "all_candidates": [str(path) for path in dev_candidates],
    "safe_candidates": [str(path) for path in safe_dev_candidates],
}
# Select the sole development-only source.
dev_path = safe_dev_candidates[0]
# Hash the development source before parsing it.
dev_sha256 = sha256_file(dev_path)
# Read the immutable development table without importing NumPy or pandas.
dev, dev_columns = read_csv_rows(dev_path)

# Identify the shared semantic-group key without assuming the historical schema.
group_column = next((name for name in ["content_group_id", "leakage_group_id", "semantic_group_id"] if name in dev_columns), None)
# Identify the speaker field if the baseline table contains one.
speaker_column = next((name for name in ["speaker_code", "speaker", "speaker_id"] if name in dev_columns), None)
# Identify the split field if the baseline table contains one.
split_column = next((name for name in ["split", "partition", "data_split"] if name in dev_columns), None)
# Require the semantic-group key needed for leakage checking.
assert group_column is not None, f"No semantic-group field found in development columns: {dev_columns}"
# Normalize non-empty development group IDs.
dev_groups = {row[group_column] for row in dev if row.get(group_column)}
# Record the exact overlap list for transparent leakage auditing.
group_overlap = sorted(train_groups.intersection(dev_groups))
# Enforce the frozen semantic-group-disjoint boundary.
assert not group_overlap, f"Train/development semantic-group overlap detected: {group_overlap[:20]}"
# If a split column exists, collect its normalized labels.
if split_column is not None:
    # Normalize the observed split labels.
    observed_dev_splits = sorted({row[split_column].strip().lower() for row in dev if row.get(split_column)})
    # Reject any test-labelled row before writing outputs.
    assert not any("test" in value for value in observed_dev_splits), f"Test-labelled row detected: {observed_dev_splits}"
else:
    # Record that partition identity comes from the immutable baseline artifact name and run provenance.
    observed_dev_splits = []

# Compute per-speaker train summaries with deterministic speaker ordering.
train_by_speaker = []
# Iterate over the four frozen speaker codes.
for speaker in EXPECTED_SPEAKERS:
    # Select this speaker's train-only rows.
    block = [row for row in train if row["speaker_code"] == speaker]
    # Append the speaker's row, group and duration counts.
    train_by_speaker.append(
        {
            "speaker_code": speaker,
            "rows": len(block),
            "semantic_groups": len({row["content_group_id"] for row in block}),
            "audio_hours": sum(float(row["duration_seconds"]) for row in block) / 3600.0,
        }
    )

# Compute an optional development speaker summary without assuming uniqueness.
dev_by_speaker = {}
# Populate the summary only when the baseline schema exposes a speaker field.
if speaker_column is not None:
    # Count rows per observed speaker code.
    dev_by_speaker = dict(sorted(Counter(row[speaker_column] for row in dev).items()))

# Assemble the complete preflight report.
report = {
    "artifact": "mms_maternal_adaptation_preflight_report_v1",
    "protocol": "mms-maternal-asr-adaptation-preflight-v1",
    "executed_at_utc": datetime.now(timezone.utc).isoformat(),
    "base_model": {
        "repo_id": "facebook/mms-1b-all",
        "revision": "3d33597edbdaaba14a8e858e2c8caa76e3cec0cd",
        "target_lang": "aka",
    },
    "training_manifest": {
        "path": str(TRAIN_MANIFEST),
        "sha256": observed_train_sha256,
        "rows": len(train),
        "unique_records": len(set(train_record_ids)),
        "semantic_groups": len(train_groups),
        "speaker_codes": EXPECTED_SPEAKERS,
        "audio_hours": sum(float(row["duration_seconds"]) for row in train) / 3600.0,
        "audio_files_present": sum(audio_exists),
        "audio_files_missing": len(missing_audio_paths),
        "by_speaker": train_by_speaker,
    },
    "development_source": {
        "path": str(dev_path),
        "sha256": dev_sha256,
        "rows": len(dev),
        "columns": dev_columns,
        "group_column": group_column,
        "semantic_groups": len(dev_groups),
        "speaker_column": speaker_column,
        "by_speaker_rows": dev_by_speaker,
        "split_column": split_column,
        "split_values": observed_dev_splits,
    },
    "leakage_checks": {
        "train_development_semantic_group_overlap_count": len(group_overlap),
        "train_development_semantic_group_overlap": group_overlap,
    },
    "boundaries": {
        "model_fitted": False,
        "sealed_test_opened": False,
        "test_rows_read": 0,
        "rnmt_human_outcomes_read": False,
        "sbllm_run": False,
        "production_changed": False,
    },
    "preflight_pass": True,
}

# Pin the machine-readable report path.
report_path = EXP_ROOT / "MMS_MATERNAL_ADAPTATION_PREFLIGHT_REPORT.json"
# Serialize with stable key order and UTF-8 Twi support.
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
# Hash the completed report for the execution log.
report_sha256 = sha256_file(report_path)
# Write a separate output manifest so the report identity is obvious.
output_manifest = {
    "artifact": "mms_maternal_adaptation_preflight_output_manifest_v1",
    "report_file": report_path.name,
    "report_sha256": report_sha256,
    "sealed_test_opened": False,
    "test_rows_read": 0,
}
# Pin the output-manifest path.
output_manifest_path = EXP_ROOT / "MMS_MATERNAL_ADAPTATION_PREFLIGHT_OUTPUT_MANIFEST.json"
# Write the output manifest deterministically.
output_manifest_path.write_text(json.dumps(output_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
# Print the decision record for visible Colab verification.
print(json.dumps({"report": report, "report_sha256": report_sha256}, indent=2, ensure_ascii=False))

