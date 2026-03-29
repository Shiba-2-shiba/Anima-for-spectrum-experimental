from typing import Any

import torch


def safe_float_timestep(timestep: Any) -> float:
    if torch.is_tensor(timestep):
        return float(timestep.flatten()[0].item())
    return float(timestep)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def batch_index_tensor(mask: torch.Tensor) -> torch.Tensor:
    return mask.nonzero(as_tuple=False).flatten()


def slice_if_batch(value: Any, index_tensor: torch.Tensor, batch_size: int) -> Any:
    if isinstance(value, torch.Tensor) and value.dim() > 0 and value.shape[0] == batch_size:
        return value[index_tensor.to(value.device)]
    return value


def slice_model_kwargs(kwargs: dict, index_tensor: torch.Tensor, batch_size: int) -> dict:
    c = kwargs.get("c", {})
    return {
        "input": kwargs["input"][index_tensor.to(kwargs["input"].device)],
        "timestep": slice_if_batch(kwargs["timestep"], index_tensor, batch_size),
        "c": {key: slice_if_batch(value, index_tensor, batch_size) for key, value in c.items()},
    }
