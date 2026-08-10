"""Run one seed of the frozen three-seed MMS maternal-health confirmation."""

# Use only standard-library modules until the pinned execution environment is verified.
import csv
import hashlib
import json
import math
import os
import random
import shutil
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from math import gcd
from pathlib import Path

# Import the pinned scientific stack from the isolated Colab environment.
import numpy as np
import soundfile as sf
import torch
from safetensors.torch import save_file as safe_save_file
from scipy.signal import resample_poly
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset, Sampler
from transformers import (
    Wav2Vec2CTCTokenizer,
    Wav2Vec2FeatureExtractor,
    Wav2Vec2ForCTC,
    Wav2Vec2Processor,
    get_linear_schedule_with_warmup,
)


# Freeze identifiers, paths and hashes before touching the data.
PROTOCOL_ID = "mms-maternal-adapter-confirm-dev-v1"
SEED = int(os.environ["MMS_CONFIRM_SEED"])
BASE_REPO = "facebook/mms-1b-all"
BASE_REVISION = "3d33597edbdaaba14a8e858e2c8caa76e3cec0cd"
DRIVE_ROOT = Path("/content/drive/MyDrive/Akan_ASR_PhD_Experiments")
EXP_ROOT = DRIVE_ROOT / "03_Adaptation/mms_maternal_adaptation_2026-08-06"
TRAIN_MANIFEST = EXP_ROOT / "V3_M5_TRAIN_AUDIO_MANIFEST_v1.csv"
EXPECTED_TRAIN_SHA = "1EBC4FF1D7F668AD28BA7262DD4CB143264F39906CF98B3B11806A9BCCDB5633"
EXPECTED_DEV_SHA = "30C202E8490BE242A411B1547712527546D3355237072CB29C09CB301FACFA4F"
DEV_FILENAME = "evaluated_records_full_dev.csv"
BASELINE_PRED_FILENAME = "mms_1b_akan_base__3d33597edbda__full_dev.csv"
RUN_ID = f"20260807_mms_maternal_adapter_confirm_seed{SEED}"
RUN_DIR = EXP_ROOT / "runs" / RUN_ID
LOCAL_CACHE = Path("/content/mms_maternal_adapter_audio16k")
TARGET_SR = 16000
EPOCHS = 4
BATCH_SIZE = 8
GRAD_ACCUM = 4
LEARNING_RATE = 1e-3
WARMUP_RATIO = 0.10
BOOTSTRAP_DRAWS = 5000


# Hash files in streaming chunks for immutable provenance.
def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


# Read a CSV without importing pandas or changing Unicode strings.
def read_csv_rows(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = list(reader.fieldnames or [])
    return rows, columns


# Write a CSV with stable header order and UTF-8 text.
def write_csv_rows(path, rows, columns):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# Apply the already frozen primary ASR scoring normalization.
def normalize_primary(text):
    text = unicodedata.normalize("NFC", str(text or "")).casefold()
    text = "".join(" " if unicodedata.category(char)[0] in {"P", "S"} else char for char in text)
    return " ".join(text.split())


# Compute exact Levenshtein distance for words or characters.
def edit_distance(reference, hypothesis):
    previous = list(range(len(hypothesis) + 1))
    for index, ref_item in enumerate(reference, start=1):
        current = [index]
        for position, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[position] + 1,
                    previous[position - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


# Compute row-level word and character error numerators and denominators.
def row_error_counts(reference, hypothesis):
    ref_norm = normalize_primary(reference)
    hyp_norm = normalize_primary(hypothesis)
    ref_words = ref_norm.split()
    hyp_words = hyp_norm.split()
    ref_chars = list(ref_norm.replace(" ", ""))
    hyp_chars = list(hyp_norm.replace(" ", ""))
    return {
        "reference_normalized": ref_norm,
        "prediction_normalized": hyp_norm,
        "word_errors": edit_distance(ref_words, hyp_words),
        "reference_words": len(ref_words),
        "char_errors": edit_distance(ref_chars, hyp_chars),
        "reference_chars": len(ref_chars),
    }


# Aggregate row-level counts into corpus WER and space-excluded CER.
def aggregate_rates(rows, prefix):
    word_errors = sum(int(row[f"{prefix}_word_errors"]) for row in rows)
    ref_words = sum(int(row["reference_words"]) for row in rows)
    char_errors = sum(int(row[f"{prefix}_char_errors"]) for row in rows)
    ref_chars = sum(int(row["reference_chars"]) for row in rows)
    return {
        "wer": word_errors / ref_words,
        "cer": char_errors / ref_chars,
        "word_errors": word_errors,
        "reference_words": ref_words,
        "char_errors": char_errors,
        "reference_chars": ref_chars,
    }


# Resample and cache one verified audio file at 16 kHz mono on local SSD.
def materialize_audio(source, destination, expected_sha):
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 44:
        return
    assert source.exists(), source
    assert sha256_file(source) == expected_sha.upper(), f"Audio hash mismatch: {source}"
    waveform, sampling_rate = sf.read(source, dtype="float32", always_2d=False)
    if waveform.ndim == 2:
        waveform = waveform.mean(axis=1)
    if int(sampling_rate) != TARGET_SR:
        divisor = gcd(int(sampling_rate), TARGET_SR)
        waveform = resample_poly(waveform, TARGET_SR // divisor, int(sampling_rate) // divisor).astype(np.float32)
    sf.write(destination, waveform, TARGET_SR, subtype="PCM_16")


# Define the train/evaluation dataset over already cached 16 kHz audio.
class AudioTextDataset(Dataset):
    def __init__(self, rows, processor, cache_dir, target_field):
        self.rows = rows
        self.processor = processor
        self.cache_dir = Path(cache_dir)
        self.target_field = target_field

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        audio_path = self.cache_dir / f"{row['record_uid']}.wav"
        waveform, sampling_rate = sf.read(audio_path, dtype="float32", always_2d=False)
        assert int(sampling_rate) == TARGET_SR
        input_values = self.processor(waveform, sampling_rate=TARGET_SR).input_values[0]
        labels = self.processor(text=row[self.target_field]).input_ids
        return {
            "input_values": input_values,
            "labels": labels,
            "record_uid": row["record_uid"],
        }


# Pad audio and CTC labels independently at batch time.
class CTCDataCollator:
    def __init__(self, processor):
        self.processor = processor

    def __call__(self, features):
        inputs = [{"input_values": feature["input_values"]} for feature in features]
        labels = [{"input_ids": feature["labels"]} for feature in features]
        batch = self.processor.pad(inputs, padding=True, return_tensors="pt")
        label_batch = self.processor.pad(labels=labels, padding=True, return_tensors="pt")
        batch["labels"] = label_batch["input_ids"].masked_fill(label_batch.attention_mask.ne(1), -100)
        batch["record_uid"] = [feature["record_uid"] for feature in features]
        return batch


# Create deterministic length-bucketed batches to reduce padding.
class LengthBucketBatchSampler(Sampler):
    def __init__(self, rows, batch_size, seed):
        self.rows = rows
        self.batch_size = batch_size
        self.seed = seed
        self.epoch = 0
        self.batches = []

    def set_epoch(self, epoch):
        self.epoch = epoch

    def __iter__(self):
        ordered = sorted(range(len(self.rows)), key=lambda idx: (float(self.rows[idx]["duration_seconds"]), self.rows[idx]["record_uid"]))
        batches = [ordered[start : start + self.batch_size] for start in range(0, len(ordered), self.batch_size)]
        rng = random.Random(self.seed + self.epoch)
        rng.shuffle(batches)
        self.batches = batches
        return iter(batches)

    def __len__(self):
        return math.ceil(len(self.rows) / self.batch_size)


# Evaluate one model and return raw predictions in immutable development order.
@torch.inference_mode()
def predict_model(model, processor, loader, device):
    model.eval()
    predictions = {}
    failures = 0
    for batch in loader:
        record_uids = batch.pop("record_uid")
        labels = batch.pop("labels")
        inputs = {key: value.to(device, non_blocking=True) for key, value in batch.items()}
        try:
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=torch.cuda.is_bf16_supported()):
                logits = model(**inputs).logits
            decoded = processor.batch_decode(torch.argmax(logits, dim=-1))
        except Exception:
            decoded = [""] * len(record_uids)
            failures += len(record_uids)
        for record_uid, prediction in zip(record_uids, decoded):
            predictions[record_uid] = prediction
        del labels
    return predictions, failures


# Build paired evaluation rows against the immutable baseline predictions.
def build_paired_rows(dev_rows, adapted_predictions, baseline_predictions):
    paired = []
    for row in dev_rows:
        uid = row["record_uid"]
        reference = row["Transcription"]
        adapted = row_error_counts(reference, adapted_predictions.get(uid, ""))
        baseline = row_error_counts(reference, baseline_predictions.get(uid, ""))
        paired.append(
            {
                "record_uid": uid,
                "content_group_id": row["content_group_id"],
                "speaker_code": row["speaker_code"],
                "reference_raw": reference,
                "reference_normalized": adapted["reference_normalized"],
                "baseline_prediction_raw": baseline_predictions.get(uid, ""),
                "baseline_prediction_normalized": baseline["prediction_normalized"],
                "adapted_prediction_raw": adapted_predictions.get(uid, ""),
                "adapted_prediction_normalized": adapted["prediction_normalized"],
                "reference_words": adapted["reference_words"],
                "reference_chars": adapted["reference_chars"],
                "baseline_word_errors": baseline["word_errors"],
                "baseline_char_errors": baseline["char_errors"],
                "adapted_word_errors": adapted["word_errors"],
                "adapted_char_errors": adapted["char_errors"],
            }
        )
    return paired


# Compute a semantic-group-clustered paired bootstrap for WER and CER deltas.
def clustered_bootstrap(paired_rows, draws, seed):
    grouped = defaultdict(list)
    for row in paired_rows:
        grouped[row["content_group_id"]].append(row)
    group_ids = sorted(grouped)
    group_summaries = []
    for group_id in group_ids:
        block = grouped[group_id]
        group_summaries.append(
            [
                sum(row["adapted_word_errors"] for row in block),
                sum(row["baseline_word_errors"] for row in block),
                sum(row["reference_words"] for row in block),
                sum(row["adapted_char_errors"] for row in block),
                sum(row["baseline_char_errors"] for row in block),
                sum(row["reference_chars"] for row in block),
            ]
        )
    matrix = np.asarray(group_summaries, dtype=np.float64)
    rng = np.random.default_rng(seed)
    wer_deltas = np.empty(draws, dtype=np.float64)
    cer_deltas = np.empty(draws, dtype=np.float64)
    for draw in range(draws):
        sampled = matrix[rng.integers(0, len(matrix), size=len(matrix))].sum(axis=0)
        wer_deltas[draw] = sampled[0] / sampled[2] - sampled[1] / sampled[2]
        cer_deltas[draw] = sampled[3] / sampled[5] - sampled[4] / sampled[5]
    return {
        "draws": draws,
        "clusters": len(group_ids),
        "wer_delta_ci95": [float(np.quantile(wer_deltas, 0.025)), float(np.quantile(wer_deltas, 0.975))],
        "cer_delta_ci95": [float(np.quantile(cer_deltas, 0.025)), float(np.quantile(cer_deltas, 0.975))],
    }


# Make all random sources deterministic where the runtime permits it.
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
os.environ["PYTHONHASHSEED"] = str(SEED)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True

# Create output locations without touching any sealed-test directory.
RUN_DIR.mkdir(parents=True, exist_ok=True)
(RUN_DIR / "checkpoints").mkdir(exist_ok=True)
(RUN_DIR / "predictions").mkdir(exist_ok=True)
(RUN_DIR / "metrics").mkdir(exist_ok=True)
(RUN_DIR / "logs").mkdir(exist_ok=True)

# Verify the immutable train manifest before parsing it.
assert sha256_file(TRAIN_MANIFEST) == EXPECTED_TRAIN_SHA
train_rows, train_columns = read_csv_rows(TRAIN_MANIFEST)
assert len(train_rows) == 7240
assert {row["split"].lower() for row in train_rows} == {"train"}

# Locate and verify the sole immutable development source.
dev_candidates = [path for path in DRIVE_ROOT.rglob(DEV_FILENAME) if "test" not in str(path).lower()]
assert len(dev_candidates) == 1, [str(path) for path in dev_candidates]
dev_path = dev_candidates[0]
assert sha256_file(dev_path) == EXPECTED_DEV_SHA
dev_rows, dev_columns = read_csv_rows(dev_path)
assert len(dev_rows) == 1558
assert {row["split"].lower() for row in dev_rows} == {"dev"}
assert not ({row["content_group_id"] for row in train_rows} & {row["content_group_id"] for row in dev_rows})

# Locate the immutable MMS baseline development predictions.
baseline_candidates = [path for path in DRIVE_ROOT.rglob(BASELINE_PRED_FILENAME) if "test" not in str(path).lower()]
assert len(baseline_candidates) == 1, [str(path) for path in baseline_candidates]
baseline_path = baseline_candidates[0]
baseline_rows, baseline_columns = read_csv_rows(baseline_path)
baseline_predictions = {row["record_uid"]: row["prediction_raw"] for row in baseline_rows if row["status"] == "ok"}
assert len(baseline_predictions) == len(dev_rows)

# Build a train-only normalized character vocabulary.
train_targets = [normalize_primary(row["source_gold_normalized"]) for row in train_rows]
assert all(train_targets)
characters = sorted(set("".join(train_targets)) - {" "})
vocab = {"|": 0}
for character in characters:
    if character not in vocab:
        vocab[character] = len(vocab)
vocab["[UNK]"] = len(vocab)
vocab["[PAD]"] = len(vocab)
vocab_path = RUN_DIR / "vocab.json"
vocab_path.write_text(json.dumps(vocab, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

# Measure development characters absent from the train-only vocabulary.
dev_normalized = [normalize_primary(row["Transcription"]) for row in dev_rows]
dev_chars = [character for text in dev_normalized for character in text if character != " "]
oov_chars = sorted(set(dev_chars).difference(characters))
oov_occurrences = sum(character in oov_chars for character in dev_chars)
oov_rate = oov_occurrences / max(1, len(dev_chars))

# Materialize a fully local, verified, 16 kHz cache for deterministic throughput.
cache_started = time.time()
for split_name, rows in [("train", train_rows), ("dev", dev_rows)]:
    split_cache = LOCAL_CACHE / split_name
    split_cache.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(rows, start=1):
        materialize_audio(
            row["audio_path_frozen"],
            split_cache / f"{row['record_uid']}.wav",
            row["audio_sha256"],
        )
        if index % 500 == 0:
            print(f"cached {split_name}: {index}/{len(rows)}", flush=True)
cache_seconds = time.time() - cache_started

# Construct the train-only processor and preserve it with the run.
tokenizer = Wav2Vec2CTCTokenizer(
    str(vocab_path),
    unk_token="[UNK]",
    pad_token="[PAD]",
    word_delimiter_token="|",
    bos_token=None,
    eos_token=None,
)
feature_extractor = Wav2Vec2FeatureExtractor(
    feature_size=1,
    sampling_rate=TARGET_SR,
    padding_value=0.0,
    do_normalize=True,
    return_attention_mask=True,
)
processor = Wav2Vec2Processor(feature_extractor=feature_extractor, tokenizer=tokenizer)
processor.save_pretrained(RUN_DIR / "processor")

# Attach normalized train targets without changing the immutable source manifest.
for row, target in zip(train_rows, train_targets):
    row["training_target"] = target
for row, target in zip(dev_rows, dev_normalized):
    row["evaluation_target"] = target

# Build deterministic datasets and loaders.
train_dataset = AudioTextDataset(train_rows, processor, LOCAL_CACHE / "train", "training_target")
dev_dataset = AudioTextDataset(dev_rows, processor, LOCAL_CACHE / "dev", "evaluation_target")
collator = CTCDataCollator(processor)
batch_sampler = LengthBucketBatchSampler(train_rows, BATCH_SIZE, SEED)
train_loader = DataLoader(
    train_dataset,
    batch_sampler=batch_sampler,
    collate_fn=collator,
    num_workers=4,
    pin_memory=True,
    persistent_workers=True,
)
dev_loader = DataLoader(
    dev_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    collate_fn=collator,
    num_workers=4,
    pin_memory=True,
    persistent_workers=True,
)

# Require the intended A100-class CUDA execution surface.
assert torch.cuda.is_available(), "CUDA is required for the frozen screening run"
device = torch.device("cuda")
gpu_name = torch.cuda.get_device_name(0)
assert "A100" in gpu_name.upper(), f"Expected A100, observed {gpu_name}"

# Load the exact frozen MMS base and create a fresh train-only output vocabulary.
model = Wav2Vec2ForCTC.from_pretrained(
    BASE_REPO,
    revision=BASE_REVISION,
    attention_dropout=0.0,
    hidden_dropout=0.0,
    feat_proj_dropout=0.0,
    layerdrop=0.0,
    ctc_loss_reduction="mean",
    pad_token_id=processor.tokenizer.pad_token_id,
    vocab_size=len(processor.tokenizer),
    ignore_mismatched_sizes=True,
    # Load concrete CPU tensors before resizing the train-only CTC head.  The
    # low-memory meta-device path leaves resized parameters unmaterialized in
    # transformers 4.46.3 and fails before the first epoch when moved to CUDA.
    low_cpu_mem_usage=False,
)
model.init_adapter_layers()
model.freeze_base_model()
for parameter in model._get_adapters().values():
    parameter.requires_grad = True
model.gradient_checkpointing_enable()
model.config.ctc_zero_infinity = True
model.to(device)

# Verify that only a small adapter subset is trainable.
trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
total_parameters = sum(parameter.numel() for parameter in model.parameters())
assert 100_000 < trainable_parameters < 5_000_000, trainable_parameters

# Configure the frozen optimizer and linear warm-up schedule.
optimizer = AdamW(
    [parameter for parameter in model.parameters() if parameter.requires_grad],
    lr=LEARNING_RATE,
    betas=(0.9, 0.999),
    eps=1e-8,
    weight_decay=0.0,
)
optimizer_steps_per_epoch = math.ceil(len(batch_sampler) / GRAD_ACCUM)
total_optimizer_steps = optimizer_steps_per_epoch * EPOCHS
warmup_steps = math.ceil(total_optimizer_steps * WARMUP_RATIO)
scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_optimizer_steps)

# Record the complete execution environment before training begins.
environment = {
    "protocol": PROTOCOL_ID,
    "run_id": RUN_ID,
    "python": sys.version,
    "torch": torch.__version__,
    "transformers": __import__("transformers").__version__,
    "numpy": np.__version__,
    "scipy": __import__("scipy").__version__,
    "soundfile": sf.__version__,
    "gpu": gpu_name,
    "cuda": torch.version.cuda,
    "bf16_supported": torch.cuda.is_bf16_supported(),
    "trainable_parameters": trainable_parameters,
    "total_parameters": total_parameters,
    "cache_seconds": cache_seconds,
    "dev_oov_characters": oov_chars,
    "dev_oov_occurrences": oov_occurrences,
    "dev_oov_rate": oov_rate,
    "sealed_test_opened": False,
    "test_rows_read": 0,
}
(RUN_DIR / "environment.json").write_text(json.dumps(environment, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

# Train all four frozen epochs and retain every epoch result.
epoch_records = []
best_key = None
best_epoch = None
best_predictions = None
training_started = time.time()
torch.cuda.reset_peak_memory_stats()
for epoch in range(1, EPOCHS + 1):
    batch_sampler.set_epoch(epoch)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    running_loss = 0.0
    batches_seen = 0
    for batch_index, batch in enumerate(train_loader, start=1):
        batch.pop("record_uid")
        inputs = {key: value.to(device, non_blocking=True) for key, value in batch.items()}
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=torch.cuda.is_bf16_supported()):
            loss = model(**inputs).loss / GRAD_ACCUM
        loss.backward()
        running_loss += float(loss.detach().cpu()) * GRAD_ACCUM
        batches_seen += 1
        if batch_index % GRAD_ACCUM == 0 or batch_index == len(train_loader):
            torch.nn.utils.clip_grad_norm_([parameter for parameter in model.parameters() if parameter.requires_grad], 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
        if batch_index % 100 == 0:
            print(f"epoch {epoch} batch {batch_index}/{len(train_loader)} loss {running_loss / batches_seen:.5f}", flush=True)

    adapted_predictions, output_failures = predict_model(model, processor, dev_loader, device)
    paired_rows = build_paired_rows(dev_rows, adapted_predictions, baseline_predictions)
    adapted_rates = aggregate_rates(paired_rows, "adapted")
    baseline_rates = aggregate_rates(paired_rows, "baseline")
    epoch_record = {
        "epoch": epoch,
        "train_loss": running_loss / max(1, batches_seen),
        "adapted": adapted_rates,
        "baseline": baseline_rates,
        "output_failures": output_failures,
        "output_failure_rate": output_failures / len(dev_rows),
        "learning_rate_end": scheduler.get_last_lr()[0],
    }
    epoch_records.append(epoch_record)
    epoch_path = RUN_DIR / "metrics" / f"epoch_{epoch:02d}_metrics.json"
    epoch_path.write_text(json.dumps(epoch_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    adapter_path = RUN_DIR / "checkpoints" / f"adapter_epoch_{epoch:02d}.safetensors"
    safe_save_file(model._get_adapters(), str(adapter_path), metadata={"format": "pt", "protocol": PROTOCOL_ID})
    key = (adapted_rates["wer"], adapted_rates["cer"], epoch)
    if best_key is None or key < best_key:
        best_key = key
        best_epoch = epoch
        best_predictions = dict(adapted_predictions)
    print(json.dumps(epoch_record, indent=2), flush=True)

# Build the final paired table from the precommitted best-epoch rule.
assert best_predictions is not None
paired_rows = build_paired_rows(dev_rows, best_predictions, baseline_predictions)
adapted_overall = aggregate_rates(paired_rows, "adapted")
baseline_overall = aggregate_rates(paired_rows, "baseline")
bootstrap = clustered_bootstrap(paired_rows, BOOTSTRAP_DRAWS, SEED + 1000)

# Compute deterministic per-speaker paired results.
speaker_results = {}
for speaker in sorted({row["speaker_code"] for row in paired_rows}):
    block = [row for row in paired_rows if row["speaker_code"] == speaker]
    adapted_speaker = aggregate_rates(block, "adapted")
    baseline_speaker = aggregate_rates(block, "baseline")
    speaker_results[speaker] = {
        "rows": len(block),
        "adapted_wer": adapted_speaker["wer"],
        "baseline_wer": baseline_speaker["wer"],
        "wer_delta": adapted_speaker["wer"] - baseline_speaker["wer"],
        "adapted_cer": adapted_speaker["cer"],
        "baseline_cer": baseline_speaker["cer"],
        "cer_delta": adapted_speaker["cer"] - baseline_speaker["cer"],
    }

# Apply the frozen automatic advancement gate without human interpretation.
selected_epoch_record = next(record for record in epoch_records if record["epoch"] == best_epoch)
gate_checks = {
    "wer_relative_improvement_at_least_5pct": adapted_overall["wer"] <= 0.95 * baseline_overall["wer"],
    "cer_no_worse": adapted_overall["cer"] <= baseline_overall["cer"],
    "one_clustered_ci_upper_below_zero": bootstrap["wer_delta_ci95"][1] < 0 or bootstrap["cer_delta_ci95"][1] < 0,
    "no_speaker_wer_regression_gt_0_03": max(result["wer_delta"] for result in speaker_results.values()) <= 0.03,
    "no_speaker_cer_regression_gt_0_02": max(result["cer_delta"] for result in speaker_results.values()) <= 0.02,
    "output_failure_rate_at_most_1pct": selected_epoch_record["output_failure_rate"] <= 0.01,
    "integrity_pass": True,
}
automatic_pass = all(gate_checks.values())

# Preserve the final paired predictions and all metrics.
prediction_columns = [
    "record_uid",
    "content_group_id",
    "speaker_code",
    "reference_raw",
    "reference_normalized",
    "baseline_prediction_raw",
    "baseline_prediction_normalized",
    "adapted_prediction_raw",
    "adapted_prediction_normalized",
    "reference_words",
    "reference_chars",
    "baseline_word_errors",
    "baseline_char_errors",
    "adapted_word_errors",
    "adapted_char_errors",
]
predictions_path = RUN_DIR / "predictions" / "mms_adapter_confirm_best_epoch_full_dev_paired.csv"
write_csv_rows(predictions_path, paired_rows, prediction_columns)

# Record the screening decision and strict downstream stop-state.
decision = {
    "artifact": "mms_maternal_adapter_screen_decision_v1",
    "protocol": PROTOCOL_ID,
    "run_id": RUN_ID,
    "seed": SEED,
    "selected_epoch": best_epoch,
    "epoch_records": epoch_records,
    "overall": {
        "adapted": adapted_overall,
        "baseline": baseline_overall,
        "wer_delta": adapted_overall["wer"] - baseline_overall["wer"],
        "cer_delta": adapted_overall["cer"] - baseline_overall["cer"],
    },
    "clustered_bootstrap": bootstrap,
    "by_speaker": speaker_results,
    "gate_checks": gate_checks,
    "automatic_pass": automatic_pass,
    "training_seconds": time.time() - training_started,
    "peak_gpu_memory_bytes": torch.cuda.max_memory_allocated(),
    "trainable_parameters": trainable_parameters,
    "dev_oov_characters": oov_chars,
    "dev_oov_occurrences": oov_occurrences,
    "dev_oov_rate": oov_rate,
    "input_sha256": {
        "train_manifest": sha256_file(TRAIN_MANIFEST),
        "development_source": sha256_file(dev_path),
        "baseline_predictions": sha256_file(baseline_path),
        "vocab": sha256_file(vocab_path),
    },
    "output_sha256_before_decision": {
        "paired_predictions": sha256_file(predictions_path),
        "selected_adapter": sha256_file(RUN_DIR / "checkpoints" / f"adapter_epoch_{best_epoch:02d}.safetensors"),
    },
    "selected_adapter_path": str(RUN_DIR / "checkpoints" / f"adapter_epoch_{best_epoch:02d}.safetensors"),
    "sealed_test_opened": False,
    "test_rows_read": 0,
    "rnmt_human_outcomes_read": False,
    "sbllm_run": False,
    "production_changed": False,
    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
}
decision_path = RUN_DIR / "MMS_ADAPTER_CONFIRMATION_SEED_DECISION.json"
decision_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

# Hash every small result artifact while excluding ephemeral local audio.
result_manifest = []
for path in sorted(RUN_DIR.rglob("*")):
    if path.is_file():
        result_manifest.append({"path": str(path.relative_to(RUN_DIR)), "sha256": sha256_file(path), "bytes": path.stat().st_size})
manifest_path = RUN_DIR / "SHA256_MANIFEST.json"
manifest_path.write_text(json.dumps(result_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

# Print the complete automatic decision for visible Colab monitoring.
print(json.dumps(decision, indent=2, ensure_ascii=False), flush=True)
