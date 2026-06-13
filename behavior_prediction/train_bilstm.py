from pathlib import Path

from train_behavior_models import DEFAULT_OUTPUT_DIR, parse_args, run_training


def main() -> None:
    args = parse_args()
    if args.output_dir == DEFAULT_OUTPUT_DIR:
        args.output_dir = Path(__file__).resolve().parent / "outputs_bilstm"
    run_training(["bilstm"], args)


if __name__ == "__main__":
    main()
