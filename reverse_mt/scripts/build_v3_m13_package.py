"""Build the frozen V3-M13 development-only benchmark package."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parent
FROZEN = ROOT / "frozen_inputs"

SOURCE_DEV = (
    WORKSPACE
    / "work_products"
    / "nllb_v3_m9"
    / "execution_outputs"
    / "outputs"
    / "V3_M9_G_D0_D1_ALL_DEVELOPMENT_PREDICTIONS.csv"
)
SOURCE_TRAIN = (
    WORKSPACE
    / "work_products"
    / "nllb_v3_m6_design"
    / "V3_M6_TRAIN_ONLY_MULTIVARIANT_INDEX_2026-08-06.csv"
)
SOURCE_SCHEMA = (
    WORKSPACE
    / "work_products"
    / "nllb_v3_m3"
    / "V3_M3_PROTECTED_CONCEPT_SCHEMA_FROZEN_2026-08-06.json"
)

PROTOCOL = ROOT / "RNMT_SBLLM_V3_M13_REVERSE_MT_ZERO_SHOT_BENCHMARK_PROTOCOL_FROZEN_2026-08-08.md"
SCRIPT = ROOT / "v3_m13_execute.py"
NOTEBOOK = ROOT / "V3_M13_REVERSE_MT_ZERO_SHOT_DEV_COLAB_2026-08-08.ipynb"
REGISTRY = ROOT / "V3_M13_CANDIDATE_REGISTRY_FROZEN_2026-08-08.json"
INPUT_MANIFEST = ROOT / "V3_M13_INPUT_MANIFEST_2026-08-08.json"
PRECOMMIT = ROOT / "V3_M13_EXECUTION_PRECOMMIT_2026-08-08.json"
PACKAGE_MANIFEST = ROOT / "V3_M13_PREEXECUTION_PACKAGE_MANIFEST_2026-08-08.json"

DEV_UNITS = FROZEN / "V3_M13_DEV_MULTIREFERENCE_460_UNITS_2026-08-08.csv"
TRAIN_INDEX = FROZEN / "V3_M13_TRAIN_ONLY_MULTIVARIANT_INDEX_7240_ROWS_2026-08-08.csv"
SCHEMA = FROZEN / "V3_M13_PROTECTED_CONCEPT_SCHEMA_FROZEN_COPY_2026-08-08.json"

PROTOCOL_ID = "rnmt-sbllm-v3-m13-reverse-mt-zeroshot-dev-v1"
M12_RESPONSE_SHA256 = "EF50378C45C31E6FF1474D0FE0EC9E80863A58582ABA2EFFAD4C6293F01F2821"


def normalize(value: object) -> str:
    """Apply only NFC and whitespace collapse to human-authored content."""
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def normalized_key(value: object) -> str:
    """Return the leakage-audit key without changing the stored text."""
    return normalize(value).casefold()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_development_units() -> dict[str, object]:
    rows = load_csv(SOURCE_DEV)
    if len(rows) != 1558:
        raise RuntimeError(f"Expected 1,558 development rows; observed {len(rows)}")
    if len({row["record_uid"] for row in rows}) != 1558:
        raise RuntimeError("Development record_uid values are not unique")
    original_groups = {row["content_group_id"] for row in rows}
    if len(original_groups) != 458:
        raise RuntimeError(f"Expected 458 development groups; observed {len(original_groups)}")

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    sources_by_group: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        source = normalize(row["reference_english"])
        grouped[(row["content_group_id"], source)].append(row)
        sources_by_group[row["content_group_id"]].add(source)

    units: list[dict[str, object]] = []
    split_groups: dict[str, list[str]] = {}
    for content_group_id in sorted(sources_by_group):
        sources = sorted(
            sources_by_group[content_group_id],
            key=lambda text: (sha256_text(text), text),
        )
        if len(sources) > 1:
            split_groups[content_group_id] = sources
        for index, source in enumerate(sources):
            unit_id = content_group_id if len(sources) == 1 else f"{content_group_id}-{chr(65 + index)}"
            members = grouped[(content_group_id, source)]
            references: list[str] = []
            for member in members:
                reference = normalize(member["gold_twi"])
                if reference and reference not in references:
                    references.append(reference)
            if not references:
                raise RuntimeError(f"No Twi reference for {unit_id}")
            record_uids = sorted({member["record_uid"] for member in members})
            speakers = sorted({member["speaker_code"] for member in members})
            themes = sorted({member["theme_key"] for member in members})
            body = {
                "eval_unit_id": unit_id,
                "original_content_group_id": content_group_id,
                "source_english": source,
                "references_twi_json": json.dumps(references, ensure_ascii=False),
                "reference_count": len(references),
                "record_uids_json": json.dumps(record_uids, ensure_ascii=False),
                "speaker_codes_json": json.dumps(speakers, ensure_ascii=False),
                "theme_keys_json": json.dumps(themes, ensure_ascii=False),
            }
            body["input_row_sha256"] = sha256_text(
                json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            )
            units.append(body)

    if len(units) != 460:
        raise RuntimeError(f"Expected 460 evaluation units; observed {len(units)}")
    write_csv(
        DEV_UNITS,
        units,
        [
            "eval_unit_id",
            "original_content_group_id",
            "source_english",
            "references_twi_json",
            "reference_count",
            "record_uids_json",
            "speaker_codes_json",
            "theme_keys_json",
            "input_row_sha256",
        ],
    )
    return {
        "source_rows": len(rows),
        "original_content_groups": len(original_groups),
        "evaluation_units": len(units),
        "split_original_groups": split_groups,
    }


def copy_and_audit_training_index(dev_units: list[dict[str, str]]) -> dict[str, object]:
    shutil.copyfile(SOURCE_TRAIN, TRAIN_INDEX)
    train = load_csv(TRAIN_INDEX)
    if len(train) != 7240:
        raise RuntimeError(f"Expected 7,240 train rows; observed {len(train)}")
    train_groups = {row["content_group_id"] for row in train}
    if len(train_groups) != 2139:
        raise RuntimeError(f"Expected 2,139 train groups; observed {len(train_groups)}")
    dev_groups = {row["original_content_group_id"] for row in dev_units}
    exact_group_overlap = sorted(train_groups & dev_groups)
    train_english = {normalized_key(row["train_english"]) for row in train}
    dev_english = {normalized_key(row["source_english"]) for row in dev_units}
    english_overlap = sorted(train_english & dev_english)
    if exact_group_overlap or english_overlap:
        raise RuntimeError(
            f"Train/development leakage: groups={exact_group_overlap[:5]}, "
            f"normalized_english={english_overlap[:5]}"
        )
    return {
        "train_rows": len(train),
        "train_groups": len(train_groups),
        "development_original_groups": len(dev_groups),
        "exact_group_overlap_count": len(exact_group_overlap),
        "normalized_english_overlap_count": len(english_overlap),
    }


def build_candidate_registry() -> None:
    candidates = [
        {
            "candidate_id": "B0",
            "model_id": "facebook/nllb-200-distilled-600M",
            "revision": "f8d333a098d19b4fd9a8b18f94170487ad3f821d",
            "architecture": "nllb",
            "mode": "paragraph",
            "source_language": "eng_Latn",
            "target_language": "twi_Latn",
            "eligible_for_shortlist": False,
            "role": "historical_baseline",
        },
        {
            "candidate_id": "B1",
            "model_id": "facebook/nllb-200-distilled-600M",
            "revision": "f8d333a098d19b4fd9a8b18f94170487ad3f821d",
            "architecture": "nllb",
            "mode": "sentence",
            "source_language": "eng_Latn",
            "target_language": "twi_Latn",
            "eligible_for_shortlist": False,
            "role": "v3_m12_mechanism_anchor",
        },
        {
            "candidate_id": "B2",
            "model_id": "facebook/nllb-200-distilled-1.3B",
            "revision": "7be3e24664b38ce1cac29b8aeed6911aa0cf0576",
            "architecture": "nllb",
            "mode": "sentence",
            "source_language": "eng_Latn",
            "target_language": "twi_Latn",
            "eligible_for_shortlist": True,
            "role": "nllb_capacity_arm",
        },
        {
            "candidate_id": "B3",
            "model_id": "facebook/nllb-200-3.3B",
            "revision": "a2814a8c92847d0d6aaf7afc9eac24ab57f26151",
            "architecture": "nllb",
            "mode": "sentence",
            "source_language": "eng_Latn",
            "target_language": "twi_Latn",
            "eligible_for_shortlist": True,
            "role": "larger_nllb_ceiling",
        },
        {
            "candidate_id": "B4",
            "model_id": "google/madlad400-3b-mt",
            "revision": "fa184c675da0b5c9e1c8694fccd4e12e2d422094",
            "architecture": "madlad",
            "mode": "sentence",
            "source_language": "eng",
            "target_language": "ak",
            "target_prefix": "<2ak>",
            "eligible_for_shortlist": True,
            "role": "independent_architecture",
        },
    ]
    write_json(
        REGISTRY,
        {
            "artifact": "v3_m13_candidate_registry_frozen_v1",
            "protocol_id": PROTOCOL_ID,
            "frozen_date": "2026-08-08",
            "decoding": {
                "num_beams": 6,
                "early_stopping": True,
                "length_penalty": 1.0,
                "max_new_tokens_per_segment": 192,
                "sampling": False,
                "sentence_segmenter": "pysbd-English",
            },
            "candidates": candidates,
        },
    )


def build_notebook() -> None:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# V3-M13 reverse-MT zero-shot development benchmark\n",
                "This notebook mounts the frozen Drive package, verifies an A100 runtime, installs pinned research dependencies, and runs the prespecified benchmark. It does not read the sealed test or alter production.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Mount the investigator's Drive so all inputs and outputs remain versioned and persistent.\n",
                "from google.colab import drive\n",
                "drive.mount('/content/drive', force_remount=False)\n",
                "\n",
                "# Fail before model download if the required A100 runtime is not active.\n",
                "import torch\n",
                "assert torch.cuda.is_available(), 'A CUDA GPU is required.'\n",
                "gpu_name = torch.cuda.get_device_name(0)\n",
                "assert 'A100' in gpu_name.upper(), f'V3-M13 requires an A100; found {gpu_name}.'\n",
                "print({'gpu': gpu_name, 'torch': torch.__version__})\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Install the exact analysis stack used by the frozen execution script.\n",
                "%pip install -q 'transformers==4.57.1' 'accelerate==1.11.0' 'sacrebleu==2.5.1' 'sentencepiece==0.2.1' 'pysbd==0.3.4' 'pandas==2.2.3' 'numpy==1.26.4' 'scipy==1.15.2' 'matplotlib==3.10.0'\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Execute the frozen benchmark. Atomic per-candidate files make an interrupted run safely resumable.\n",
                "%run /content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_m13_reverse_mt_benchmark_2026-08-08/v3_m13_execute.py\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Display only the prespecified aggregate evidence and shortlist decision.\n",
                "import json, pandas as pd\n",
                "root = '/content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_m13_reverse_mt_benchmark_2026-08-08/execution_outputs'\n",
                "display(pd.read_csv(f'{root}/V3_M13_AGGREGATE_METRICS.csv'))\n",
                "print(json.dumps(json.load(open(f'{root}/V3_M13_SHORTLIST_DECISION.json')), indent=2, ensure_ascii=False))\n",
            ],
        },
    ]
    write_json(
        NOTEBOOK,
        {
            "cells": cells,
            "metadata": {
                "accelerator": "GPU",
                "colab": {"gpuType": "A100", "provenance": []},
                "kernelspec": {"display_name": "Python 3", "name": "python3"},
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        },
    )


def main() -> None:
    for required in (SOURCE_DEV, SOURCE_TRAIN, SOURCE_SCHEMA, PROTOCOL, SCRIPT):
        if not required.is_file():
            raise FileNotFoundError(required)
    FROZEN.mkdir(parents=True, exist_ok=True)
    dev_summary = build_development_units()
    dev_rows = load_csv(DEV_UNITS)
    train_summary = copy_and_audit_training_index(dev_rows)
    shutil.copyfile(SOURCE_SCHEMA, SCHEMA)
    build_candidate_registry()
    build_notebook()

    write_json(
        INPUT_MANIFEST,
        {
            "artifact": "v3_m13_input_manifest_v1",
            "protocol_id": PROTOCOL_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "development": dev_summary,
            "training_leakage_audit": train_summary,
            "m12_response_diagnostic": {
                "rows": 95,
                "permitted_column": "source_english_response",
                "sha256": M12_RESPONSE_SHA256,
                "drive_relative_path": "nllb_v3_m12_selective_rescue_2026-08-08/execution_outputs/V3_M12_ALL_95_CASE_OUTPUTS.csv",
            },
            "sealed_test_opened": False,
            "sealed_test_rows_read": 0,
            "production_changed": False,
        },
    )

    hashed = {
        "protocol": PROTOCOL,
        "execution_script": SCRIPT,
        "candidate_registry": REGISTRY,
        "development_units": DEV_UNITS,
        "train_index": TRAIN_INDEX,
        "protected_schema": SCHEMA,
        "input_manifest": INPUT_MANIFEST,
        "execution_notebook_preexecution": NOTEBOOK,
    }
    write_json(
        PRECOMMIT,
        {
            "artifact": "v3_m13_execution_precommit_v1",
            "protocol_id": PROTOCOL_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "sha256": {name: sha256_file(path) for name, path in hashed.items()},
            "external_input_sha256": {"v3_m12_95_response_file": M12_RESPONSE_SHA256},
            "stop_boundaries": {
                "sealed_test_opened": False,
                "sealed_test_rows_read": 0,
                "human_outcomes_read": False,
                "adaptation_run": False,
                "production_changed": False,
            },
        },
    )

    package_files = [
        PROTOCOL,
        SCRIPT,
        NOTEBOOK,
        REGISTRY,
        INPUT_MANIFEST,
        PRECOMMIT,
        DEV_UNITS,
        TRAIN_INDEX,
        SCHEMA,
        Path(__file__),
    ]
    write_json(
        PACKAGE_MANIFEST,
        {
            "artifact": "v3_m13_preexecution_package_manifest_v1",
            "protocol_id": PROTOCOL_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "files": [
                {
                    "relative_path": path.relative_to(ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in sorted(package_files)
            ],
        },
    )
    print(
        json.dumps(
            {
                "status": "V3_M13_PACKAGE_BUILT",
                "root": str(ROOT),
                "development": dev_summary,
                "training": train_summary,
                "manifest_sha256": sha256_file(PACKAGE_MANIFEST),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

