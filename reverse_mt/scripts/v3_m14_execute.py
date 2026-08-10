"""Execute the frozen V3-M14 B1-versus-B3 end-to-end reverse-MT gate."""

from __future__ import annotations

import gc
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pysbd
import torch
import transformers
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


PROJECT_ROOT = Path("/content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation")
ROOT = Path(os.environ.get("V3_M14_ROOT", PROJECT_ROOT / "nllb_v3_m14_end_to_end_reverse_mt_2026-08-09"))
PROTOCOL_ID = "rnmt-sbllm-v3-m14-end-to-end-reverse-mt-gate-v1"
PROTOCOL = ROOT / "RNMT_SBLLM_V3_M14_END_TO_END_REVERSE_MT_GATE_PROTOCOL_FROZEN_2026-08-09.md"
PRECOMMIT = ROOT / "V3_M14_EXECUTION_PRECOMMIT_2026-08-09.json"
REGISTRY = ROOT / "V3_M14_CANDIDATE_REGISTRY_FROZEN_2026-08-09.json"
INPUTS = ROOT / "frozen_inputs" / "V3_M14_72_CASE_REVERSE_MT_INPUTS_2026-08-09.csv"
INPUT_MANIFEST = ROOT / "frozen_inputs" / "V3_M14_72_CASE_INPUT_MANIFEST_2026-08-09.json"
SCRIPT = ROOT / "v3_m14_execute.py"
OUTPUTS = ROOT / "execution_outputs"
RAW = OUTPUTS / "raw"
ENVIRONMENT = OUTPUTS / "environment"
for directory in (OUTPUTS, RAW, ENVIRONMENT):
    directory.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8", lineterminator="\n")
    temporary.replace(path)


def normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value or "")).split())


def tokens(value: object) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", str(value or "")).casefold(), re.UNICODE)


def repetition_diagnostics(english: str, twi: str) -> dict[str, object]:
    values = tokens(twi)
    fourgrams = [tuple(values[i:i + 4]) for i in range(max(0, len(values) - 3))]
    repeated_fourgram_proportion = 1 - len(set(fourgrams)) / len(fourgrams) if fourgrams else 0.0
    maximum_run = 0
    current = 0
    previous = None
    for value in values:
        if value == previous:
            current += 1
        else:
            previous = value
            current = 1
        maximum_run = max(maximum_run, current)
    source_count = len(tokens(english))
    return {
        "repeated_fourgram_proportion": repeated_fourgram_proportion,
        "maximum_identical_token_run": maximum_run,
        "detector_positive": bool(repeated_fourgram_proportion >= 0.15 or maximum_run >= 4),
        "english_token_count": source_count,
        "twi_token_count": len(values),
        "twi_to_english_token_ratio": len(values) / source_count if source_count else math.nan,
    }


def verify_package() -> dict[str, str]:
    precommit = json.loads(PRECOMMIT.read_text(encoding="utf-8"))
    if precommit["protocol_id"] != PROTOCOL_ID or precommit["frozen_before_execution"] is not True:
        raise RuntimeError("Invalid V3-M14 precommit")
    paths = {
        "protocol": PROTOCOL,
        "execution_script": SCRIPT,
        "candidate_registry": REGISTRY,
        "input_ledger": INPUTS,
        "input_manifest": INPUT_MANIFEST,
    }
    actual = {key: sha256_file(path) for key, path in paths.items()}
    mismatches = {
        key: {"expected": precommit["sha256"].get(key), "observed": value}
        for key, value in actual.items()
        if precommit["sha256"].get(key, "").upper() != value
    }
    if mismatches:
        raise RuntimeError(f"Frozen package mismatch: {json.dumps(mismatches, indent=2)}")
    expected_boundaries = {
        "sealed_test_opened": False,
        "sealed_test_rows_read": 0,
        "human_outcomes_read": False,
        "training_or_parameter_update": False,
        "production_changed": False,
    }
    if precommit["stop_boundaries"] != expected_boundaries:
        raise RuntimeError("Stop boundaries changed")
    return actual


def segment_documents(documents: list[str]) -> tuple[list[str], list[list[int]]]:
    segmenter = pysbd.Segmenter(language="en", clean=False)
    segments: list[str] = []
    mapping: list[list[int]] = []
    for document in documents:
        parts = [normalize(part) for part in segmenter.segment(normalize(document)) if normalize(part)]
        if not parts:
            parts = [normalize(document)]
        indexes: list[int] = []
        for part in parts:
            indexes.append(len(segments))
            segments.append(part)
        mapping.append(indexes)
    return segments, mapping


def translate_candidate(candidate: dict[str, Any], audit_ids: list[str], documents: list[str]) -> tuple[pd.DataFrame, dict[str, object]]:
    candidate_id = candidate["candidate_id"]
    resumable = RAW / f"V3_M14_{candidate_id}_TRANSLATIONS.csv"
    if resumable.is_file():
        frame = pd.read_csv(resumable, dtype=str).fillna("")
        if len(frame) == 72 and frame["audit_id"].tolist() == audit_ids and frame["translation_twi"].str.strip().ne("").all():
            completion = json.loads((RAW / f"V3_M14_{candidate_id}_COMPLETION.json").read_text(encoding="utf-8"))
            return frame, completion
        raise RuntimeError(f"Invalid resumable output for {candidate_id}")

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    token = os.environ.get("HF_TOKEN") or None
    tokenizer = AutoTokenizer.from_pretrained(
        candidate["model_id"], revision=candidate["revision"], src_lang=candidate["source_language"], token=token
    )
    load_started = time.perf_counter()
    model = AutoModelForSeq2SeqLM.from_pretrained(
        candidate["model_id"], revision=candidate["revision"], torch_dtype=torch.float16,
        low_cpu_mem_usage=True, token=token
    ).to("cuda")
    model.eval()
    load_seconds = time.perf_counter() - load_started
    forced_bos = tokenizer.convert_tokens_to_ids(candidate["target_language"])
    if forced_bos in (None, tokenizer.unk_token_id):
        raise RuntimeError(f"{candidate_id}: missing target language token")

    segments, mapping = segment_documents(documents)
    batch_size = 32 if "600M" in candidate["model_id"] else 8
    translated_segments: list[str] = []
    generation_started = time.perf_counter()
    for start in range(0, len(segments), batch_size):
        batch = segments[start:start + batch_size]
        encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=512).to("cuda")
        with torch.inference_mode():
            generated = model.generate(
                **encoded, forced_bos_token_id=forced_bos, num_beams=6, do_sample=False,
                early_stopping=True, length_penalty=1.0, max_new_tokens=192
            )
        translated_segments.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
    torch.cuda.synchronize()
    generation_seconds = time.perf_counter() - generation_started
    documents_out = [normalize(" ".join(translated_segments[index] for index in indexes)) for indexes in mapping]
    if len(documents_out) != 72 or any(not value for value in documents_out):
        raise RuntimeError(f"{candidate_id}: incomplete reconstruction")

    rows = []
    for audit_id, english, twi in zip(audit_ids, documents, documents_out):
        rows.append({
            "audit_id": audit_id,
            "candidate_id": candidate_id,
            "model_id": candidate["model_id"],
            "revision": candidate["revision"],
            "source_english": english,
            "translation_twi": twi,
            "source_sha256": sha256_text(english),
            "translation_sha256": sha256_text(twi),
            **repetition_diagnostics(english, twi),
        })
    frame = pd.DataFrame(rows)
    write_csv(resumable, frame)
    completion = {
        "artifact": "v3_m14_candidate_completion_v1",
        "protocol_id": PROTOCOL_ID,
        "candidate_id": candidate_id,
        "model_id": candidate["model_id"],
        "revision": candidate["revision"],
        "document_count": 72,
        "segment_count": len(segments),
        "load_seconds": load_seconds,
        "generation_seconds": generation_seconds,
        "peak_gpu_memory_gib": torch.cuda.max_memory_allocated() / (1024 ** 3),
        "output_sha256": sha256_file(resumable),
        "completed_at_utc": utc_now(),
    }
    write_json(RAW / f"V3_M14_{candidate_id}_COMPLETION.json", completion)
    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    return frame, completion


def main() -> None:
    started = utc_now()
    verified = verify_package()
    gpu = subprocess.run(["nvidia-smi", "-L"], check=True, capture_output=True, text=True).stdout.strip()
    if "A100" not in gpu:
        raise RuntimeError(f"A100 required; observed: {gpu}")
    inputs = pd.read_csv(INPUTS, dtype=str).fillna("")
    if len(inputs) != 72 or inputs["audit_id"].nunique() != 72:
        raise RuntimeError("Expected 72 unique frozen cases")
    if not inputs["sbllm_response_english"].str.strip().ne("").all():
        raise RuntimeError("Blank frozen SBLLM response")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    candidates = registry["candidates"]
    if [candidate["candidate_id"] for candidate in candidates] != ["B1", "B3"]:
        raise RuntimeError("Candidate registry order changed")

    audit_ids = inputs["audit_id"].tolist()
    documents = inputs["sbllm_response_english"].tolist()
    frames = []
    completions = []
    for candidate in candidates:
        frame, completion = translate_candidate(candidate, audit_ids, documents)
        frames.append(frame)
        completions.append(completion)
    combined = pd.concat(frames, ignore_index=True)
    if len(combined) != 144 or combined.groupby("audit_id")["candidate_id"].nunique().ne(2).any():
        raise RuntimeError("Incomplete paired output")
    combined_path = OUTPUTS / "V3_M14_ALL_TRANSLATIONS.csv"
    write_csv(combined_path, combined)

    environment = {
        "artifact": "v3_m14_environment_v1",
        "created_at_utc": utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "gpu": gpu,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "pysbd": importlib.metadata.version("pysbd"),
        "cuda": torch.version.cuda,
    }
    write_json(ENVIRONMENT / "V3_M14_ENVIRONMENT.json", environment)
    subprocess.run([sys.executable, "-m", "pip", "freeze"], check=True, stdout=(ENVIRONMENT / "pip_freeze.txt").open("w", encoding="utf-8"))
    manifest = {
        "artifact": "v3_m14_execution_completion_v1",
        "protocol_id": PROTOCOL_ID,
        "started_at_utc": started,
        "completed_at_utc": utc_now(),
        "verified_preexecution_sha256": verified,
        "candidate_completions": completions,
        "row_count": 144,
        "paired_case_count": 72,
        "repetition_detector_positive_counts": combined.groupby("candidate_id")["detector_positive"].sum().astype(int).to_dict(),
        "sha256": {
            "all_translations": sha256_file(combined_path),
            "environment": sha256_file(ENVIRONMENT / "V3_M14_ENVIRONMENT.json"),
            "pip_freeze": sha256_file(ENVIRONMENT / "pip_freeze.txt"),
        },
        "sealed_test_opened": False,
        "human_outcomes_read": False,
        "training_or_parameter_update": False,
        "production_changed": False,
    }
    write_json(OUTPUTS / "V3_M14_EXECUTION_COMPLETION.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
