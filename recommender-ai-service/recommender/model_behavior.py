"""
Deep learning behavior model for storefront recommendations.

Neural Collaborative Filtering (NCF-style): user + item embeddings fused
through an MLP to predict affinity. Training merges completed purchases
with optional view / click / add_to_cart events (weighted positives),
then uses weighted BCE with negative sampling.

Artifacts: single checkpoint file (state_dict + id maps + hparams).
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
from django.conf import settings

logger = logging.getLogger(__name__)

_load_lock = threading.Lock()
# (checkpoint mtime, device string, predictor) — device part avoids stale cache when switching CPU/GPU
_cached: Optional[Tuple[float, str, "BehaviorPredictor"]] = None


COMPLETED_STATUSES = frozenset({"PAID", "SHIPPED", "DELIVERED"})


def resolve_torch_device(spec: str) -> torch.device:
    """
    Map BEHAVIOR_TORCH_DEVICE to a torch.device.

    - auto: CUDA if available, else Apple MPS if available, else CPU
    - cuda / cuda:0: use GPU when torch was built with CUDA and runtime is available
    - mps: Apple Silicon GPU when available
    - cpu: always CPU
    """
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
                "behavior model: %r requested but CUDA is not available; using CPU",
                spec,
            )
            return torch.device("cpu")
        return torch.device(spec)

    if s == "mps":
        if not getattr(torch.backends, "mps", None) or not torch.backends.mps.is_available():
            logger.warning(
                "behavior model: mps requested but MPS is not available; using CPU"
            )
            return torch.device("cpu")
        return torch.device("mps")

    return torch.device("cpu")


def behavior_torch_device() -> torch.device:
    """Device from Django settings (BEHAVIOR_TORCH_DEVICE)."""
    raw = getattr(settings, "BEHAVIOR_TORCH_DEVICE", "cpu")
    return resolve_torch_device(raw)


def _product_id_from_order_item(item: dict) -> Optional[int]:
    """order-service uses product_id; legacy payloads may use book_id."""
    pid = item.get("product_id")
    if pid is not None:
        return int(pid)
    bid = item.get("book_id")
    if bid is not None:
        return int(bid)
    return None


def behavior_event_weights() -> Dict[str, float]:
    """Max affinity contributed by each event type (orders use BEHAVIOR_WEIGHT_PURCHASE)."""
    return {
        "view": float(getattr(settings, "BEHAVIOR_WEIGHT_VIEW", 0.15)),
        "click": float(getattr(settings, "BEHAVIOR_WEIGHT_CLICK", 0.4)),
        "add_to_cart": float(getattr(settings, "BEHAVIOR_WEIGHT_ADD_TO_CART", 0.75)),
    }


def build_user_item_affinity(
    orders: List[dict],
    events: Optional[List[dict]] = None,
) -> Dict[int, Dict[int, float]]:
    """
    Per customer, per product: max signal strength in (0, 1].
    Purchases from completed orders use BEHAVIOR_WEIGHT_PURCHASE.
    """
    purchase_w = float(getattr(settings, "BEHAVIOR_WEIGHT_PURCHASE", 1.0))
    purchase_w = max(0.0, min(1.0, purchase_w))
    ev_weights = behavior_event_weights()
    out: Dict[int, Dict[int, float]] = defaultdict(dict)

    for order in orders:
        if order.get("status") not in COMPLETED_STATUSES:
            continue
        cid = order.get("customer_id")
        if cid is None:
            continue
        cid = int(cid)
        for item in order.get("items", []):
            pid = _product_id_from_order_item(item)
            if pid is None:
                continue
            cur = out[cid].get(pid, 0.0)
            out[cid][pid] = max(cur, purchase_w)

    for ev in events or []:
        try:
            cid = int(ev["customer_id"])
            pid = int(ev["product_id"])
        except (KeyError, TypeError, ValueError):
            continue
        et = str(ev.get("event_type") or "").strip().lower()
        w = float(ev_weights.get(et, 0.0))
        if w <= 0.0:
            continue
        w = max(0.0, min(1.0, w))
        cur = out[cid].get(pid, 0.0)
        out[cid][pid] = max(cur, w)

    return {u: dict(items) for u, items in out.items()}


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
            layers.extend(
                [nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(p=0.15)]
            )
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

        u_tensor_full = torch.full(
            (batch_size,), u_idx, dtype=torch.long, device=device
        )
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
    """
    Return (product_id, score) recommendations, or None if model unavailable
    or user is out of vocabulary (caller should fall back to CF).
    """
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
    events: Optional[List[dict]] = None,
) -> Optional[Tuple[List[Tuple[int, int, float]], Dict[int, int], Dict[int, int]]]:
    """
    From orders plus optional behavior events, build weighted positive
    (user_idx, item_idx, affinity) triples and raw id maps (meta uses book_map key).
    """
    affinity = build_user_item_affinity(orders, events)
    if len(affinity) < 2:
        return None

    all_users = sorted(affinity.keys())
    all_items: Set[int] = set()
    for products in affinity.values():
        all_items.update(products.keys())
    all_items_sorted = sorted(all_items)
    if len(all_items_sorted) < 2:
        return None

    user_map = {u: i for i, u in enumerate(all_users)}
    item_map = {p: i for i, p in enumerate(all_items_sorted)}

    triples: List[Tuple[int, int, float]] = []
    for u_raw, prod_weights in affinity.items():
        ui = user_map[u_raw]
        for p_raw, w in prod_weights.items():
            triples.append((ui, item_map[p_raw], float(w)))

    if len(triples) < 4:
        return None

    return (
        triples,
        {u: user_map[u] for u in all_users},
        {p: item_map[p] for p in all_items_sorted},
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
    events: Optional[List[dict]] = None,
) -> bool:
    """
    Train NCF on merged purchase + storefront signals and write checkpoint to save_path.
    Returns False if not enough data.
    """
    built = build_training_arrays(orders, events=events)
    if not built:
        logger.warning("behavior model: insufficient training data")
        return False

    pairs, user_raw_to_idx, book_raw_to_idx = built
    n_users = len(user_raw_to_idx)
    n_items = len(book_raw_to_idx)
    random.seed(seed)
    torch.manual_seed(seed)

    user_items: Dict[int, Set[int]] = defaultdict(set)
    for u_idx, i_idx, _w in pairs:
        user_items[u_idx].add(i_idx)

    all_item_indices = list(range(n_items))
    device_t = (
        resolve_torch_device(device) if device is not None else behavior_torch_device()
    )
    model = BehaviorNCF(
        n_users, n_items, embed_dim=embed_dim, mlp_hidden=mlp_hidden
    ).to(device_t)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss(reduction="none")

    model.train()
    n_pairs = len(pairs)
    start = time.time()
    used_events = bool(events)
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
            weights: List[float] = []
            for u_idx, pos_i, pos_w in batch_pos:
                users.append(u_idx)
                items.append(pos_i)
                labels.append(1.0)
                weights.append(max(1e-6, min(1.0, float(pos_w))))
                neg_i = random.choice(all_item_indices)
                guard = 0
                while neg_i in user_items[u_idx] and guard < 50:
                    neg_i = random.choice(all_item_indices)
                    guard += 1
                users.append(u_idx)
                items.append(neg_i)
                labels.append(0.0)
                weights.append(1.0)

            u_t = torch.tensor(users, dtype=torch.long, device=device_t)
            i_t = torch.tensor(items, dtype=torch.long, device=device_t)
            y_t = torch.tensor(labels, dtype=torch.float32, device=device_t)
            w_t = torch.tensor(weights, dtype=torch.float32, device=device_t)
            opt.zero_grad()
            logits = model(u_t, i_t)
            loss = (loss_fn(logits, y_t) * w_t).mean()
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
        "trained_with_behavior_events": used_events,
        "behavior_weights": {
            "purchase": float(getattr(settings, "BEHAVIOR_WEIGHT_PURCHASE", 1.0)),
            **behavior_event_weights(),
        },
    }
    ckpt = {"state_dict": model.state_dict(), "meta": meta}
    torch.save(ckpt, save_path)
    logger.info(
        "behavior model saved to %s (%.1fs, users=%s items=%s pairs=%s events=%s)",
        save_path,
        time.time() - start,
        n_users,
        n_items,
        n_pairs,
        used_events,
    )
    return True


def clear_predictor_cache() -> None:
    global _cached
    with _load_lock:
        _cached = None
