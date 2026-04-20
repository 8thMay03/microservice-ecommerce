from django.conf import settings
from django.core.management.base import BaseCommand

from recommender.engine import _fetch_all_orders
from recommender.model_sequence_rnn import train_all_three


class Command(BaseCommand):
    help = (
        "Train RNN, LSTM, and BiLSTM sequence models that predict the next customer "
        "behavior event (view / click / add_to_cart / purchase). Data merges "
        "BehaviorEvent rows with completed orders from order-service."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seq-len",
            type=int,
            default=8,
            help="Sliding window length (default 8).",
        )
        parser.add_argument(
            "--epochs",
            type=int,
            default=20,
            help="Epochs per model (default 20).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=64,
            help="Batch size (default 64).",
        )
        parser.add_argument(
            "--embed-dim",
            type=int,
            default=32,
            help="Event embedding dimension (default 32).",
        )
        parser.add_argument(
            "--hidden-size",
            type=int,
            default=64,
            help="RNN/LSTM hidden size (default 64).",
        )
        parser.add_argument(
            "--rnn-out",
            type=str,
            default="",
            help="Override RNN checkpoint path (default: BEHAVIOR_SEQ_RNN_PATH).",
        )
        parser.add_argument(
            "--lstm-out",
            type=str,
            default="",
            help="Override LSTM checkpoint path (default: BEHAVIOR_SEQ_LSTM_PATH).",
        )
        parser.add_argument(
            "--bilstm-out",
            type=str,
            default="",
            help="Override BiLSTM checkpoint path (default: BEHAVIOR_SEQ_BILSTM_PATH).",
        )
        parser.add_argument(
            "--device",
            type=str,
            default=None,
            help="Torch device: cpu, cuda, cuda:0, mps, auto. Default: BEHAVIOR_TORCH_DEVICE.",
        )

    def handle(self, *args, **options):
        rnn_path = options["rnn_out"] or getattr(
            settings, "BEHAVIOR_SEQ_RNN_PATH", ""
        )
        lstm_path = options["lstm_out"] or getattr(
            settings, "BEHAVIOR_SEQ_LSTM_PATH", ""
        )
        bilstm_path = options["bilstm_out"] or getattr(
            settings, "BEHAVIOR_SEQ_BILSTM_PATH", ""
        )
        if not (rnn_path and lstm_path and bilstm_path):
            self.stderr.write(
                "Sequence model paths are not configured. Set BEHAVIOR_SEQ_*_PATH or pass --*-out."
            )
            return

        orders = _fetch_all_orders()
        if not orders:
            self.stderr.write(
                "No completed orders from order-service; training may still use BehaviorEvent rows only."
            )

        metrics = train_all_three(
            orders,
            rnn_path=rnn_path,
            lstm_path=lstm_path,
            bilstm_path=bilstm_path,
            seq_len=options["seq_len"],
            epochs=options["epochs"],
            batch_size=options["batch_size"],
            embed_dim=options["embed_dim"],
            hidden_size=options["hidden_size"],
            device_spec=options["device"],
        )

        paths = {"rnn": rnn_path, "lstm": lstm_path, "bilstm": bilstm_path}
        for name, m in metrics.items():
            if m is None:
                self.stderr.write(
                    self.style.WARNING(
                        f"{name}: skipped (not enough sequence samples; "
                        f"lower --seq-len or add BehaviorEvent / order history)."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{name}: val_accuracy={m['val_accuracy']:.4f} "
                        f"n_samples={int(m['n_samples'])} -> {paths[name]}"
                    )
                )
