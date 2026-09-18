"""
GeoCoral — model training entry point.

Runs the two-phase transfer learning strategy described in the
Methodology chapter:
  Phase 1: train the classification head only (ResNet50 base frozen),
           LR = 1e-4
  Phase 2: unfreeze the final residual blocks (conv5_block*) and
           fine-tune jointly with the head, LR = 1e-5

Adam optimizer, binary cross-entropy loss, batch size 32. Early stopping
and model checkpointing on validation loss are applied in both phases.

Run:
    python -m training.train
"""

import json
import os
import sys

import tensorflow as tf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from training.dataset import get_train_dataset, get_val_dataset
from training.model import build_model, compile_model, unfreeze_for_fine_tuning, count_trainable_params


def make_callbacks(checkpoint_path, log_subdir):
    os.makedirs(config.MODEL_DIR, exist_ok=True)
    os.makedirs(os.path.join(config.LOG_DIR, log_subdir), exist_ok=True)

    return [
        tf.keras.callbacks.EarlyStopping(
            monitor=config.EARLY_STOPPING_MONITOR,
            patience=config.EARLY_STOPPING_PATIENCE,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=checkpoint_path,
            monitor=config.EARLY_STOPPING_MONITOR,
            save_best_only=True,
        ),
        tf.keras.callbacks.CSVLogger(
            os.path.join(config.LOG_DIR, log_subdir, "history.csv")
        ),
        tf.keras.callbacks.TensorBoard(
            log_dir=os.path.join(config.LOG_DIR, log_subdir)
        ),
    ]


def main():
    print("Loading datasets...")
    train_ds, n_train = get_train_dataset()
    val_ds, n_val = get_val_dataset()
    print(f"Train images: {n_train} | Val images: {n_val}")

    print("\nBuilding ResNet50 transfer-learning model...")
    model, base_model = build_model()

    # ------------------------------------------------------------------
    # Phase 1 — head training (base frozen)
    # ------------------------------------------------------------------
    print("\n=== Phase 1: head training (base frozen) ===")
    compile_model(model, learning_rate=config.HEAD_LEARNING_RATE)
    trainable, non_trainable = count_trainable_params(model)
    print(f"Trainable params: {trainable:,} | Frozen params: {non_trainable:,}")

    history_phase1 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=config.HEAD_EPOCHS,
        callbacks=make_callbacks(config.BEST_MODEL_PATH, "phase1_head_training"),
    )

    # ------------------------------------------------------------------
    # Phase 2 — fine-tuning (unfreeze conv5_block*)
    # ------------------------------------------------------------------
    print("\n=== Phase 2: fine-tuning (unfreezing final residual blocks) ===")
    unfreeze_for_fine_tuning(base_model)
    compile_model(model, learning_rate=config.FINE_TUNE_LEARNING_RATE)
    trainable, non_trainable = count_trainable_params(model)
    print(f"Trainable params: {trainable:,} | Frozen params: {non_trainable:,}")

    history_phase2 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=config.FINE_TUNE_EPOCHS,
        callbacks=make_callbacks(config.BEST_MODEL_PATH, "phase2_fine_tuning"),
    )

    os.makedirs(config.MODEL_DIR, exist_ok=True)
    model.save(config.FINAL_MODEL_PATH)
    print(f"\nFinal model saved to {config.FINAL_MODEL_PATH}")
    print(f"Best checkpoint (lowest val_loss) saved to {config.BEST_MODEL_PATH}")

    combined_history = {
        "phase1_head_training": history_phase1.history,
        "phase2_fine_tuning": history_phase2.history,
    }
    history_path = os.path.join(config.LOG_DIR, "combined_history.json")
    with open(history_path, "w") as f:
        json.dump(combined_history, f, indent=2)
    print(f"Training history saved to {history_path}")


if __name__ == "__main__":
    main()
