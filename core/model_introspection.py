from typing import List, Optional, Tuple

import torch.nn as nn


EXPLICIT_BLOCK_PATHS = (
    "blocks",
    "net.blocks",
    "model.blocks",
)


def _resolve_attr_path(obj, path: str):
    current = obj
    for part in path.split("."):
        if not hasattr(current, part):
            return None
        current = getattr(current, part)
    return current


def looks_like_supported_model(diffusion_model) -> bool:
    for path in EXPLICIT_BLOCK_PATHS:
        candidate = _resolve_attr_path(diffusion_model, path)
        if isinstance(candidate, nn.ModuleList) and len(candidate) >= 1:
            return True

    cls_name = diffusion_model.__class__.__name__.lower()
    mod_name = diffusion_model.__class__.__module__.lower()
    text = f"{mod_name} {cls_name}"
    return ("anima" in text) or ("cosmos" in text) or ("predict2" in text)


def _modulelist_score(name: str, module_list: nn.ModuleList) -> int:
    if len(module_list) < 4:
        return -10_000

    name_l = name.lower()
    score = 0

    for token, bonus in (
        ("blocks", 80),
        ("layers", 70),
        ("transformer", 40),
        ("dit", 35),
        ("double", 10),
        ("single", 10),
    ):
        if token in name_l:
            score += bonus

    score += min(len(module_list), 128)

    type_names = [module.__class__.__name__.lower() for module in module_list]
    unique_types = len(set(type_names))
    score += max(0, 30 - unique_types * 5)

    if any("block" in type_name for type_name in type_names):
        score += 30
    if any("layer" in type_name for type_name in type_names):
        score += 15

    if any(token in name_l for token in ("norm", "embed", "rope", "pos", "adapter", "proj")):
        score -= 40

    return score


def _explicit_block_container(diffusion_model) -> Optional[Tuple[str, nn.ModuleList]]:
    for path in EXPLICIT_BLOCK_PATHS:
        candidate = _resolve_attr_path(diffusion_model, path)
        if isinstance(candidate, nn.ModuleList) and len(candidate) >= 1:
            return path, candidate
    return None


def find_best_block_container(diffusion_model) -> Tuple[str, nn.ModuleList, List[Tuple[str, int]]]:
    explicit = _explicit_block_container(diffusion_model)
    if explicit is not None:
        name, module_list = explicit
        return name, module_list, [(name, len(module_list))]

    candidates = []
    for name, module in diffusion_model.named_modules():
        if isinstance(module, nn.ModuleList):
            score = _modulelist_score(name, module)
            if score > -1000:
                candidates.append((score, name, module))

    if not candidates:
        raise RuntimeError(
            "Could not find a repeated nn.ModuleList block container for this Anima/Cosmos-style diffusion model."
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, best_name, best_module = candidates[0]
    summary = [(name, len(module)) for _, name, module in candidates[:10]]
    return best_name, best_module, summary


def restore_all_previous_replay_patches(diffusion_model) -> int:
    restored = 0
    for module in diffusion_model.modules():
        if getattr(module, "_anima_replay_patched", False):
            original_forward = getattr(module, "_anima_replay_original_forward", None)
            if original_forward is not None:
                module.forward = original_forward
            if hasattr(module, "_anima_replay_patched"):
                delattr(module, "_anima_replay_patched")
            if hasattr(module, "_anima_replay_original_forward"):
                delattr(module, "_anima_replay_original_forward")
            restored += 1
    return restored
