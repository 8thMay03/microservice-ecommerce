"""
Sequence models (Vanilla RNN, LSTM, BiLSTM) for next customer behavior (event type).

Training data merges:
  - `BehaviorEvent` rows from the recommender DB (when present)
  - Completed orders from order-service (each line item → a purchase event at order time)

Target: classify the next event among EVENT_TYPES (multi-class).
"""
from __future__ import annotations

import logging
import os
import random
import time
from collections import defaultdict
from typing import Dict, List, Optional, Sequence as TypingSequence, Tuple

import torch
import torch.nn as nn
from django.utils import dateparse
from django.utils import timezone

from recommender.model_behavior import behavior_torch_device, resolve_torch_device

logger = logging.getLogger(__name__)

EVENT_TYPES: TypingSequence[str] = (
    "view",
    "click",
    "add_to_cart",
    "purchase",
)
EVENT_TO_IDX: Dict[str, int] = {e: i for i, e in enumerate(EVENT_TYPES)}
NUM_EVENT_CLASSES = len(EVENT_TYPES)


def _item_product_id(item: dict) -> Optional[int]:
    raw = item.get("product_id")
    if raw is None:
        raw = item.get("book_id")
    if raw is None:
        return None
    return int(raw)


def _parse_order_datetime(order: dict):
    v = order.get("created_at")
    if v is None:
        return None
    if hasattr(v, "tzinfo"):
        return v
    if isinstance(v, str):
        dt = dateparse.parse_datetime(v)
        if dt is None:
            return None
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    return None


def timeline_from_orders(orders: List[dict]) -> List[Tuple[int, object, int, Optional[int]]]:
    """
    Rows: (customer_id, sortable_datetime, event_type_idx, product_id).
    """
    rows: List[Tuple[int, object, int, Optional[int]]] = []
    purchase_idx = EVENT_TO_IDX["purchase"]
    for order in orders:
        status = (order.get("status") or "").upper()
        if status not in {"PAID", "SHIPPED", "DELIVERED"}:
            continue
        cid = order.get("customer_id")
        if cid is None:
            continue
        dt = _parse_order_datetime(order)
        if dt is None:
            continue
        cid = int(cid)
        for item in order.get("items") or []:
            pid = _item_product_id(item)
            rows.append((cid, dt, purchase_idx, pid))
    return rows


def timeline_from_orm() -> List[Tuple[int, object, int, Optional[int]]]:
    from recommender.models import BehaviorEvent

    rows: List[Tuple[int, object, int, Optional[int]]] = []
    for ev in BehaviorEvent.objects.all().order_by("id").iterator(chunk_size=2000):
        idx = EVENT_TO_IDX.get((ev.event_type or "").lower())
        if idx is None:
            continue
        rows.append(
            (
                int(ev.customer_id),
                ev.created_at,
                idx,
                int(ev.product_id) if ev.product_id is not None else None,
            )
        )
    return rows


def merge_timelines(
    orm_rows: List[Tuple[int, object, int, Optional[int]]],
    order_rows: List[Tuple[int, object, int, Optional[int]]],
) -> List[Tuple[int, object, int, Optional[int]]]:
    merged = list(orm_rows) + list(order_rows)
    merged.sort(key=lambda r: (r[0], r[1]))
    return merged


def build_xy_sequences(
    rows: List[Tuple[int, object, int, Optional[int]]],
    seq_len: int,
) -> Tuple[List[List[int]], List[int]]:
    """
    Per customer, sort by time; sliding windows of length seq_len → predict next class.
    """
    by_cust: Dict[int, List[Tuple[object, int]]] = defaultdict(list)
    for cid, dt, eidx, _pid in rows:
        by_cust[cid].append((dt, eidx))

    xs: List[List[int]] = []
    ys: List[int] = []
    for _cid, events in by_cust.items():
        events.sort(key=lambda t: t[0])
        indices = [e[1] for e in events]
        if len(indices) <= seq_len:
            continue
        for i in range(len(indices) - seq_len):
            xs.append(indices[i : i + seq_len])
            ys.append(indices[i + seq_len])
    return xs, ys


class VanillaRNNClassifier(nn.Module):
    def __init__(self, num_classes: int, embed_dim: int = 32, hidden_size: int = 64, num_layers: int = 1):
        super().__init__()
        self.emb = nn.Embedding(num_classes, embed_dim)
        self.rnn = nn.RNN(
            embed_dim,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            nonlinearity="tanh",
        )
        self.head = nn.Linear(hidden_size, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e = self.emb(x)
        out, h_n = self.rnn(e)
        last = out[:, -1, :]
        return self.head(last)


class LSTMClassifier(nn.Module):
    def __init__(self, num_classes: int, embed_dim: int = 32, hidden_size: int = 64, num_layers: int = 1):
        super().__init__()
        self.emb = nn.Embedding(num_classes, embed_dim)
        self.rnn = nn.LSTM(
            embed_dim,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )
        self.head = nn.Linear(hidden_size, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e = self.emb(x)
        out, _ = self.rnn(e)
        last = out[:, -1, :]
        return self.head(last)


class BiLSTMClassifier(nn.Module):
    def __init__(self, num_classes: int, embed_dim: int = 32, hidden_size: int = 64, num_layers: int = 1):
        super().__init__()
        self.emb = nn.Embedding(num_classes, embed_dim)
        self.rnn = nn.LSTM(
            embed_dim,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
        )
        self.head = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e = self.emb(x)
        out, _ = self.rnn(e)
        last = out[:, -1, :]
        return self.head(last)


def _make_model(kind: str, num_classes: int, embed_dim: int, hidden_size: int):
    k = kind.lower()
    if k == "rnn":
        return VanillaRNNClassifier(num_classes, embed_dim, hidden_size)
    if k == "lstm":
        return LSTMClassifier(num_classes, embed_dim, hidden_size)
    if k == "bilstm":
        return BiLSTMClassifier(num_classes, embed_dim, hidden_size)
    raise ValueError(f"Unknown model kind: {kind}")


def train_sequence_model(
    kind: str,
    xs: List[List[int]],
    ys: List[int],
    save_path: str,
    epochs: int = 20,
    batch_size: int = 64,
    embed_dim: int = 32,
    hidden_size: int = 64,
    lr: float = 1e-3,
    val_ratio: float = 0.15,
    seed: int = 42,
    device_spec: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    """
    Train one architecture; save checkpoint with meta.
    Returns metrics dict or None if not enough data.
    """
    n = len(ys)
    if n < 8:
        logger.warning("sequence %s: need at least 8 samples, got %s", kind, n)
        return None

    random.seed(seed)
    torch.manual_seed(seed)
    perm = list(range(n))
    random.shuffle(perm)
    n_val = max(1, int(n * val_ratio))
    val_idx = set(perm[:n_val])
    train_idx = [i for i in range(n) if i not in val_idx]

    x_t_all = torch.tensor(xs, dtype=torch.long)
    y_t_all = torch.tensor(ys, dtype=torch.long)

    if device_spec is not None:
        device = resolve_torch_device(device_spec)
    else:
        device = behavior_torch_device()

    model = _make_model(kind, NUM_EVENT_CLASSES, embed_dim, hidden_size).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()

    def batch_iterate(idxs: List[int], shuffle: bool):
        order = list(idxs)
        if shuffle:
            random.shuffle(order)
        for s in range(0, len(order), batch_size):
            chunk = order[s : s + batch_size]
            if not chunk:
                continue
            bx = x_t_all[chunk].to(device)
            by = y_t_all[chunk].to(device)
            yield bx, by

    t0 = time.time()
    model.train()
    for epoch in range(epochs):
        total = 0.0
        steps = 0
        for bx, by in batch_iterate(train_idx, shuffle=True):
            opt.zero_grad()
            logits = model(bx)
            loss = loss_fn(logits, by)
            loss.backward()
            opt.step()
            total += float(loss.item())
            steps += 1
        if steps:
            logger.info(
                "sequence %s epoch %s/%s train_loss=%.4f",
                kind,
                epoch + 1,
                epochs,
                total / steps,
            )

    model.eval()
    correct = 0
    total_v = 0
    with torch.no_grad():
        for bx, by in batch_iterate(list(val_idx), shuffle=False):
            logits = model(bx)
            pred = logits.argmax(dim=-1)
            correct += int((pred == by).sum().item())
            total_v += by.size(0)
    acc = correct / total_v if total_v else 0.0

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    meta = {
        "model_kind": kind.lower(),
        "event_types": list(EVENT_TYPES),
        "num_classes": NUM_EVENT_CLASSES,
        "seq_len": len(xs[0]) if xs else 0,
        "embed_dim": embed_dim,
        "hidden_size": hidden_size,
        "epochs": epochs,
        "n_samples": n,
        "val_accuracy": acc,
        "train_seconds": round(time.time() - t0, 2),
    }
    torch.save({"state_dict": model.state_dict(), "meta": meta}, save_path)
    logger.info(
        "sequence %s saved to %s val_acc=%.4f n=%s",
        kind,
        save_path,
        acc,
        n,
    )
    return {"val_accuracy": acc, "n_samples": float(n)}


def train_all_three(
    orders: List[dict],
    rnn_path: str,
    lstm_path: str,
    bilstm_path: str,
    seq_len: int = 8,
    epochs: int = 20,
    batch_size: int = 64,
    embed_dim: int = 32,
    hidden_size: int = 64,
    device_spec: Optional[str] = None,
) -> Dict[str, Optional[Dict[str, float]]]:
    orm_rows = timeline_from_orm()
    order_rows = timeline_from_orders(orders)
    rows = merge_timelines(orm_rows, order_rows)
    xs, ys = build_xy_sequences(rows, seq_len=seq_len)
    if device_spec is not None:
        dev_str = str(resolve_torch_device(device_spec))
    else:
        dev_str = str(behavior_torch_device())

    out: Dict[str, Optional[Dict[str, float]]] = {}
    out["rnn"] = train_sequence_model(
        "rnn",
        xs,
        ys,
        rnn_path,
        epochs=epochs,
        batch_size=batch_size,
        embed_dim=embed_dim,
        hidden_size=hidden_size,
        device_spec=dev_str,
    )
    out["lstm"] = train_sequence_model(
        "lstm",
        xs,
        ys,
        lstm_path,
        epochs=epochs,
        batch_size=batch_size,
        embed_dim=embed_dim,
        hidden_size=hidden_size,
        device_spec=dev_str,
    )
    out["bilstm"] = train_sequence_model(
        "bilstm",
        xs,
        ys,
        bilstm_path,
        epochs=epochs,
        batch_size=batch_size,
        embed_dim=embed_dim,
        hidden_size=hidden_size,
        device_spec=dev_str,
    )
    return out


def load_sequence_model(
    kind: str,
    path: str,
    device: Optional[torch.device] = None,
) -> Optional[Tuple[nn.Module, dict]]:
    """
    Load a trained sequence checkpoint. Returns (model, meta) or None if missing/invalid.
    """
    if not path or not os.path.isfile(path):
        return None
    if device is None:
        device = behavior_torch_device()
    try:
        try:
            ckpt = torch.load(path, map_location=device, weights_only=False)
        except TypeError:
            ckpt = torch.load(path, map_location=device)
    except Exception as exc:
        logger.warning("sequence model: failed to load %s: %s", path, exc)
        return None

    meta = ckpt.get("meta") or {}
    embed_dim = int(meta.get("embed_dim", 32))
    hidden_size = int(meta.get("hidden_size", 64))
    model = _make_model(kind, NUM_EVENT_CLASSES, embed_dim, hidden_size)
    model.load_state_dict(ckpt["state_dict"])
    model.to(device)
    model.eval()
    return model, meta


@torch.no_grad()
def predict_next_event_probs(
    kind: str,
    path: str,
    recent_event_indices: List[int],
    device: Optional[torch.device] = None,
) -> Optional[List[Tuple[str, float]]]:
    """
    Given the last `seq_len` event class indices (same order as training),
    return [(event_name, probability), ...] sorted by prob descending.
    """
    loaded = load_sequence_model(kind, path, device=device)
    if loaded is None:
        return None
    model, meta = loaded
    seq_len = int(meta.get("seq_len", len(recent_event_indices)))
    if len(recent_event_indices) != seq_len:
        logger.warning(
            "sequence predict: expected seq_len=%s got %s",
            seq_len,
            len(recent_event_indices),
        )
        return None
    if device is None:
        device = behavior_torch_device()
    x = torch.tensor([recent_event_indices], dtype=torch.long, device=device)
    logits = model(x)
    probs = torch.softmax(logits, dim=-1).cpu().tolist()[0]
    pairs = [(EVENT_TYPES[i], float(probs[i])) for i in range(len(EVENT_TYPES))]
    pairs.sort(key=lambda t: t[1], reverse=True)
    return pairs
