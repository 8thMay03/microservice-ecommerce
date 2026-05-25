"""
CLI script to train the Neural CF behavior model.
Replaces the Django management command: python manage.py train_behavior_model

Usage:
  python train_model.py [--epochs N] [--output PATH] [--device DEVICE]
"""
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")

from app import config as settings
from app.engine import _fetch_all_orders
from app.model_behavior import clear_predictor_cache, train_and_save


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the deep learning behavior model (NCF) from order-service history."
    )
    parser.add_argument("--epochs", type=int, default=25, help="Training epochs (default 25).")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Override output path (default: BEHAVIOR_MODEL_PATH from config).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Torch device override: cpu, cuda, cuda:0, mps, auto.",
    )
    args = parser.parse_args()

    path = args.output or settings.BEHAVIOR_MODEL_PATH
    if not path:
        print("ERROR: BEHAVIOR_MODEL_PATH is not set.", file=sys.stderr)
        sys.exit(1)

    orders = _fetch_all_orders()
    if not orders:
        print("ERROR: No completed orders returned from order-service.", file=sys.stderr)
        sys.exit(1)

    ok = train_and_save(orders, save_path=path, epochs=args.epochs, device=args.device)
    if ok:
        clear_predictor_cache()
        print(f"Training finished. Checkpoint saved to: {path}")
    else:
        print(
            "Training skipped: need at least 2 customers, 2 books, and enough interactions.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
