import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import torch
from bilstm_model import BiLSTMBehaviorClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from torch import nn
from torch.utils.data import DataLoader, Dataset


MODEL_NAME = "bilstm"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "behavior-data" / "data_user500.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs_bilstm"


class BehaviorDataset(Dataset):
    def __init__(self, samples: Sequence[Tuple[List[int], List[int], int]]) -> None:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train BiLSTM model for customer behavior prediction.")
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


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def build_vocab(values: Sequence[str]) -> Dict[str, int]:
    return {value: index + 1 for index, value in enumerate(sorted(set(values)))}


def split_users(users: Sequence[str], seed: int) -> Tuple[set, set, set]:
    users = list(users)
    random.Random(seed).shuffle(users)
    train_end = int(len(users) * 0.7)
    val_end = train_end + int(len(users) * 0.15)
    return set(users[:train_end]), set(users[train_end:val_end]), set(users[val_end:])


def make_samples(
    rows: Sequence[Dict[str, str]],
    selected_users: set,
    product_to_id: Dict[str, int],
    action_to_id: Dict[str, int],
    sequence_length: int,
) -> List[Tuple[List[int], List[int], int]]:
    histories = defaultdict(list)
    for row in rows:
        if row["user_id"] in selected_users:
            histories[row["user_id"]].append(row)

    samples = []
    for history in histories.values():
        history = sorted(history, key=lambda row: row["timestamp"])
        for target_index in range(sequence_length, len(history)):
            window = history[target_index - sequence_length : target_index]
            target = history[target_index]
            product_ids = [product_to_id[item["product_id"]] for item in window]
            action_ids = [action_to_id[item["action"]] for item in window]
            target_id = action_to_id[target["action"]] - 1
            samples.append((product_ids, action_ids, target_id))
    return samples


def class_weights(samples: Sequence[Tuple[List[int], List[int], int]], num_classes: int) -> torch.Tensor:
    counts = Counter(target for _, _, target in samples)
    total = sum(counts.values())
    weights = np.array([total / max(counts.get(index, 1), 1) for index in range(num_classes)], dtype=np.float32)
    weights = weights / weights.mean()
    return torch.tensor(weights, dtype=torch.float32)


def train_epoch(model: nn.Module, loader: DataLoader, criterion: nn.Module, optimizer: torch.optim.Optimizer, device: torch.device) -> Tuple[float, float]:
    model.train()
    total_loss = 0.0
    y_true, y_pred = [], []
    for product_ids, action_ids, labels in loader:
        product_ids, action_ids, labels = product_ids.to(device), action_ids.to(device), labels.to(device)
        optimizer.zero_grad()
        logits = model(product_ids, action_ids)
        loss = criterion(logits, labels)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
        optimizer.step()
        total_loss += loss.item() * labels.size(0)
        y_true.extend(labels.cpu().tolist())
        y_pred.extend(logits.argmax(dim=1).detach().cpu().tolist())
    return total_loss / len(loader.dataset), f1_score(y_true, y_pred, average="macro", zero_division=0)


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device) -> Tuple[float, float, List[int], List[int]]:
    model.eval()
    total_loss = 0.0
    y_true, y_pred = [], []
    for product_ids, action_ids, labels in loader:
        product_ids, action_ids, labels = product_ids.to(device), action_ids.to(device), labels.to(device)
        logits = model(product_ids, action_ids)
        loss = criterion(logits, labels)
        total_loss += loss.item() * labels.size(0)
        y_true.extend(labels.cpu().tolist())
        y_pred.extend(logits.argmax(dim=1).cpu().tolist())
    return total_loss / len(loader.dataset), f1_score(y_true, y_pred, average="macro", zero_division=0), y_true, y_pred


def save_plots(output_dir: Path, history: Dict[str, List[float]], y_true: Sequence[int], y_pred: Sequence[int], labels: Sequence[str]) -> None:
    epochs = range(1, len(history["train_loss"]) + 1)
    plt.figure(figsize=(8, 5))
    plt.plot(epochs, history["train_loss"], marker="o", label="train_loss")
    plt.plot(epochs, history["val_loss"], marker="o", label="val_loss")
    plt.title("BiLSTM Train/Validation Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Cross entropy loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "bilstm_loss.png", dpi=160)
    plt.close()

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))
    plt.figure(figsize=(7, 6))
    plt.imshow(cm, cmap="Blues")
    plt.title("BiLSTM Confusion Matrix")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.xticks(range(len(labels)), labels, rotation=30, ha="right")
    plt.yticks(range(len(labels)), labels)
    for row in range(cm.shape[0]):
        for col in range(cm.shape[1]):
            plt.text(col, row, str(cm[row, col]), ha="center", va="center")
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(output_dir / "bilstm_confusion_matrix.png", dpi=160)
    plt.close()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(args.data_path)
    product_to_id = build_vocab([row["product_id"] for row in rows])
    action_to_id = build_vocab([row["action"] for row in rows])
    id_to_action = {index - 1: action for action, index in action_to_id.items()}
    labels = [id_to_action[index] for index in sorted(id_to_action)]

    train_users, val_users, test_users = split_users(sorted({row["user_id"] for row in rows}), args.seed)
    train_samples = make_samples(rows, train_users, product_to_id, action_to_id, args.sequence_length)
    val_samples = make_samples(rows, val_users, product_to_id, action_to_id, args.sequence_length)
    test_samples = make_samples(rows, test_users, product_to_id, action_to_id, args.sequence_length)

    train_loader = DataLoader(BehaviorDataset(train_samples), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(BehaviorDataset(val_samples), batch_size=args.batch_size)
    test_loader = DataLoader(BehaviorDataset(test_samples), batch_size=args.batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BiLSTMBehaviorClassifier(
        num_products=len(product_to_id) + 1,
        num_actions=len(action_to_id) + 1,
        product_embedding_dim=args.product_embedding_dim,
        action_embedding_dim=args.action_embedding_dim,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
    ).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights(train_samples, len(action_to_id)).to(device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)

    history = {"train_loss": [], "train_f1": [], "val_loss": [], "val_f1": []}
    best_state, best_val_f1, bad_epochs = None, -1.0, 0
    for epoch in range(1, args.epochs + 1):
        train_loss, train_f1 = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_f1, _, _ = evaluate(model, val_loader, criterion, device)
        history["train_loss"].append(train_loss)
        history["train_f1"].append(train_f1)
        history["val_loss"].append(val_loss)
        history["val_f1"].append(val_f1)
        print(f"Epoch {epoch:02d}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}, val_f1={val_f1:.4f}")

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
        if bad_epochs >= args.patience:
            break

    if best_state:
        model.load_state_dict(best_state)

    _, _, y_true, y_pred = evaluate(model, test_loader, criterion, device)
    metrics = {
        "model": MODEL_NAME,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "classification_report": classification_report(y_true, y_pred, target_names=labels, zero_division=0, output_dict=True),
    }

    torch.save(
        {
            "model_name": MODEL_NAME,
            "model_state_dict": model.state_dict(),
            "product_to_id": product_to_id,
            "action_to_id": action_to_id,
            "metrics": metrics,
        },
        args.output_dir / "model_best.pt",
    )
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    save_plots(args.output_dir, history, y_true, y_pred, labels)
    print(f"BiLSTM test macro F1: {metrics['f1_macro']:.4f}")
    print(f"Saved outputs to: {args.output_dir}")


if __name__ == "__main__":
    main()
