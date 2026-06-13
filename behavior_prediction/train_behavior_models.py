import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from torch import nn
from torch.utils.data import DataLoader, Dataset

from bilstm_model import BiLSTMBehaviorClassifier
from lstm_model import LSTMBehaviorClassifier
from rnn_model import RNNBehaviorClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "behavior-data" / "data_user500.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


@dataclass
class ModelResult:
    name: str
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    f1_weighted: float
    best_val_f1_macro: float
    epochs_trained: int


class BehaviorSequenceDataset(Dataset):
    def __init__(
        self,
        samples: Sequence[Tuple[List[int], List[int], int]],
    ) -> None:
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        product_ids, action_ids, target = self.samples[index]
        return (
            torch.tensor(product_ids, dtype=torch.long),
            torch.tensor(action_ids, dtype=torch.long),
            torch.tensor(target, dtype=torch.long),
        )


MODEL_FACTORIES = {
    "rnn": RNNBehaviorClassifier,
    "lstm": LSTMBehaviorClassifier,
    "bilstm": BiLSTMBehaviorClassifier,
}


def create_model(
    model_name: str,
    num_products: int,
    num_actions: int,
    args: argparse.Namespace,
) -> nn.Module:
    if model_name not in MODEL_FACTORIES:
        raise ValueError(f"Unsupported model_name: {model_name}")
    model_class = MODEL_FACTORIES[model_name]
    return model_class(
        num_products=num_products,
        num_actions=num_actions,
        product_embedding_dim=args.product_embedding_dim,
        action_embedding_dim=args.action_embedding_dim,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
    )


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_rows(csv_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required_columns = {"user_id", "product_id", "action", "timestamp"}
        missing = required_columns.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns in {csv_path}: {sorted(missing)}")
        for row in reader:
            rows.append(row)
    return rows


def build_vocab(values: Iterable[str]) -> Dict[str, int]:
    unique_values = sorted(set(values))
    return {value: index + 1 for index, value in enumerate(unique_values)}


def split_users(
    users: Sequence[str],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> Tuple[set, set, set]:
    shuffled_users = list(users)
    rng = random.Random(seed)
    rng.shuffle(shuffled_users)

    train_end = int(len(shuffled_users) * train_ratio)
    val_end = train_end + int(len(shuffled_users) * val_ratio)
    return (
        set(shuffled_users[:train_end]),
        set(shuffled_users[train_end:val_end]),
        set(shuffled_users[val_end:]),
    )


def make_samples(
    rows: Sequence[Dict[str, str]],
    user_ids: set,
    product_to_id: Dict[str, int],
    action_to_id: Dict[str, int],
    sequence_length: int,
) -> List[Tuple[List[int], List[int], int]]:
    histories: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["user_id"] in user_ids:
            histories[row["user_id"]].append(row)

    samples: List[Tuple[List[int], List[int], int]] = []
    for user_history in histories.values():
        sorted_history = sorted(user_history, key=lambda item: item["timestamp"])
        if len(sorted_history) <= sequence_length:
            continue

        for target_index in range(sequence_length, len(sorted_history)):
            window = sorted_history[target_index - sequence_length : target_index]
            target = sorted_history[target_index]
            product_ids = [product_to_id[item["product_id"]] for item in window]
            action_ids = [action_to_id[item["action"]] for item in window]
            target_id = action_to_id[target["action"]] - 1
            samples.append((product_ids, action_ids, target_id))
    return samples


def get_class_weights(samples: Sequence[Tuple[List[int], List[int], int]], num_classes: int) -> torch.Tensor:
    targets = [target for _, _, target in samples]
    counts = Counter(targets)
    total = sum(counts.values())
    weights = [total / max(counts.get(class_id, 1), 1) for class_id in range(num_classes)]
    normalized = np.array(weights, dtype=np.float32)
    normalized = normalized / normalized.mean()
    return torch.tensor(normalized, dtype=torch.float32)


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float]:
    model.train()
    running_loss = 0.0
    predictions: List[int] = []
    targets: List[int] = []

    for product_ids, action_ids, labels in loader:
        product_ids = product_ids.to(device)
        action_ids = action_ids.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = model(product_ids, action_ids)
        loss = criterion(logits, labels)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
        optimizer.step()

        running_loss += loss.item() * labels.size(0)
        predictions.extend(logits.argmax(dim=1).detach().cpu().tolist())
        targets.extend(labels.detach().cpu().tolist())

    loss_value = running_loss / len(loader.dataset)
    f1_value = f1_score(targets, predictions, average="macro", zero_division=0)
    return loss_value, f1_value


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float, List[int], List[int]]:
    model.eval()
    running_loss = 0.0
    predictions: List[int] = []
    targets: List[int] = []

    for product_ids, action_ids, labels in loader:
        product_ids = product_ids.to(device)
        action_ids = action_ids.to(device)
        labels = labels.to(device)
        logits = model(product_ids, action_ids)
        loss = criterion(logits, labels)

        running_loss += loss.item() * labels.size(0)
        predictions.extend(logits.argmax(dim=1).cpu().tolist())
        targets.extend(labels.cpu().tolist())

    loss_value = running_loss / len(loader.dataset)
    f1_value = f1_score(targets, predictions, average="macro", zero_division=0)
    return loss_value, f1_value, predictions, targets


def train_model(
    model_name: str,
    num_products: int,
    num_actions: int,
    train_loader: DataLoader,
    val_loader: DataLoader,
    class_weights: torch.Tensor,
    args: argparse.Namespace,
    device: torch.device,
) -> Tuple[nn.Module, Dict[str, List[float]], float]:
    model = create_model(
        model_name=model_name,
        num_products=num_products,
        num_actions=num_actions,
        args=args,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))

    history = {
        "train_loss": [],
        "train_f1_macro": [],
        "val_loss": [],
        "val_f1_macro": [],
    }
    best_state = None
    best_val_f1 = -1.0
    patience_counter = 0

    for _ in range(args.epochs):
        train_loss, train_f1 = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_f1, _, _ = evaluate(model, val_loader, criterion, device)

        history["train_loss"].append(train_loss)
        history["train_f1_macro"].append(train_f1)
        history["val_loss"].append(val_loss)
        history["val_f1_macro"].append(val_f1)

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= args.patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, history, best_val_f1


def compute_result(
    name: str,
    y_true: Sequence[int],
    y_pred: Sequence[int],
    best_val_f1_macro: float,
    epochs_trained: int,
) -> ModelResult:
    return ModelResult(
        name=name,
        accuracy=accuracy_score(y_true, y_pred),
        precision_macro=precision_score(y_true, y_pred, average="macro", zero_division=0),
        recall_macro=recall_score(y_true, y_pred, average="macro", zero_division=0),
        f1_macro=f1_score(y_true, y_pred, average="macro", zero_division=0),
        f1_weighted=f1_score(y_true, y_pred, average="weighted", zero_division=0),
        best_val_f1_macro=best_val_f1_macro,
        epochs_trained=epochs_trained,
    )


def save_plots(
    output_dir: Path,
    histories: Dict[str, Dict[str, List[float]]],
    results: Sequence[ModelResult],
    best_name: str,
    y_true: Sequence[int],
    y_pred: Sequence[int],
    labels: Sequence[str],
) -> None:
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 5))
    for model_name, history in histories.items():
        epochs = range(1, len(history["val_f1_macro"]) + 1)
        plt.plot(epochs, history["train_f1_macro"], linestyle="--", label=f"{model_name} train")
        plt.plot(epochs, history["val_f1_macro"], label=f"{model_name} val")
    plt.title("Macro F1 during training")
    plt.xlabel("Epoch")
    plt.ylabel("Macro F1")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "training_f1.png", dpi=160)
    plt.close()

    plt.figure(figsize=(10, 5))
    for model_name, history in histories.items():
        epochs = range(1, len(history["val_loss"]) + 1)
        plt.plot(epochs, history["train_loss"], linestyle="--", label=f"{model_name} train")
        plt.plot(epochs, history["val_loss"], label=f"{model_name} val")
    plt.title("Loss during training")
    plt.xlabel("Epoch")
    plt.ylabel("Cross entropy loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "training_loss.png", dpi=160)
    plt.close()

    metric_names = ["accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted"]
    x = np.arange(len(metric_names))
    width = 0.24
    plt.figure(figsize=(11, 5))
    for index, result in enumerate(results):
        values = [getattr(result, metric_name) for metric_name in metric_names]
        plt.bar(x + (index - 1) * width, values, width, label=result.name)
    plt.xticks(x, [name.replace("_", " ") for name in metric_names], rotation=10)
    plt.ylim(0, 1)
    plt.title("Test metrics comparison")
    plt.ylabel("Score")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "model_comparison.png", dpi=160)
    plt.close()

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))
    plt.figure(figsize=(7, 6))
    plt.imshow(cm, cmap="Blues")
    plt.title(f"Confusion matrix - {best_name}")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.xticks(range(len(labels)), labels, rotation=30, ha="right")
    plt.yticks(range(len(labels)), labels)
    for row in range(cm.shape[0]):
        for col in range(cm.shape[1]):
            plt.text(col, row, str(cm[row, col]), ha="center", va="center", color="black")
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(output_dir / "best_confusion_matrix.png", dpi=160)
    plt.close()


def build_selection_note(best: ModelResult, all_results: Sequence[ModelResult]) -> str:
    sorted_results = sorted(all_results, key=lambda item: item.f1_macro, reverse=True)
    runner_up = sorted_results[1] if len(sorted_results) > 1 else None
    lines = [
        f"Model duoc chon: {best.name}",
        (
            "Ly do: macro F1 tren tap test cao nhat "
            f"({best.f1_macro:.4f}), phu hop hon accuracy khi cac lop hanh vi bi lech."
        ),
        (
            f"Do chinh xac: {best.accuracy:.4f}; precision macro: {best.precision_macro:.4f}; "
            f"recall macro: {best.recall_macro:.4f}; weighted F1: {best.f1_weighted:.4f}."
        ),
    ]
    if runner_up is not None:
        gap = best.f1_macro - runner_up.f1_macro
        lines.append(f"So voi mo hinh dung thu hai ({runner_up.name}), macro F1 chenh {gap:.4f}.")
    lines.append(
        "Nhan xet: Neu confusion matrix con nham nhieu o lop it mau, nen tang du lieu, "
        "thu them feature thoi gian, hoac tinh chinh class weight/sequence_length."
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train RNN, LSTM and BiLSTM models for behavior prediction.")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sequence-length", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--patience", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--product-embedding-dim", type=int, default=32)
    parser.add_argument("--action-embedding-dim", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=0.0001)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(args.data_path)
    product_to_id = build_vocab(row["product_id"] for row in rows)
    action_to_id = build_vocab(row["action"] for row in rows)
    id_to_action = {index - 1: action for action, index in action_to_id.items()}

    users = sorted({row["user_id"] for row in rows})
    train_users, val_users, test_users = split_users(users, train_ratio=0.7, val_ratio=0.15, seed=args.seed)
    train_samples = make_samples(rows, train_users, product_to_id, action_to_id, args.sequence_length)
    val_samples = make_samples(rows, val_users, product_to_id, action_to_id, args.sequence_length)
    test_samples = make_samples(rows, test_users, product_to_id, action_to_id, args.sequence_length)

    if not train_samples or not val_samples or not test_samples:
        raise ValueError("Not enough samples. Try reducing --sequence-length.")

    train_loader = DataLoader(BehaviorSequenceDataset(train_samples), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(BehaviorSequenceDataset(val_samples), batch_size=args.batch_size)
    test_loader = DataLoader(BehaviorSequenceDataset(test_samples), batch_size=args.batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    class_weights = get_class_weights(train_samples, num_classes=len(action_to_id))

    histories: Dict[str, Dict[str, List[float]]] = {}
    results: List[ModelResult] = []
    reports: Dict[str, Dict[str, object]] = {}
    trained_models: Dict[str, nn.Module] = {}
    predictions_by_model: Dict[str, Tuple[List[int], List[int]]] = {}

    print(f"Device: {device}")
    print(f"Samples - train: {len(train_samples)}, val: {len(val_samples)}, test: {len(test_samples)}")
    print(f"Actions: {', '.join(id_to_action[index] for index in sorted(id_to_action))}")

    criterion_for_eval = nn.CrossEntropyLoss(weight=class_weights.to(device))
    for model_name in ["rnn", "lstm", "bilstm"]:
        print(f"\nTraining {model_name}...")
        model, history, best_val_f1 = train_model(
            model_name=model_name,
            num_products=len(product_to_id) + 1,
            num_actions=len(action_to_id) + 1,
            train_loader=train_loader,
            val_loader=val_loader,
            class_weights=class_weights,
            args=args,
            device=device,
        )
        _, _, test_predictions, test_targets = evaluate(model, test_loader, criterion_for_eval, device)
        result = compute_result(
            model_name,
            test_targets,
            test_predictions,
            best_val_f1_macro=best_val_f1,
            epochs_trained=len(history["val_f1_macro"]),
        )
        histories[model_name] = history
        results.append(result)
        reports[model_name] = classification_report(
            test_targets,
            test_predictions,
            target_names=[id_to_action[index] for index in sorted(id_to_action)],
            zero_division=0,
            output_dict=True,
        )
        trained_models[model_name] = model
        predictions_by_model[model_name] = (test_targets, test_predictions)
        print(f"{model_name}: accuracy={result.accuracy:.4f}, macro_f1={result.f1_macro:.4f}")

    best_result = max(results, key=lambda item: item.f1_macro)
    best_model = trained_models[best_result.name]
    best_y_true, best_y_pred = predictions_by_model[best_result.name]
    label_names = [id_to_action[index] for index in sorted(id_to_action)]

    torch.save(
        {
            "model_name": best_result.name,
            "model_state_dict": best_model.state_dict(),
            "model_config": {
                "num_products": len(product_to_id) + 1,
                "num_actions": len(action_to_id) + 1,
                "sequence_length": args.sequence_length,
                "product_embedding_dim": args.product_embedding_dim,
                "action_embedding_dim": args.action_embedding_dim,
                "hidden_size": args.hidden_size,
                "num_layers": args.num_layers,
                "dropout": args.dropout,
            },
            "product_to_id": product_to_id,
            "action_to_id": action_to_id,
            "id_to_action": id_to_action,
            "metrics": asdict(best_result),
        },
        args.output_dir / "model_best.pt",
    )

    metrics_payload = {
        "data_path": str(args.data_path),
        "sequence_length": args.sequence_length,
        "split": {
            "train_users": len(train_users),
            "val_users": len(val_users),
            "test_users": len(test_users),
            "train_samples": len(train_samples),
            "val_samples": len(val_samples),
            "test_samples": len(test_samples),
        },
        "results": [asdict(result) for result in results],
        "classification_reports": reports,
        "best_model": asdict(best_result),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    (args.output_dir / "model_selection_note.txt").write_text(
        build_selection_note(best_result, results),
        encoding="utf-8",
    )
    save_plots(args.output_dir, histories, results, best_result.name, best_y_true, best_y_pred, label_names)

    print("\nBest model:", best_result.name)
    print(build_selection_note(best_result, results))
    print(f"\nSaved outputs to: {args.output_dir}")


if __name__ == "__main__":
    main()
