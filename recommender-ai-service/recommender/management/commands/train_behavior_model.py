from django.conf import settings
from django.core.management.base import BaseCommand

from recommender.engine import _fetch_all_orders
from recommender.model_behavior import clear_predictor_cache, train_and_save


class Command(BaseCommand):
    help = (
        "Train the deep learning behavior model (NCF) from order-service history "
        "and save weights to BEHAVIOR_MODEL_PATH."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--epochs",
            type=int,
            default=25,
            help="Training epochs (default 25).",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Override output path (default: settings.BEHAVIOR_MODEL_PATH).",
        )
        parser.add_argument(
            "--device",
            type=str,
            default=None,
            help=(
                "torch device override: cpu, cuda, cuda:0, mps, auto. "
                "Default: BEHAVIOR_TORCH_DEVICE from settings/env."
            ),
        )

    def handle(self, *args, **options):
        path = options["output"] or getattr(
            settings, "BEHAVIOR_MODEL_PATH", ""
        )
        if not path:
            self.stderr.write(
                "BEHAVIOR_MODEL_PATH is not set. Configure it in settings or pass --output."
            )
            return

        orders = _fetch_all_orders()
        if not orders:
            self.stderr.write("No completed orders returned from order-service.")
            return

        ok = train_and_save(
            orders,
            save_path=path,
            epochs=options["epochs"],
            device=options["device"],
        )
        if ok:
            clear_predictor_cache()
            self.stdout.write(self.style.SUCCESS(f"Training finished. Checkpoint: {path}"))
        else:
            self.stderr.write(
                "Training skipped: need at least 2 customers, 2 books, and enough interactions."
            )
