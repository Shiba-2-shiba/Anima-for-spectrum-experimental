from typing import Optional

import torch

from .helpers import safe_float_timestep


def get_schedule_from_c(c: dict) -> Optional[torch.Tensor]:
    try:
        transformer_options = c.get("transformer_options", {})
        if not isinstance(transformer_options, dict):
            return None

        sigmas = transformer_options.get("sample_sigmas")
        if sigmas is None:
            sigmas = transformer_options.get("sigmas")

        if torch.is_tensor(sigmas) and sigmas.numel() > 1:
            return sigmas.detach().flatten().float()
    except Exception:
        return None
    return None


def get_schedule_step_count(c: dict) -> Optional[int]:
    sigmas = get_schedule_from_c(c)
    if sigmas is None or sigmas.numel() <= 1:
        return None
    return int(sigmas.numel())


def get_schedule_last_step_index(c: dict) -> Optional[int]:
    step_count = get_schedule_step_count(c)
    if step_count is None:
        return None
    return max(step_count - 1, 1)


def progress_from_schedule(timestep, c: dict) -> Optional[float]:
    sigmas = get_schedule_from_c(c)
    if sigmas is None or sigmas.numel() <= 1:
        return None

    try:
        t_value = safe_float_timestep(timestep)
        target = torch.tensor([t_value], device=sigmas.device, dtype=sigmas.dtype)
        idx = int((sigmas - target).abs().argmin().item())
        denom = max(1, int(sigmas.numel()) - 1)
        return float(idx) / float(denom)
    except Exception:
        return None


def estimate_total_steps(current_step: int, c: dict, fallback: int = 50) -> int:
    step_count = get_schedule_step_count(c)
    if step_count is not None:
        return step_count
    return max(int(fallback), int(current_step) + 1, 1)


def estimate_last_step_index(total_steps: int) -> int:
    return max(int(total_steps) - 1, 1)


def should_reset_for_new_pass(timestep: float, last_timestep: float, eps: float = 1e-7) -> bool:
    return bool(timestep > float(last_timestep) + eps)