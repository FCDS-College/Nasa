"""Label-free temporal model on frozen pretrained-backbone embeddings.

There are no ground-truth labels yet, so the head is trained to predict the
next frame embedding (self-supervised). Its per-step error is a change/anomaly
signal, NOT an accuracy metric. A regression head can be enabled once a labels
manifest exists.
"""
from __future__ import annotations

import glob
import os
import random
from typing import List, Optional

import numpy as np
import torch
import torch.nn as nn


def seed_everything(seed: int = 0) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def list_images(image_dir: str) -> List[str]:
    paths = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        paths += glob.glob(os.path.join(image_dir, ext))
    return sorted(paths)


@torch.no_grad()
def extract_embeddings(frames: List[np.ndarray], device: Optional[torch.device] = None,
                       batch_size: int = 32, weights: bool = True, arch: str = "resnet18") -> torch.Tensor:
    """RGB uint8 frames (H,W,3) -> (N, D) ResNet embeddings, AMP on CUDA."""
    import torchvision
    import cv2
    device = device or get_device()
    net = getattr(torchvision.models, arch)(weights="DEFAULT" if weights else None)
    net.fc = nn.Identity()
    net.eval().to(device)
    mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=device).view(1, 3, 1, 1)
    out = []
    for i in range(0, len(frames), batch_size):
        batch = np.stack([cv2.resize(f, (224, 224)) for f in frames[i:i + batch_size]])
        x = torch.from_numpy(batch).to(device).permute(0, 3, 1, 2).float() / 255.0
        with torch.autocast(device.type, enabled=device.type == "cuda"):
            out.append(net((x - mean) / std).float().cpu())
    return torch.cat(out)


class TemporalHead(nn.Module):
    def __init__(self, dim: int = 512, hidden: int = 128, n_targets: int = 0):
        super().__init__()
        self.gru = nn.GRU(dim, hidden, batch_first=True)
        self.next_emb = nn.Linear(hidden, dim)
        self.reg = nn.Linear(hidden, n_targets) if n_targets else None

    def forward(self, x):
        h, _ = self.gru(x)
        return self.next_emb(h), (self.reg(h.mean(1)) if self.reg else None)


def train_next_embedding(emb: torch.Tensor, epochs: int = 100, lr: float = 1e-3,
                         val_frac: float = 0.3, patience: int = 10, seed: int = 0,
                         device: Optional[torch.device] = None) -> dict:
    """Chronological split (no shuffling across time), early stopping on val loss."""
    seed_everything(seed)
    device = device or get_device()
    emb = (emb - emb.mean(0)) / (emb.std(0) + 1e-6)
    n_val = max(2, int(len(emb) * val_frac))
    tr, va = emb[:-n_val].unsqueeze(0).to(device), emb[-n_val - 1:].unsqueeze(0).to(device)
    model = TemporalHead(emb.shape[1]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    best, best_state, bad = float("inf"), None, 0
    for _ in range(epochs):
        model.train()
        pred, _ = model(tr[:, :-1])
        loss = nn.functional.mse_loss(pred, tr[:, 1:])
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        model.eval()
        with torch.no_grad():
            vp, _ = model(va[:, :-1])
            vl = nn.functional.mse_loss(vp, va[:, 1:]).item()
        if vl < best:
            best, bad = vl, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    # Baseline: predicting "no change" (copy previous embedding).
    copy_mse = nn.functional.mse_loss(va[:, :-1], va[:, 1:]).item()
    return {"model": model, "val_mse": best, "copy_previous_mse": copy_mse,
            "beats_baseline": best < copy_mse,
            "note": "self-supervised; not an accuracy metric"}
