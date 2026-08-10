"""Execute the frozen V3-M13 reverse-MT zero-shot development benchmark."""

from __future__ import annotations

import gc
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pysbd
import torch
import transformers
from sacrebleu.metrics import BLEU, CHRF
from scipy.stats import binomtest
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


PROJECT_ROOT = Path("/content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation")
ROOT = Path(
    os.environ.get(
        "V3_M13_ROOT",
        PROJECT_ROOT / "nllb_v3_m13_reverse_mt_benchmark_2026-08-08",
    )
)
M12_OUTPUT = (
    PROJECT_ROOT
    / "nllb_v3_m12_selective_rescue_2026-08-08"
    / "execution_outputs"
    / "V3_M12_ALL_95_CASE_OUTPUTS.csv"
)

PROTOCOL_ID = "rnmt-sbllm-v3-m13-reverse-mt-zeroshot-dev-v1"
PROTOCOL = ROOT / "RNMT_SBLLM_V3_M13_REVERSE_MT_ZERO_SHOT_BENCHMARK_PROTOCOL_FROZEN_2026-08-08.md"
PRECOMMIT = ROOT / "V3_M13_EXECUTION_PRECOMMIT_2026-08-08.json"
REGISTRY = ROOT / "V3_M13_CANDIDATE_REGISTRY_FROZEN_2026-08-08.json"
INPUT_MANIFEST = ROOT / "V3_M13_INPUT_MANIFEST_2026-08-08.json"
SCRIPT = ROOT / "v3_m13_execute.py"
NOTEBOOK = ROOT / "V3_M13_REVERSE_MT_ZERO_SHOT_DEV_COLAB_2026-08-08.ipynb"
DEV_UNITS = ROOT / "frozen_inputs" / "V3_M13_DEV_MULTIREFERENCE_460_UNITS_2026-08-08.csv"
TRAIN_INDEX = ROOT / "frozen_inputs" / "V3_M13_TRAIN_ONLY_MULTIVARIANT_INDEX_7240_ROWS_2026-08-08.csv"
SCHEMA_PATH = ROOT / "frozen_inputs" / "V3_M13_PROTECTED_CONCEPT_SCHEMA_FROZEN_COPY_2026-08-08.json"

OUTPUTS = ROOT / "execution_outputs"
RAW = OUTPUTS / "raw"
ENVIRONMENT = OUTPUTS / "environment"
FIGURES = OUTPUTS / "figures"
for directory in (OUTPUTS, RAW, ENVIRONMENT, FIGURES):
    directory.mkdir(parents=True, exist_ok=True)

M12_EXPECTED_SHA256 = "EF50378C45C31E6FF1474D0FE0EC9E80863A58582ABA2EFFAD4C6293F01F2821"
BOOTSTRAP_SEED = 20260808
BOOTSTRAP_REPLICATES = 20_000
REPETITION_THRESHOLD = 0.15
MAX_TOKEN_RUN_THRESHOLD = 4
PROTECTED_NONINFERIORITY = -0.01
QUESTION_NONINFERIORITY = -0.02


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


def write_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def write_csv_atomic(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8", lineterminator="\n")
    temporary.replace(path)


def normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def match_normalize(value: object) -> str:
    value = unicodedata.normalize("NFKC", str(value)).casefold()
    value = value.replace("’", "'").replace("‘", "'")
    value = re.sub(r"[^\w']+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def phrase_present(text: object, phrase: object) -> bool:
    return f" {match_normalize(phrase)} " in f" {match_normalize(text)} "


def unicode_tokens(text: object) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", str(text)).casefold(), re.UNICODE)


def token_f1(reference: object, hypothesis: object) -> float:
    ref = Counter(unicode_tokens(reference))
    hyp = Counter(unicode_tokens(hypothesis))
    if not ref and not hyp:
        return 1.0
    if not ref or not hyp:
        return 0.0
    overlap = sum((ref & hyp).values())
    precision = overlap / sum(hyp.values())
    recall = overlap / sum(ref.values())
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def repetition_diagnostics(english: str, twi: str) -> dict[str, object]:
    tokens = unicode_tokens(twi)
    fourgrams = [tuple(tokens[index : index + 4]) for index in range(max(0, len(tokens) - 3))]
    repeated_fourgram_proportion = (
        1.0 - len(set(fourgrams)) / len(fourgrams) if fourgrams else 0.0
    )
    maximum_run = 0
    current_run = 0
    previous = None
    for token in tokens:
        if token == previous:
            current_run += 1
        else:
            current_run = 1
            previous = token
        maximum_run = max(maximum_run, current_run)
    sentences = [
        normalize(part).casefold()
        for part in re.split(r"(?<=[.!?])\s+", normalize(twi))
        if normalize(part)
    ]
    exact_repeated_sentence = len(sentences) != len(set(sentences))
    detector_positive = bool(
        repeated_fourgram_proportion >= REPETITION_THRESHOLD
        or maximum_run >= MAX_TOKEN_RUN_THRESHOLD
        or exact_repeated_sentence
    )
    english_count = len(unicode_tokens(english))
    return {
        "repeated_fourgram_proportion": repeated_fourgram_proportion,
        "maximum_identical_token_run": maximum_run,
        "exact_repeated_sentence": exact_repeated_sentence,
        "detector_positive": detector_positive,
        "twi_token_count": len(tokens),
        "english_token_count": english_count,
        "twi_to_english_token_ratio": len(tokens) / english_count if english_count else math.nan,
    }


def mapped_target_items(text: str, schema: dict[str, Any]) -> set[str]:
    items: set[str] = set()
    for category, values in schema["akan_source_values"].items():
        if isinstance(values, dict):
            for label, phrases in values.items():
                if any(phrase_present(text, phrase) for phrase in phrases):
                    items.add(f"{category}={label}")
        else:
            if any(phrase_present(text, phrase) for phrase in values):
                items.add(f"{category}=present")
    numbers = set(re.findall(schema["number_regex"], match_normalize(text)))
    items.update(f"number={value}" for value in numbers)
    temporal = {
        term
        for term in schema["temporal_akan"]
        if phrase_present(text, term)
    }
    items.update(f"temporal={value}" for value in temporal)
    return items


def protected_scores(reference: str, hypothesis: str, schema: dict[str, Any]) -> tuple[float, float]:
    reference_items = mapped_target_items(reference, schema)
    hypothesis_items = mapped_target_items(hypothesis, schema)
    if not reference_items:
        return math.nan, math.nan
    overlap = len(reference_items & hypothesis_items)
    recall = overlap / len(reference_items)
    precision = overlap / len(hypothesis_items) if hypothesis_items else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return recall, f1


def marker_set(text: str, pattern: str) -> set[str]:
    return {value.casefold() for value in re.findall(pattern, match_normalize(text))}


def temporal_set(text: str, terms: list[str]) -> set[str]:
    return {term for term in terms if phrase_present(text, term)}


def verify_precommit() -> dict[str, str]:
    precommit = json.loads(PRECOMMIT.read_text(encoding="utf-8"))
    if precommit["protocol_id"] != PROTOCOL_ID:
        raise RuntimeError("Protocol identifier mismatch")
    paths = {
        "protocol": PROTOCOL,
        "execution_script": SCRIPT,
        "candidate_registry": REGISTRY,
        "development_units": DEV_UNITS,
        "train_index": TRAIN_INDEX,
        "protected_schema": SCHEMA_PATH,
        "input_manifest": INPUT_MANIFEST,
    }
    actual = {name: sha256_file(path) for name, path in paths.items()}
    expected = precommit["sha256"]
    mismatch = {
        name: {"expected": expected.get(name), "observed": digest}
        for name, digest in actual.items()
        if expected.get(name, "").upper() != digest
    }
    if mismatch:
        raise RuntimeError(f"Frozen package mismatch: {json.dumps(mismatch, indent=2)}")
    if sha256_file(M12_OUTPUT) != M12_EXPECTED_SHA256:
        raise RuntimeError("The frozen V3-M12 95-response file hash changed")
    required_boundaries = {
        "sealed_test_opened": False,
        "sealed_test_rows_read": 0,
        "human_outcomes_read": False,
        "adaptation_run": False,
        "production_changed": False,
    }
    if precommit["stop_boundaries"] != required_boundaries:
        raise RuntimeError("V3-M13 stop boundaries changed")
    return actual


def verify_data(dev: pd.DataFrame, train: pd.DataFrame, responses: pd.DataFrame) -> None:
    if len(dev) != 460 or dev["eval_unit_id"].nunique() != 460:
        raise RuntimeError("Development identity is not 460 unique units")
    if dev["original_content_group_id"].nunique() != 458:
        raise RuntimeError("Development cluster identity is not 458 groups")
    if len(train) != 7240 or train["content_group_id"].nunique() != 2139:
        raise RuntimeError("Training identity is not 7,240 rows / 2,139 groups")
    if len(responses) != 95 or responses["review_id"].nunique() != 95:
        raise RuntimeError("Response diagnostic identity is not 95 unique rows")
    if dev["source_english"].map(normalize).eq("").any():
        raise RuntimeError("Empty development source")
    if responses["source_english_response"].map(normalize).eq("").any():
        raise RuntimeError("Empty response source")
    group_overlap = set(train["content_group_id"].astype(str)) & set(
        dev["original_content_group_id"].astype(str)
    )
    train_english = {match_normalize(value) for value in train["train_english"]}
    dev_english = {match_normalize(value) for value in dev["source_english"]}
    if group_overlap or train_english & dev_english:
        raise RuntimeError("Train/development leakage detected at execution")


def segment_documents(documents: list[str], mode: str) -> tuple[list[str], list[list[int]]]:
    if mode == "paragraph":
        return documents, [[index] for index in range(len(documents))]
    segmenter = pysbd.Segmenter(language="en", clean=False)
    segments: list[str] = []
    mapping: list[list[int]] = []
    for document in documents:
        indices: list[int] = []
        parts = [normalize(value) for value in segmenter.segment(normalize(document)) if normalize(value)]
        if not parts:
            parts = [normalize(document)]
        for part in parts:
            indices.append(len(segments))
            segments.append(part)
        mapping.append(indices)
    return segments, mapping


def translate_candidate(
    candidate: dict[str, Any],
    documents: list[str],
) -> tuple[list[str], dict[str, object]]:
    candidate_id = candidate["candidate_id"]
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    load_started = time.perf_counter()
    tokenizer_kwargs: dict[str, Any] = {"revision": candidate["revision"]}
    if candidate["architecture"] == "nllb":
        tokenizer_kwargs["src_lang"] = candidate["source_language"]
    tokenizer = AutoTokenizer.from_pretrained(candidate["model_id"], **tokenizer_kwargs)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        candidate["model_id"],
        revision=candidate["revision"],
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    ).to("cuda")
    model.eval()
    load_seconds = time.perf_counter() - load_started

    segments, mapping = segment_documents(documents, candidate["mode"])
    if candidate["architecture"] == "madlad":
        model_inputs = [f"{candidate['target_prefix']} {segment}" for segment in segments]
        batch_size = 8
        forced_bos_token_id = None
    else:
        model_inputs = segments
        forced_bos_token_id = tokenizer.convert_tokens_to_ids(candidate["target_language"])
        if forced_bos_token_id in (None, tokenizer.unk_token_id):
            raise RuntimeError(f"{candidate_id}: missing target language token")
        size_hint = candidate["model_id"]
        batch_size = 32 if "600M" in size_hint else (16 if "1.3B" in size_hint else 8)

    translations: list[str] = []
    generation_started = time.perf_counter()
    for start in range(0, len(model_inputs), batch_size):
        batch = model_inputs[start : start + batch_size]
        encoded = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        ).to("cuda")
        generation_kwargs: dict[str, Any] = {
            "num_beams": 6,
            "do_sample": False,
            "early_stopping": True,
            "length_penalty": 1.0,
            "max_new_tokens": 192,
        }
        if forced_bos_token_id is not None:
            generation_kwargs["forced_bos_token_id"] = forced_bos_token_id
        with torch.inference_mode():
            generated = model.generate(**encoded, **generation_kwargs)
        translations.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
    torch.cuda.synchronize()
    generation_seconds = time.perf_counter() - generation_started

    documents_out = [normalize(" ".join(translations[index] for index in indices)) for indices in mapping]
    if len(documents_out) != len(documents):
        raise RuntimeError(f"{candidate_id}: reconstruction length mismatch")
    record = {
        "candidate_id": candidate_id,
        "model_id": candidate["model_id"],
        "revision": candidate["revision"],
        "mode": candidate["mode"],
        "document_count": len(documents),
        "segment_count": len(segments),
        "load_seconds": load_seconds,
        "generation_seconds": generation_seconds,
        "peak_gpu_memory_gib": torch.cuda.max_memory_allocated() / (1024**3),
        "completed_at_utc": utc_now(),
    }
    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    return documents_out, record


def validate_resumable_output(path: Path, candidate_id: str, expected_items: list[str]) -> pd.DataFrame | None:
    if not path.is_file():
        return None
    frame = pd.read_csv(path)
    if (
        len(frame) == len(expected_items)
        and frame["item_id"].astype(str).tolist() == expected_items
        and set(frame["candidate_id"].astype(str)) == {candidate_id}
        and not frame["translation_twi"].isna().any()
    ):
        return frame
    raise RuntimeError(f"Invalid resumable candidate output: {path}")


def evaluate_development(
    dev: pd.DataFrame,
    translations: pd.DataFrame,
    schema: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, float]]:
    joined = dev.merge(
        translations.loc[translations["dataset"].eq("development"), ["item_id", "translation_twi"]],
        left_on="eval_unit_id",
        right_on="item_id",
        validate="one_to_one",
    )
    chrf = CHRF(word_order=2)
    bleu = BLEU(effective_order=True)
    per_unit: list[dict[str, object]] = []
    all_references: list[list[str]] = []
    for row in joined.itertuples(index=False):
        references = json.loads(row.references_twi_json)
        hypothesis = normalize(row.translation_twi)
        reference_chrf = [chrf.sentence_score(hypothesis, [reference]).score for reference in references]
        reference_bleu = [bleu.sentence_score(hypothesis, [reference]).score for reference in references]
        token_scores = [token_f1(reference, hypothesis) for reference in references]
        protected = [protected_scores(reference, hypothesis, schema) for reference in references]
        protected_recalls = [value[0] for value in protected if not math.isnan(value[0])]
        protected_f1s = [value[1] for value in protected if not math.isnan(value[1])]
        number_hyp = marker_set(hypothesis, schema["number_regex"])
        number_agreement = max(
            float(number_hyp == marker_set(reference, schema["number_regex"]))
            for reference in references
        )
        temporal_hyp = temporal_set(hypothesis, schema["temporal_akan"])
        temporal_agreement = max(
            float(temporal_hyp == temporal_set(reference, schema["temporal_akan"]))
            for reference in references
        )
        source_tokens = len(unicode_tokens(row.source_english))
        target_tokens = len(unicode_tokens(hypothesis))
        per_unit.append(
            {
                "eval_unit_id": row.eval_unit_id,
                "original_content_group_id": row.original_content_group_id,
                "source_english": row.source_english,
                "translation_twi": hypothesis,
                "reference_count": len(references),
                "best_sentence_chrf_pp": max(reference_chrf),
                "best_sentence_bleu": max(reference_bleu),
                "best_token_f1": max(token_scores),
                "best_protected_recall": max(protected_recalls) if protected_recalls else math.nan,
                "best_protected_f1": max(protected_f1s) if protected_f1s else math.nan,
                "number_marker_agreement": number_agreement,
                "temporal_marker_agreement": temporal_agreement,
                "is_question": "?" in normalize(row.source_english),
                "question_mark_retained": float("?" in hypothesis) if "?" in normalize(row.source_english) else math.nan,
                "empty_output": not bool(hypothesis),
                "output_source_token_ratio": target_tokens / source_tokens if source_tokens else math.nan,
            }
        )
        all_references.append(references)
    frame = pd.DataFrame(per_unit)
    hypotheses = frame["translation_twi"].tolist()
    max_references = max(len(values) for values in all_references)
    reference_streams = [
        [values[index] if index < len(values) else values[0] for values in all_references]
        for index in range(max_references)
    ]
    aggregate = {
        "corpus_chrf_pp": chrf.corpus_score(hypotheses, reference_streams).score,
        "corpus_sacrebleu": bleu.corpus_score(hypotheses, reference_streams).score,
        "mean_best_sentence_chrf_pp": frame["best_sentence_chrf_pp"].mean(),
        "mean_best_token_f1": frame["best_token_f1"].mean(),
        "mean_best_protected_recall": frame["best_protected_recall"].mean(),
        "mean_best_protected_f1": frame["best_protected_f1"].mean(),
        "number_marker_agreement": frame["number_marker_agreement"].mean(),
        "temporal_marker_agreement": frame["temporal_marker_agreement"].mean(),
        "question_mark_retention": frame.loc[frame["is_question"], "question_mark_retained"].mean(),
        "empty_development_outputs": int(frame["empty_output"].sum()),
        "mean_development_output_source_token_ratio": frame["output_source_token_ratio"].mean(),
    }
    return frame, aggregate


def evaluate_responses(responses: pd.DataFrame, translations: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    joined = responses.merge(
        translations.loc[translations["dataset"].eq("response"), ["item_id", "translation_twi"]],
        left_on="review_id",
        right_on="item_id",
        validate="one_to_one",
    )
    rows: list[dict[str, object]] = []
    for row in joined.itertuples(index=False):
        diagnostic = repetition_diagnostics(row.source_english_response, row.translation_twi)
        rows.append(
            {
                "review_id": row.review_id,
                "record_uid": row.record_uid,
                "content_group_id": row.content_group_id,
                "source_english_response": row.source_english_response,
                "translation_twi": row.translation_twi,
                **diagnostic,
                "empty_output": not bool(normalize(row.translation_twi)),
            }
        )
    frame = pd.DataFrame(rows)
    aggregate = {
        "response_detector_positive_count": int(frame["detector_positive"].sum()),
        "response_exact_repeated_sentence_count": int(frame["exact_repeated_sentence"].sum()),
        "mean_response_repeated_fourgram_proportion": frame["repeated_fourgram_proportion"].mean(),
        "maximum_response_identical_token_run": int(frame["maximum_identical_token_run"].max()),
        "mean_response_output_source_token_ratio": frame["twi_to_english_token_ratio"].mean(),
        "empty_response_outputs": int(frame["empty_output"].sum()),
    }
    return frame, aggregate


def cluster_bootstrap_difference(
    candidate: pd.DataFrame,
    baseline: pd.DataFrame,
    metric: str,
    seed_offset: int,
) -> dict[str, float]:
    paired = candidate[["eval_unit_id", "original_content_group_id", metric]].merge(
        baseline[["eval_unit_id", metric]],
        on="eval_unit_id",
        suffixes=("_candidate", "_baseline"),
        validate="one_to_one",
    )
    paired["difference"] = paired[f"{metric}_candidate"] - paired[f"{metric}_baseline"]
    cluster_values = paired.groupby("original_content_group_id")["difference"].mean().dropna().to_numpy()
    if not len(cluster_values):
        return {"difference": math.nan, "ci_low": math.nan, "ci_high": math.nan}
    rng = np.random.default_rng(BOOTSTRAP_SEED + seed_offset)
    samples = rng.choice(cluster_values, size=(BOOTSTRAP_REPLICATES, len(cluster_values)), replace=True).mean(axis=1)
    return {
        "difference": float(cluster_values.mean()),
        "ci_low": float(np.quantile(samples, 0.025)),
        "ci_high": float(np.quantile(samples, 0.975)),
    }


def build_figure(metrics: pd.DataFrame) -> None:
    order = metrics["candidate_id"].tolist()
    colors = ["#6b7280", "#1d4ed8", "#0f766e", "#7c3aed", "#b45309"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    panels = [
        ("corpus_chrf_pp", "Multi-reference chrF++", False),
        ("mean_best_protected_recall", "Protected-concept recall", False),
        ("response_detector_positive_count", "Response repetition flags", True),
        ("question_mark_retention", "Question-mark retention", False),
    ]
    for axis, (column, title, integer) in zip(axes.flat, panels):
        values = metrics[column].astype(float).tolist()
        bars = axis.bar(order, values, color=colors)
        axis.set_title(title)
        axis.grid(axis="y", alpha=0.2)
        for bar, value in zip(bars, values):
            label = f"{int(value)}" if integer else f"{value:.3f}"
            axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), label, ha="center", va="bottom", fontsize=9)
    fig.suptitle("V3-M13 development-only reverse-MT zero-shot screen", fontsize=15)
    fig.text(0.5, 0.01, "B0: paragraph NLLB-600M; B1: sentence NLLB-600M anchor; B2/B3: larger NLLB; B4: MADLAD-3B", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(FIGURES / "V3_M13_ZERO_SHOT_SCREEN.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    random.seed(BOOTSTRAP_SEED)
    np.random.seed(BOOTSTRAP_SEED)
    transformers.set_seed(BOOTSTRAP_SEED)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HOME"] = "/content/hf_cache"
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.set_float32_matmul_precision("high")

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA GPU is required")
    gpu_name = torch.cuda.get_device_name(0)
    if "A100" not in gpu_name.upper():
        raise RuntimeError(f"V3-M13 requires an A100; found {gpu_name}")

    observed_hashes = verify_precommit()
    dev = pd.read_csv(DEV_UNITS)
    train = pd.read_csv(TRAIN_INDEX)
    responses_all = pd.read_csv(M12_OUTPUT)
    permitted_response_columns = [
        "review_id",
        "record_uid",
        "content_group_id",
        "speaker_code",
        "theme_key",
        "source_english_response",
    ]
    missing = set(permitted_response_columns) - set(responses_all.columns)
    if missing:
        raise RuntimeError(f"Missing permitted V3-M12 response columns: {sorted(missing)}")
    responses = responses_all[permitted_response_columns].copy()
    del responses_all
    verify_data(dev, train, responses)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    package_versions = {
        package: importlib.metadata.version(package)
        for package in (
            "transformers",
            "accelerate",
            "sacrebleu",
            "sentencepiece",
            "pysbd",
            "pandas",
            "numpy",
            "scipy",
            "matplotlib",
        )
    }
    environment = {
        "protocol_id": PROTOCOL_ID,
        "started_at_utc": utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "gpu": gpu_name,
        "gpu_memory_gib": torch.cuda.get_device_properties(0).total_memory / (1024**3),
        "package_versions": package_versions,
        "verified_input_sha256": observed_hashes,
        "external_m12_response_sha256": sha256_file(M12_OUTPUT),
        "sealed_test_opened": False,
        "sealed_test_rows_read": 0,
        "human_outcomes_read": False,
        "adaptation_run": False,
        "production_changed": False,
    }
    write_json(ENVIRONMENT / "V3_M13_ENVIRONMENT.json", environment)
    (ENVIRONMENT / "pip_freeze.txt").write_text(
        subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True),
        encoding="utf-8",
    )

    item_ids = [f"DEV::{value}" for value in dev["eval_unit_id"].astype(str)] + [
        f"RESP::{value}" for value in responses["review_id"].astype(str)
    ]
    documents = dev["source_english"].map(normalize).tolist() + responses[
        "source_english_response"
    ].map(normalize).tolist()

    aggregate_rows: list[dict[str, object]] = []
    development_frames: dict[str, pd.DataFrame] = {}
    response_frames: dict[str, pd.DataFrame] = {}
    completion_records: dict[str, dict[str, object]] = {}
    for candidate in registry["candidates"]:
        candidate_id = candidate["candidate_id"]
        raw_path = RAW / f"V3_M13_{candidate_id}_ALL_TRANSLATIONS.csv"
        raw = validate_resumable_output(raw_path, candidate_id, item_ids)
        completion_path = RAW / f"V3_M13_{candidate_id}_COMPLETION.json"
        if raw is None:
            translated, completion = translate_candidate(candidate, documents)
            raw = pd.DataFrame(
                {
                    "candidate_id": candidate_id,
                    "model_id": candidate["model_id"],
                    "revision": candidate["revision"],
                    "mode": candidate["mode"],
                    "dataset": ["development"] * len(dev) + ["response"] * len(responses),
                    "item_id": item_ids,
                    "source_english": documents,
                    "translation_twi": translated,
                }
            )
            write_csv_atomic(raw_path, raw)
            completion["raw_output_sha256"] = sha256_file(raw_path)
            write_json(completion_path, completion)
        else:
            completion = json.loads(completion_path.read_text(encoding="utf-8"))
            if completion.get("raw_output_sha256") != sha256_file(raw_path):
                raise RuntimeError(f"{candidate_id}: resumable output hash mismatch")
            completion["resumed"] = True
        completion_records[candidate_id] = completion

        raw_for_join = raw.copy()
        raw_for_join["item_id"] = raw_for_join["item_id"].str.replace(r"^(DEV|RESP)::", "", regex=True)
        dev_frame, dev_aggregate = evaluate_development(dev, raw_for_join, schema)
        response_frame, response_aggregate = evaluate_responses(responses, raw_for_join)
        dev_frame.insert(0, "candidate_id", candidate_id)
        response_frame.insert(0, "candidate_id", candidate_id)
        development_frames[candidate_id] = dev_frame
        response_frames[candidate_id] = response_frame
        aggregate_rows.append(
            {
                "candidate_id": candidate_id,
                "model_id": candidate["model_id"],
                "revision": candidate["revision"],
                "mode": candidate["mode"],
                **dev_aggregate,
                **response_aggregate,
                "load_seconds": completion["load_seconds"],
                "generation_seconds": completion["generation_seconds"],
                "peak_gpu_memory_gib": completion["peak_gpu_memory_gib"],
            }
        )
        print(
            json.dumps(
                {
                    "completed_candidate": candidate_id,
                    "corpus_chrf_pp": dev_aggregate["corpus_chrf_pp"],
                    "protected_recall": dev_aggregate["mean_best_protected_recall"],
                    "response_repetition_flags": response_aggregate["response_detector_positive_count"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    aggregate = pd.DataFrame(aggregate_rows)
    write_csv_atomic(OUTPUTS / "V3_M13_AGGREGATE_METRICS.csv", aggregate)
    write_csv_atomic(
        OUTPUTS / "V3_M13_DEVELOPMENT_UNIT_METRICS.csv",
        pd.concat(development_frames.values(), ignore_index=True),
    )
    write_csv_atomic(
        OUTPUTS / "V3_M13_RESPONSE_DIAGNOSTICS.csv",
        pd.concat(response_frames.values(), ignore_index=True),
    )

    baseline_dev = development_frames["B1"]
    baseline_response = response_frames["B1"]
    pairwise_rows: list[dict[str, object]] = []
    for index, candidate_id in enumerate(["B0", "B2", "B3", "B4"], start=1):
        row: dict[str, object] = {"candidate_id": candidate_id, "anchor_id": "B1"}
        for metric_index, metric in enumerate(
            (
                "best_sentence_chrf_pp",
                "best_token_f1",
                "best_protected_recall",
                "question_mark_retained",
            ),
            start=1,
        ):
            result = cluster_bootstrap_difference(
                development_frames[candidate_id],
                baseline_dev,
                metric,
                seed_offset=index * 100 + metric_index,
            )
            row[f"{metric}_difference"] = result["difference"]
            row[f"{metric}_ci_low"] = result["ci_low"]
            row[f"{metric}_ci_high"] = result["ci_high"]
        paired_response = response_frames[candidate_id][["review_id", "detector_positive"]].merge(
            baseline_response[["review_id", "detector_positive"]],
            on="review_id",
            suffixes=("_candidate", "_anchor"),
            validate="one_to_one",
        )
        candidate_only = int(
            (paired_response["detector_positive_candidate"] & ~paired_response["detector_positive_anchor"]).sum()
        )
        anchor_only = int(
            (~paired_response["detector_positive_candidate"] & paired_response["detector_positive_anchor"]).sum()
        )
        discordant = candidate_only + anchor_only
        row["response_repetition_candidate_only"] = candidate_only
        row["response_repetition_anchor_only"] = anchor_only
        row["response_repetition_exact_p"] = (
            float(binomtest(candidate_only, discordant, p=0.5, alternative="two-sided").pvalue)
            if discordant
            else 1.0
        )
        pairwise_rows.append(row)
    pairwise = pd.DataFrame(pairwise_rows)
    write_csv_atomic(OUTPUTS / "V3_M13_PAIRED_COMPARISONS_VS_B1.csv", pairwise)

    metric_by_id = aggregate.set_index("candidate_id").to_dict(orient="index")
    baseline = metric_by_id["B1"]
    eligibility: dict[str, dict[str, object]] = {}
    eligible: list[str] = []
    for candidate_id in ("B2", "B3", "B4"):
        value = metric_by_id[candidate_id]
        checks = {
            "all_outputs_nonempty": (
                int(value["empty_development_outputs"]) == 0
                and int(value["empty_response_outputs"]) == 0
            ),
            "response_repetition_not_worse_than_b1": (
                int(value["response_detector_positive_count"])
                <= int(baseline["response_detector_positive_count"])
            ),
            "protected_recall_noninferior_to_b1_minus_0_01": (
                float(value["mean_best_protected_recall"])
                - float(baseline["mean_best_protected_recall"])
                >= PROTECTED_NONINFERIORITY
            ),
            "question_retention_noninferior_to_b1_minus_0_02": (
                float(value["question_mark_retention"])
                - float(baseline["question_mark_retention"])
                >= QUESTION_NONINFERIORITY
            ),
        }
        is_eligible = all(checks.values())
        eligibility[candidate_id] = {"eligible": is_eligible, "checks": checks}
        if is_eligible:
            eligible.append(candidate_id)
    ranked = sorted(
        eligible,
        key=lambda candidate_id: (
            -float(metric_by_id[candidate_id]["corpus_chrf_pp"]),
            -float(metric_by_id[candidate_id]["mean_best_protected_recall"]),
            -float(metric_by_id[candidate_id]["corpus_sacrebleu"]),
            float(metric_by_id[candidate_id]["generation_seconds"]),
        ),
    )
    shortlist = ranked[:2]
    decision = "SHORTLIST_READY_FOR_SEPARATELY_FROZEN_BLIND_AUDIT" if len(shortlist) == 2 else "INSUFFICIENT_ALTERNATIVES"
    decision_record = {
        "artifact": "v3_m13_shortlist_decision_v1",
        "protocol_id": PROTOCOL_ID,
        "created_at_utc": utc_now(),
        "decision": decision,
        "blind_audit_anchor": "B1",
        "eligible_alternatives_ranked": ranked,
        "shortlist": shortlist,
        "eligibility": eligibility,
        "sealed_test_opened": False,
        "sealed_test_rows_read": 0,
        "human_outcomes_read": False,
        "adaptation_run": False,
        "production_changed": False,
        "claim_boundary": "Development-only automatic model screening; not deployment or clinical-safety evidence.",
    }
    write_json(OUTPUTS / "V3_M13_SHORTLIST_DECISION.json", decision_record)
    build_figure(aggregate)

    completed_files = [path for path in OUTPUTS.rglob("*") if path.is_file() and path.name != "V3_M13_SHA256_MANIFEST.json"]
    write_json(
        OUTPUTS / "V3_M13_SHA256_MANIFEST.json",
        {
            "artifact": "v3_m13_execution_sha256_manifest_v1",
            "protocol_id": PROTOCOL_ID,
            "created_at_utc": utc_now(),
            "files": [
                {
                    "relative_path": path.relative_to(ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in sorted(completed_files)
            ],
            "sealed_test_opened": False,
            "production_changed": False,
        },
    )
    print(json.dumps(decision_record, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

