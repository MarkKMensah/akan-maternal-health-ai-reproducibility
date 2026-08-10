"""Execute the frozen V3-M9 development-only causal propagation experiment."""

from __future__ import annotations

import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import transformers
from peft import PeftModel
from sacrebleu.metrics import BLEU, CHRF
from scipy.stats import binomtest
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


# Bind every study path to the versioned project tree on Google Drive.
PROJECT_ROOT = Path("/content/drive/MyDrive/Akan_ASR_PhD_Experiments")
M1_ROOT = PROJECT_ROOT / "03_Adaptation" / "nllb_v3_2026-08-04"
M1_RUN = M1_ROOT / "runs" / "20260804T191924Z_nllb_v3_lora_dev_v1"
M1_INPUTS = M1_ROOT / "inputs"
MMS_ROOT = PROJECT_ROOT / "03_Adaptation" / "mms_maternal_adaptation_2026-08-06"
MMS_RUN = MMS_ROOT / "runs" / "20260807_mms_maternal_adapter_confirm_seed20260809"
V3_M9_ROOT = PROJECT_ROOT / "03_Adaptation" / "nllb_v3_m9_2026-08-07"
RUN_DIR = V3_M9_ROOT / "runs" / "20260807_v3_m9_adapted_asr_causal_propagation_dev_v1"
OUTPUT_DIR = RUN_DIR / "outputs"
FIGURE_DIR = RUN_DIR / "figures"
ENV_DIR = RUN_DIR / "environment"
for directory in (OUTPUT_DIR, FIGURE_DIR, ENV_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Freeze model, decoder, resampling and gate constants before reading outcomes.
PROTOCOL_ID = "nllb-v3-m9-adapted-asr-causal-propagation-dev-v1"
NLLB_MODEL_ID = "facebook/nllb-200-distilled-600M"
NLLB_REVISION = "f8d333a098d19b4fd9a8b18f94170487ad3f821d"
SOURCE_LANG = "twi_Latn"
TARGET_LANG = "eng_Latn"
MAX_NEW_TOKENS = 192
BOOTSTRAP_SEED = 20260807
BOOTSTRAP_REPLICATES = 20_000
CHRF_MIN_GAIN = 1.00
BLEU_NONINFERIORITY = -0.50
TOKEN_F1_NONINFERIORITY = -0.005
PROTECTED_RECALL_NONINFERIORITY = -0.005
NUMBER_AGREEMENT_NONINFERIORITY = -0.01
NEGATION_AGREEMENT_NONINFERIORITY = -0.01
SPEAKER_CHRF_MAX_LOSS = -1.00

# Preserve the exact identity of every pre-existing input.
FILES = {
    "protocol": V3_M9_ROOT / "RNMT_V3_M9_ADAPTED_ASR_CAUSAL_PROPAGATION_PROTOCOL_FROZEN_2026-08-07.md",
    "precommit": V3_M9_ROOT / "V3_M9_EXECUTION_PRECOMMIT_2026-08-07.json",
    "m1_predictions": M1_RUN / "outputs" / "V3_M0_M1_ALL_PREDICTIONS.csv",
    "m1_adapter": M1_RUN / "adapters" / "seed_17" / "adapter_model.safetensors",
    "development_source": M1_INPUTS / "dev_pairs_gold_and_mms_v1.csv",
    "clinical_lexicon": M1_INPUTS / "NLLB_V3_FROZEN_CLINICAL_LEXICON_v1.json",
    "adapted_asr_predictions": MMS_RUN / "predictions" / "mms_adapter_confirm_best_epoch_full_dev_paired.csv",
    "adapted_asr_adapter": MMS_RUN / "checkpoints" / "adapter_epoch_04.safetensors",
}
EXPECTED_HASHES = {
    "m1_predictions": "39DC9919C283FD59C1D4CDB3D878AA6D987C26D1AD993443FE246830F9C0E1C4",
    "m1_adapter": "209B17B08168DB35E02BD9CF2A5BE321A0175069DE51C0D8050AA565353C88E1",
    "development_source": "CB202D42D8A0D079F68515A4EFFD536BE2EE91CEA5E4689E2F55251A5C67626A",
    "clinical_lexicon": "A0532F1A5124DD48E90F9F4697CC8A9DDB7AC99048244C2C70DCB6A7727B23AA",
    "adapted_asr_predictions": "0D0120327BB58CE505C81C0F4563D929A8204E717E89C16F67AA4D61A0A71BD2",
    "adapted_asr_adapter": "F9B87F0ACD73BB8703ED936EB79117699FA9988B05B13ADB9D5288E0994B496B",
}

EXPECTED_PACKAGES = {
    "transformers": "4.57.1",
    "peft": "0.17.1",
    "accelerate": "1.11.0",
    "sacrebleu": "2.5.1",
    "sentencepiece": "0.2.1",
    "pandas": "2.2.3",
    "numpy": "1.26.4",
    "scipy": "1.15.2",
    "matplotlib": "3.10.0",
}


def sha256_file(path: Path) -> str:
    """Return an uppercase SHA-256 digest without loading a large file at once."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: object) -> None:
    """Write stable, human-readable UTF-8 JSON with a final newline."""
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def normalize_whitespace(value: object) -> str:
    """Apply only Unicode NFC and whitespace normalization."""
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def token_f1(reference: object, hypothesis: object) -> float:
    """Calculate multiset token F1 after the frozen minimal normalization."""
    from collections import Counter

    ref = Counter(normalize_whitespace(reference).casefold().split())
    hyp = Counter(normalize_whitespace(hypothesis).casefold().split())
    if not ref and not hyp:
        return 1.0
    if not ref or not hyp:
        return 0.0
    overlap = sum((ref & hyp).values())
    precision = overlap / sum(hyp.values())
    recall = overlap / sum(ref.values())
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def contains_term(text: object, term: object) -> bool:
    """Use transparent boundary-padded matching for the frozen lexicon."""
    padded_text = f" {normalize_whitespace(text).casefold()} "
    padded_term = f" {normalize_whitespace(term).casefold()} "
    return padded_term in padded_text


def matched_categories(text: object, categories: dict[str, list[str]]) -> set[str]:
    """Return every frozen English clinical category represented in text."""
    return {
        category
        for category, terms in categories.items()
        if any(contains_term(text, term) for term in terms)
    }


def concept_scores(reference: object, hypothesis: object, categories: dict[str, list[str]]) -> tuple[float, float]:
    """Return high-recall protected-category recall and precision."""
    ref = matched_categories(reference, categories)
    hyp = matched_categories(hypothesis, categories)
    recall = len(ref & hyp) / len(ref) if ref else np.nan
    precision = len(ref & hyp) / len(hyp) if hyp else (1.0 if not ref else 0.0)
    return recall, precision


def marker_set(text: object, pattern: re.Pattern[str]) -> tuple[str, ...]:
    """Extract a deterministic, case-folded set of number/timing markers."""
    return tuple(sorted({match.casefold() for match in pattern.findall(normalize_whitespace(text))}))


NEGATION_PATTERN = re.compile(
    r"\b(?:no|not|never|none|without|cannot|can't|do not|don't|does not|doesn't|should not|shouldn't|must not|mustn't)\b",
    flags=re.IGNORECASE,
)


def has_negation(text: object) -> bool:
    """Report whether a fixed English negation marker is present."""
    return bool(NEGATION_PATTERN.search(normalize_whitespace(text)))


# Abort before outcome calculation if an immutable file or runtime binding changed.
installed = {name: importlib.metadata.version(name) for name in EXPECTED_PACKAGES}
assert installed == EXPECTED_PACKAGES, {"expected": EXPECTED_PACKAGES, "installed": installed}
assert torch.cuda.is_available(), "A CUDA GPU is required."
gpu_name = torch.cuda.get_device_name(0)
assert "A100" in gpu_name.upper(), f"The frozen execution requires an A100; found {gpu_name}."
observed_hashes = {}
for name, path in FILES.items():
    assert path.is_file(), f"Missing immutable input: {path}"
    observed_hashes[name] = sha256_file(path)
    if name in EXPECTED_HASHES:
        assert observed_hashes[name] == EXPECTED_HASHES[name], {
            "name": name,
            "expected": EXPECTED_HASHES[name],
            "observed": observed_hashes[name],
        }

# The precommit binds this script and protocol before any outcome is calculated.
precommit = json.loads(FILES["precommit"].read_text(encoding="utf-8"))
assert precommit["protocol_id"] == PROTOCOL_ID
assert precommit["sha256"]["protocol"] == observed_hashes["protocol"]
assert precommit["sha256"]["execution_script"] == sha256_file(Path(__file__))
assert precommit["stop_boundaries"] == {
    "sealed_test_opened": False,
    "test_rows_read": 0,
    "human_outcomes_read": False,
    "sbllm_run": False,
    "production_changed": False,
}

# Record the environment before loading model outputs.
environment = {
    "protocol_id": PROTOCOL_ID,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "python": sys.version,
    "platform": platform.platform(),
    "torch": torch.__version__,
    "cuda_runtime": torch.version.cuda,
    "gpu": gpu_name,
    "packages": installed,
    "input_sha256": observed_hashes,
    "nllb_model_id": NLLB_MODEL_ID,
    "nllb_revision": NLLB_REVISION,
}
write_json(ENV_DIR / "V3_M9_ENVIRONMENT.json", environment)

# Load and validate the paired development identities without opening any test file.
m1 = pd.read_csv(FILES["m1_predictions"])
adapted = pd.read_csv(FILES["adapted_asr_predictions"])
dev_source = pd.read_csv(FILES["development_source"])
lexicon = json.loads(FILES["clinical_lexicon"].read_text(encoding="utf-8"))
assert len(m1) == 3116 and set(m1["input_condition"].astype(str)) == {"gold", "mms"}
assert len(adapted) == 1558 and adapted["record_uid"].astype(str).is_unique
assert len(dev_source) == 1558 and dev_source["record_uid"].astype(str).is_unique
assert adapted["content_group_id"].astype(str).nunique() == 458

gold = m1.loc[m1["input_condition"].astype(str).eq("gold")].copy()
d0 = m1.loc[m1["input_condition"].astype(str).eq("mms")].copy()
assert len(gold) == len(d0) == 1558
assert gold["record_uid"].astype(str).is_unique and d0["record_uid"].astype(str).is_unique

# Join by record ID and assert every shared identity and reference field agrees.
gold = gold.set_index(gold["record_uid"].astype(str), drop=False).sort_index()
d0 = d0.set_index(d0["record_uid"].astype(str), drop=False).sort_index()
adapted = adapted.set_index(adapted["record_uid"].astype(str), drop=False).sort_index()
assert list(gold.index) == list(d0.index) == list(adapted.index)
for column in ("content_group_id", "speaker_code"):
    assert gold[column].astype(str).equals(d0[column].astype(str))
    assert gold[column].astype(str).equals(adapted[column].astype(str))
assert gold["reference_english"].map(normalize_whitespace).equals(
    d0["reference_english"].map(normalize_whitespace)
)
assert gold["source_twi"].map(normalize_whitespace).equals(
    adapted["reference_raw"].map(normalize_whitespace)
)
assert d0["source_twi"].map(normalize_whitespace).equals(
    adapted["baseline_prediction_raw"].map(normalize_whitespace)
)

# Load the unchanged V3-M1 seed-17 translator and reproduce its decoder settings.
os.environ["HF_HOME"] = "/content/hf_cache"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.backends.cuda.matmul.allow_tf32 = True
torch.set_float32_matmul_precision("high")
transformers.set_seed(17)
tokenizer = AutoTokenizer.from_pretrained(
    NLLB_MODEL_ID,
    revision=NLLB_REVISION,
    src_lang=SOURCE_LANG,
    tgt_lang=TARGET_LANG,
    cache_dir=os.environ["HF_HOME"],
)
base_model = AutoModelForSeq2SeqLM.from_pretrained(
    NLLB_MODEL_ID,
    revision=NLLB_REVISION,
    torch_dtype=torch.bfloat16,
    cache_dir=os.environ["HF_HOME"],
)
model = PeftModel.from_pretrained(base_model, str(M1_RUN / "adapters" / "seed_17"), is_trainable=False)
model = model.to("cuda")
model.eval()


def translate_with_frozen_m1(sources: list[str], batch_size: int = 32) -> list[str]:
    """Translate adapted Twi with the exact V3-M1 decoding configuration."""
    translations: list[str] = []
    forced_bos = tokenizer.convert_tokens_to_ids(TARGET_LANG)
    for start in range(0, len(sources), batch_size):
        batch = [normalize_whitespace(value) for value in sources[start : start + batch_size]]
        encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=False).to("cuda")
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                forced_bos_token_id=forced_bos,
                num_beams=6,
                early_stopping=True,
                length_penalty=1.0,
                max_new_tokens=MAX_NEW_TOKENS,
            )
        translations.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
    return [normalize_whitespace(value) for value in translations]


# Generate D1 exactly once and preserve it before any metric is calculated.
generation_started = time.time()
d1_english = translate_with_frozen_m1(adapted["adapted_prediction_raw"].astype(str).tolist())
generation_seconds = time.time() - generation_started
assert len(d1_english) == 1558 and all(value.strip() for value in d1_english)

paired = pd.DataFrame(
    {
        "record_uid": gold["record_uid"].astype(str).to_numpy(),
        "content_group_id": gold["content_group_id"].astype(str).to_numpy(),
        "speaker_code": gold["speaker_code"].astype(str).to_numpy(),
        "theme_key": gold["theme_key"].astype(str).to_numpy(),
        "reference_english": gold["reference_english"].map(normalize_whitespace).to_numpy(),
        "gold_twi": gold["source_twi"].map(normalize_whitespace).to_numpy(),
        "d0_public_mms_twi": d0["source_twi"].map(normalize_whitespace).to_numpy(),
        "d1_adapted_mms_twi": adapted["adapted_prediction_raw"].map(normalize_whitespace).to_numpy(),
        "g_english": gold["hypothesis_s17"].map(normalize_whitespace).to_numpy(),
        "d0_english": d0["hypothesis_s17"].map(normalize_whitespace).to_numpy(),
        "d1_english": d1_english,
    }
)
prediction_path = OUTPUT_DIR / "V3_M9_G_D0_D1_ALL_DEVELOPMENT_PREDICTIONS.csv"
paired.to_csv(prediction_path, index=False, lineterminator="\n")
prediction_sha256 = sha256_file(prediction_path)

# Release model memory before statistical analysis.
del model, base_model
gc.collect()
torch.cuda.empty_cache()

# Calculate frozen corpus and row-level measures.
chrf = CHRF(word_order=2)
bleu = BLEU(tokenize="13a", effective_order=True)
english_categories = lexicon["english_categories"]
number_pattern = re.compile(lexicon["number_pattern"], flags=re.IGNORECASE)


def metric_bundle(frame: pd.DataFrame, column: str) -> dict[str, float]:
    """Return the frozen corpus and macro automatic metrics for one system."""
    references = frame["reference_english"].astype(str).tolist()
    hypotheses = frame[column].astype(str).tolist()
    return {
        "rows": int(len(frame)),
        "groups": int(frame["content_group_id"].astype(str).nunique()),
        "chrf_pp": float(chrf.corpus_score(hypotheses, [references]).score),
        "sacrebleu": float(bleu.corpus_score(hypotheses, [references]).score),
        "macro_token_f1": float(np.mean([token_f1(r, h) for r, h in zip(references, hypotheses)])),
        "empty_outputs": int(sum(not normalize_whitespace(h) for h in hypotheses)),
    }


for label, column in (("g", "g_english"), ("d0", "d0_english"), ("d1", "d1_english")):
    paired[f"{label}_sentence_chrf_pp"] = [
        float(chrf.sentence_score(hyp, [ref]).score)
        for ref, hyp in zip(paired["reference_english"], paired[column])
    ]
    paired[f"{label}_token_f1"] = [
        token_f1(ref, hyp) for ref, hyp in zip(paired["reference_english"], paired[column])
    ]
    concept = [
        concept_scores(ref, hyp, english_categories)
        for ref, hyp in zip(paired["reference_english"], paired[column])
    ]
    paired[f"{label}_protected_recall"] = [value[0] for value in concept]
    paired[f"{label}_protected_precision"] = [value[1] for value in concept]
    paired[f"{label}_number_agreement"] = [
        marker_set(ref, number_pattern) == marker_set(hyp, number_pattern)
        for ref, hyp in zip(paired["reference_english"], paired[column])
    ]
    paired[f"{label}_negation_agreement"] = [
        has_negation(ref) == has_negation(hyp)
        for ref, hyp in zip(paired["reference_english"], paired[column])
    ]

paired["d1_minus_d0_sentence_chrf_pp"] = paired["d1_sentence_chrf_pp"] - paired["d0_sentence_chrf_pp"]
paired.to_csv(prediction_path, index=False, lineterminator="\n")
prediction_sha256 = sha256_file(prediction_path)

overall = {label: metric_bundle(paired, column) for label, column in (
    ("G", "g_english"),
    ("D0", "d0_english"),
    ("D1", "d1_english"),
)}
for label, prefix in (("G", "g"), ("D0", "d0"), ("D1", "d1")):
    overall[label].update(
        {
            "protected_recall": float(paired[f"{prefix}_protected_recall"].mean(skipna=True)),
            "protected_precision": float(paired[f"{prefix}_protected_precision"].mean(skipna=True)),
            "number_agreement": float(paired[f"{prefix}_number_agreement"].mean()),
            "negation_agreement": float(paired[f"{prefix}_negation_agreement"].mean()),
        }
    )

# Estimate paired uncertainty at the semantic-content-group level.
group_deltas = paired.groupby("content_group_id", sort=True)["d1_minus_d0_sentence_chrf_pp"].mean()
rng = np.random.default_rng(BOOTSTRAP_SEED)
draws = group_deltas.to_numpy()[
    rng.integers(0, len(group_deltas), size=(BOOTSTRAP_REPLICATES, len(group_deltas)))
].mean(axis=1)
clustered_ci = [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]
wins = int((paired["d1_minus_d0_sentence_chrf_pp"] > 1e-12).sum())
losses = int((paired["d1_minus_d0_sentence_chrf_pp"] < -1e-12).sum())
ties = int(len(paired) - wins - losses)
sign_p = float(binomtest(wins, wins + losses, p=0.5, alternative="two-sided").pvalue) if wins + losses else 1.0

# Report every speaker code separately to prevent an overall gain hiding a subgroup loss.
speaker_rows = []
for speaker, frame in paired.groupby("speaker_code", sort=True):
    row = {"speaker_code": speaker, "rows": int(len(frame)), "groups": int(frame["content_group_id"].nunique())}
    for label, column in (("G", "g_english"), ("D0", "d0_english"), ("D1", "d1_english")):
        metrics = metric_bundle(frame, column)
        for metric in ("chrf_pp", "sacrebleu", "macro_token_f1"):
            row[f"{label.lower()}_{metric}"] = metrics[metric]
    row["d1_minus_d0_chrf_pp"] = row["d1_chrf_pp"] - row["d0_chrf_pp"]
    speaker_rows.append(row)
speaker_df = pd.DataFrame(speaker_rows)
speaker_df.to_csv(OUTPUT_DIR / "V3_M9_SPEAKER_METRICS.csv", index=False, lineterminator="\n")

# Calculate the descriptive fraction of the positive gold-input gap recovered.
gold_gap = overall["G"]["chrf_pp"] - overall["D0"]["chrf_pp"]
adapted_gain = overall["D1"]["chrf_pp"] - overall["D0"]["chrf_pp"]
recovery_fraction = adapted_gain / gold_gap if gold_gap > 0 else None

# Evaluate every precommitted gate without changing any threshold post hoc.
gate_checks = {
    "integrity_1558_rows_458_groups": len(paired) == 1558 and paired["content_group_id"].nunique() == 458,
    "d1_zero_empty_outputs": overall["D1"]["empty_outputs"] == 0,
    "d1_chrf_gain_at_least_1_point": adapted_gain >= CHRF_MIN_GAIN,
    "clustered_chrf_lower_ci_above_zero": clustered_ci[0] > 0.0,
    "paired_exact_sign_test_below_0_05_and_wins_exceed_losses": sign_p < 0.05 and wins > losses,
    "sacrebleu_noninferior_within_0_5": overall["D1"]["sacrebleu"] - overall["D0"]["sacrebleu"] >= BLEU_NONINFERIORITY,
    "macro_token_f1_noninferior_within_0_005": overall["D1"]["macro_token_f1"] - overall["D0"]["macro_token_f1"] >= TOKEN_F1_NONINFERIORITY,
    "protected_recall_noninferior_within_0_005": overall["D1"]["protected_recall"] - overall["D0"]["protected_recall"] >= PROTECTED_RECALL_NONINFERIORITY,
    "number_agreement_noninferior_within_0_01": overall["D1"]["number_agreement"] - overall["D0"]["number_agreement"] >= NUMBER_AGREEMENT_NONINFERIORITY,
    "negation_agreement_noninferior_within_0_01": overall["D1"]["negation_agreement"] - overall["D0"]["negation_agreement"] >= NEGATION_AGREEMENT_NONINFERIORITY,
    "no_speaker_chrf_loss_gt_1_point": float(speaker_df["d1_minus_d0_chrf_pp"].min()) >= SPEAKER_CHRF_MAX_LOSS,
    "strict_stop_boundaries_preserved": True,
}
automatic_pass = bool(all(gate_checks.values()))

# Save a compact table that can be used directly for dissertation figures/tables.
metric_rows = []
for condition, values in overall.items():
    metric_rows.append({"condition": condition, **values})
metric_df = pd.DataFrame(metric_rows)
metric_df.to_csv(OUTPUT_DIR / "V3_M9_OVERALL_METRICS.csv", index=False, lineterminator="\n")

# Produce fixed, publication-ready descriptive figures without test data.
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for axis, metric, title in zip(
    axes,
    ("chrf_pp", "sacrebleu", "macro_token_f1"),
    ("chrF++", "SacreBLEU", "Macro token F1"),
):
    values = metric_df.set_index("condition").loc[["G", "D0", "D1"], metric]
    axis.bar(values.index, values.values, color=["#6B7280", "#C2410C", "#0F766E"])
    axis.set_title(title)
    axis.set_ylabel("score")
    axis.grid(axis="y", alpha=0.25)
fig.suptitle("V3-M9 RNMT development metrics by ASR source condition")
fig.tight_layout()
fig.savefig(FIGURE_DIR / "V3_M9_FIGURE_1_OVERALL_METRICS.png", dpi=220, bbox_inches="tight")
plt.close(fig)

fig, axis = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(speaker_df))
axis.bar(x - 0.18, speaker_df["d0_chrf_pp"], width=0.36, label="D0 public MMS", color="#C2410C")
axis.bar(x + 0.18, speaker_df["d1_chrf_pp"], width=0.36, label="D1 adapted MMS", color="#0F766E")
axis.set_xticks(x, speaker_df["speaker_code"])
axis.set_ylabel("chrF++")
axis.set_title("V3-M9 paired development chrF++ by speaker code")
axis.legend()
axis.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "V3_M9_FIGURE_2_SPEAKER_CHRF.png", dpi=220, bbox_inches="tight")
plt.close(fig)

fig, axis = plt.subplots(figsize=(8, 4.5))
axis.hist(paired["d1_minus_d0_sentence_chrf_pp"], bins=40, color="#1D4ED8", alpha=0.85)
axis.axvline(0, color="black", linewidth=1)
axis.axvline(float(paired["d1_minus_d0_sentence_chrf_pp"].mean()), color="#B91C1C", linestyle="--", linewidth=1.5)
axis.set_xlabel("D1 - D0 sentence chrF++")
axis.set_ylabel("records")
axis.set_title("Distribution of paired RNMT changes")
axis.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(FIGURE_DIR / "V3_M9_FIGURE_3_PAIRED_CHRF_DELTAS.png", dpi=220, bbox_inches="tight")
plt.close(fig)

# Write the signed automatic-gate decision with strict downstream boundaries.
decision = {
    "artifact": "v3_m9_automatic_gate_decision_v1",
    "protocol_id": PROTOCOL_ID,
    "completed_utc": datetime.now(timezone.utc).isoformat(),
    "automatic_pass": automatic_pass,
    "decision": (
        "PASS_TO_SEPARATELY_FROZEN_72_CASE_BLINDED_DEVELOPMENT_AUDIT"
        if automatic_pass
        else "STOP_AND_PRESERVE_NEGATIVE_CAUSAL_RESULT"
    ),
    "input_sha256": observed_hashes,
    "output_sha256": {"paired_predictions": prediction_sha256},
    "generation_seconds": generation_seconds,
    "overall": overall,
    "paired_d1_minus_d0": {
        "corpus_chrf_pp_delta": adapted_gain,
        "mean_sentence_chrf_pp_delta": float(paired["d1_minus_d0_sentence_chrf_pp"].mean()),
        "semantic_group_clustered_ci95": clustered_ci,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "two_sided_exact_sign_p": sign_p,
        "sacrebleu_delta": overall["D1"]["sacrebleu"] - overall["D0"]["sacrebleu"],
        "macro_token_f1_delta": overall["D1"]["macro_token_f1"] - overall["D0"]["macro_token_f1"],
        "protected_recall_delta": overall["D1"]["protected_recall"] - overall["D0"]["protected_recall"],
        "number_agreement_delta": overall["D1"]["number_agreement"] - overall["D0"]["number_agreement"],
        "negation_agreement_delta": overall["D1"]["negation_agreement"] - overall["D0"]["negation_agreement"],
    },
    "diagnostic_gold_gap": {
        "g_minus_d0_corpus_chrf_pp": gold_gap,
        "d1_recovery_fraction_of_positive_gold_gap": recovery_fraction,
    },
    "speaker_metrics": speaker_rows,
    "gate_thresholds": {
        "chrf_min_gain": CHRF_MIN_GAIN,
        "bleu_noninferiority": BLEU_NONINFERIORITY,
        "token_f1_noninferiority": TOKEN_F1_NONINFERIORITY,
        "protected_recall_noninferiority": PROTECTED_RECALL_NONINFERIORITY,
        "number_agreement_noninferiority": NUMBER_AGREEMENT_NONINFERIORITY,
        "negation_agreement_noninferiority": NEGATION_AGREEMENT_NONINFERIORITY,
        "speaker_chrf_max_loss": SPEAKER_CHRF_MAX_LOSS,
    },
    "gate_checks": gate_checks,
    "automatic_proxy_warning": "Lexicon, number and negation checks are screening proxies, not clinical-safety judgments.",
    "sealed_test_opened": False,
    "test_rows_read": 0,
    "human_outcomes_read": False,
    "sbllm_run": False,
    "production_changed": False,
}
decision_path = OUTPUT_DIR / "V3_M9_AUTOMATIC_GATE_DECISION.json"
write_json(decision_path, decision)

# Hash every generated artifact last so the archive is independently verifiable.
manifest = []
for path in sorted(RUN_DIR.rglob("*")):
    if path.is_file() and path.name != "V3_M9_SHA256_MANIFEST.json":
        manifest.append(
            {
                "path": path.relative_to(RUN_DIR).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
write_json(RUN_DIR / "V3_M9_SHA256_MANIFEST.json", manifest)
print(json.dumps(decision, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
