"""
Deep learning behavior model — ported from Django to pure Python.

Identical logic to the original model_behavior.py; only the
settings import is replaced with app.config.
"""
from __future__ import annotations

import logging
import os
import random
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import torch
import torch.nn as nn

from app import config as settings

logger = logging.getLogger(__name__)

_load_lock = threading.Lock()
_cached: Optional[Tuple[float, str, "BehaviorPredictor"]] = None

COMPLETED_STATUSES = frozenset({"PAID", "SHIPPED", "DELIVERED"})


def resolve_torch_device(spec: str) -> torch.device:
    """Map BEHAVIOR_TORCH_DEVICE to a torch.device."""
    s = (spec or "cpu").strip().lower()
    if s == "auto":
        if torch.cuda.is_available():
            dev = torch.device("cuda:0")
            logger.info("behavior model device (auto): %s", dev)
            return dev
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            dev = torch.device("mps")
            logger.info("behavior model device (auto): %s", dev)
            return dev
        return torch.device("cpu")

    if s.startswith("cuda"):
        if not torch.cuda.is_available():
            logger.warning(
                "behavior model: %r requested but CUDA is not available; using CPU", spec
            )
            return torch.device("cpu")
        return torch.device(spec)

    if s == "mps":
        if not getattr(torch.backends, "mps", None) or not torch.backends.mps.is_available():
            logger.warning("behavior model: mps requested but MPS is not available; using CPU")
            return torch.device("cpu")
        return torch.device("mps")

    return torch.device("cpu")


def behavior_torch_device() -> torch.device:
    """Device from config (BEHAVIOR_TORCH_DEVICE)."""
    raw = getattr(settings, "BEHAVIOR_TORCH_DEVICE", "cpu")
    return resolve_torch_device(raw)


def _orders_to_user_books(orders: List[dict]) -> Dict[int, Set[int]]:
    out: Dict[int, Set[int]] = defaultdict(set)
    for order in orders:
        if order.get("status") not in COMPLETED_STATUSES:
            continue
        cid = order.get("customer_id")
        if cid is None:
            continue
        for item in order.get("items", []):
            bid = item.get("book_id")
            if bid is not None:
                out[int(cid)].add(int(bid))
    return dict(out)


class BehaviorNCF(nn.Module):
    """User/item embeddings + MLP over concatenated vectors."""

    def __init__(
        self,
        n_users: int,
        n_items: int,
        embed_dim: int = 32,
        mlp_hidden: Tuple[int, ...] = (64, 32, 16),
    ):
        super().__init__()
        self.user_emb = nn.Embedding(n_users, embed_dim)
        self.item_emb = nn.Embedding(n_items, embed_dim)
        nn.init.normal_(self.user_emb.weight, std=0.01)
        nn.init.normal_(self.item_emb.weight, std=0.01)

        layers: List[nn.Module] = []
        in_dim = embed_dim * 2
        for h in mlp_hidden:
            layers.extend([nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(p=0.15)])
            in_dim = h
        layers.append(nn.Linear(in_dim, 1))
        self.mlp = nn.Sequential(*layers)

    def forward(self, user_idx: torch.Tensor, item_idx: torch.Tensor) -> torch.Tensor:
        u = self.user_emb(user_idx)
        v = self.item_emb(item_idx)
        x = torch.cat([u, v], dim=-1)
        return self.mlp(x).squeeze(-1)


class BehaviorPredictor:
    def __init__(
        self,
        model: BehaviorNCF,
        user_map: Dict[int, int],
        book_map: Dict[int, int],
        embed_dim: int,
        mlp_hidden: Tuple[int, ...],
    ):
        self.model = model
        self.user_map = user_map
        self.book_map = book_map
        self.embed_dim = embed_dim
        self.mlp_hidden = mlp_hidden

    @classmethod
    def load(cls, path: str, device: torch.device) -> Optional["BehaviorPredictor"]:
        if not os.path.isfile(path):
            return None
        try:
            try:
                ckpt = torch.load(path, map_location=device, weights_only=False)
            except TypeError:
                ckpt = torch.load(path, map_location=device)
        except Exception as exc:
            logger.warning("behavior model: failed to load %s: %s", path, exc)
            return None

        meta = ckpt.get("meta") or {}
        user_map = {int(k): int(v) for k, v in (meta.get("user_map") or {}).items()}
        book_map = {int(k): int(v) for k, v in (meta.get("book_map") or {}).items()}
        embed_dim = int(meta.get("embed_dim", 32))
        mlp_hidden = tuple(meta.get("mlp_hidden", [64, 32, 16]))

        n_users = int(meta.get("n_users", len(user_map)))
        n_items = int(meta.get("n_items", len(book_map)))
        model = BehaviorNCF(n_users, n_items, embed_dim=embed_dim, mlp_hidden=mlp_hidden)
        model.load_state_dict(ckpt["state_dict"])
        model.to(device)
        model.eval()
        return cls(model, user_map, book_map, embed_dim, mlp_hidden)

    @torch.no_grad()
    def top_k_unseen(
        self,
        customer_id: int,
        purchased: Set[int],
        limit: int,
        device: torch.device,
        batch_size: int = 512,
    ) -> List[Tuple[int, float]]:
        if customer_id not in self.user_map:
            return []
        u_idx = self.user_map[customer_id]
        candidates = [b for b in self.book_map if b not in purchased]
        if not candidates:
            return []

        u_tensor_full = torch.full((batch_size,), u_idx, dtype=torch.long, device=device)
        scores: List[Tuple[int, float]] = []
        self.model.eval()

        for start in range(0, len(candidates), batch_size):
            chunk = candidates[start : start + batch_size]
            i_idx = torch.tensor(
                [self.book_map[b] for b in chunk], dtype=torch.long, device=device
            )
            n = i_idx.size(0)
            logits = self.model(u_tensor_full[:n], i_idx)
            probs = torch.sigmoid(logits).cpu().tolist()
            for bid, p in zip(chunk, probs):
                scores.append((bid, float(p)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]


def get_predictor() -> Optional[BehaviorPredictor]:
    """Load predictor once; reload if checkpoint file changes."""
    global _cached
    if not getattr(settings, "BEHAVIOR_DL_ENABLED", True):
        return None
    path = getattr(settings, "BEHAVIOR_MODEL_PATH", "")
    if not path or not os.path.isfile(path):
        return None

    device = behavior_torch_device()
    device_key = str(device)
    mtime = os.path.getmtime(path)

    with _load_lock:
        if _cached is not None and _cached[0] == mtime and _cached[1] == device_key:
            return _cached[2]
        pred = BehaviorPredictor.load(path, device)
        if pred is None:
            _cached = None
            return None
        _cached = (mtime, device_key, pred)
        logger.info("Loaded behavior DL model from %s on %s", path, device_key)
        return pred


def recommend_from_behavior_model(
    customer_id: int,
    purchased_books: Set[int],
    limit: int,
) -> Optional[List[Tuple[int, float]]]:
    """Return (book_id, score) recommendations, or None if model unavailable."""
    pred = get_predictor()
    if pred is None:
        return None
    device = behavior_torch_device()
    ranked = pred.top_k_unseen(customer_id, purchased_books, limit, device=device)
    if not ranked:
        return None
    return ranked


def build_training_arrays(
    orders: List[dict],
) -> Optional[Tuple[List[Tuple[int, int]], Dict[int, int], Dict[int, int]]]:
    """From raw orders JSON, build positive (user_idx, item_idx) pairs and id maps."""
    ub = _orders_to_user_books(orders)
    if len(ub) < 2:
        return None

    all_users = sorted(ub.keys())
    all_books: Set[int] = set()
    for books in ub.values():
        all_books.update(books)
    all_books_sorted = sorted(all_books)
    if len(all_books_sorted) < 2:
        return None

    user_map = {u: i for i, u in enumerate(all_users)}
    book_map = {b: i for i, b in enumerate(all_books_sorted)}

    pairs_set: Set[Tuple[int, int]] = set()
    for u_raw, books in ub.items():
        ui = user_map[u_raw]
        for b_raw in books:
            pairs_set.add((ui, book_map[b_raw]))

    pairs = list(pairs_set)
    if len(pairs) < 4:
        return None

    return (
        pairs,
        {u: user_map[u] for u in all_users},
        {b: book_map[b] for b in all_books_sorted},
    )


def train_and_save(
    orders: List[dict],
    save_path: str,
    epochs: int = 25,
    embed_dim: int = 32,
    mlp_hidden: Tuple[int, ...] = (64, 32, 16),
    batch_size: int = 256,
    lr: float = 1e-3,
    seed: int = 42,
    device: Optional[str] = None,
) -> bool:
    """Train NCF on order history and write checkpoint to save_path."""
    built = build_training_arrays(orders)
    if not built:
        logger.warning("behavior model: insufficient order data for training")
        return False

    pairs, user_raw_to_idx, book_raw_to_idx = built
    n_users = len(user_raw_to_idx)
    n_items = len(book_raw_to_idx)
    random.seed(seed)
    torch.manual_seed(seed)

    user_items: Dict[int, Set[int]] = defaultdict(set)
    for u_idx, i_idx in pairs:
        user_items[u_idx].add(i_idx)

    all_item_indices = list(range(n_items))
    device_t = (
        resolve_torch_device(device) if device is not None else behavior_torch_device()
    )
    model = BehaviorNCF(n_users, n_items, embed_dim=embed_dim, mlp_hidden=mlp_hidden).to(
        device_t
    )
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    model.train()
    n_pairs = len(pairs)
    start = time.time()
    for epoch in range(epochs):
        random.shuffle(pairs)
        total_loss = 0.0
        steps = 0
        for start_i in range(0, n_pairs, batch_size):
            batch_pos = pairs[start_i : start_i + batch_size]
            if not batch_pos:
                continue
            users: List[int] = []
            items: List[int] = []
            labels: List[float] = []
            for u_idx, pos_i in batch_pos:
                users.append(u_idx)
                items.append(pos_i)
                labels.append(1.0)
                neg_i = random.choice(all_item_indices)
                guard = 0
                while neg_i in user_items[u_idx] and guard < 50:
                    neg_i = random.choice(all_item_indices)
                    guard += 1
                users.append(u_idx)
                items.append(neg_i)
                labels.append(0.0)

            u_t = torch.tensor(users, dtype=torch.long, device=device_t)
            i_t = torch.tensor(items, dtype=torch.long, device=device_t)
            y_t = torch.tensor(labels, dtype=torch.float32, device=device_t)
            opt.zero_grad()
            logits = model(u_t, i_t)
            loss = loss_fn(logits, y_t)
            loss.backward()
            opt.step()
            total_loss += float(loss.item())
            steps += 1

        if steps:
            logger.info(
                "behavior model epoch %s/%s loss=%.4f",
                epoch + 1,
                epochs,
                total_loss / steps,
            )

    model.eval()
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    meta = {
        "user_map": {str(k): v for k, v in user_raw_to_idx.items()},
        "book_map": {str(k): v for k, v in book_raw_to_idx.items()},
        "n_users": n_users,
        "n_items": n_items,
        "embed_dim": embed_dim,
        "mlp_hidden": list(mlp_hidden),
        "trained_pairs": n_pairs,
        "epochs": epochs,
    }
    ckpt = {"state_dict": model.state_dict(), "meta": meta}
    torch.save(ckpt, save_path)
    logger.info(
        "behavior model saved to %s (%.1fs, users=%s items=%s pairs=%s)",
        save_path,
        time.time() - start,
        n_users,
        n_items,
        n_pairs,
    )
    return True


def clear_predictor_cache() -> None:
    global _cached
    with _load_lock:
        _cached = None
