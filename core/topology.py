from dataclasses import asdict, dataclass
import inspect
from typing import Any, List, Optional

import torch.nn as nn

from .model_introspection import _modulelist_score, _resolve_attr_path


KNOWN_ANIMA_METHODS = (
    "forward_before_blocks",
    "decoder_head",
)

TRANSFORMER_ATTR_PATHS = (
    "diffusion_model",
    "model",
    "net",
    "transformer",
    "transformer_model",
)


@dataclass(frozen=True)
class ModuleListCandidate:
    name: str
    length: int
    score: int
    first_block_class: Optional[str]
    unique_block_classes: List[str]
    forward_signature: Optional[str]


@dataclass(frozen=True)
class TopologyReport:
    model_class: str
    model_module: str
    transformer_path: Optional[str]
    transformer_class: Optional[str]
    transformer_module: Optional[str]
    has_forward_before_blocks: bool
    has_decoder_head: bool
    modulelist_candidates: List[ModuleListCandidate]
    selected_block_container: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _qualified_class_name(obj: object) -> tuple[str, str]:
    cls = obj.__class__
    return cls.__name__, cls.__module__


def _forward_signature(module: nn.Module) -> Optional[str]:
    forward = getattr(module, "forward", None)
    if forward is None:
        return None
    try:
        return str(inspect.signature(forward))
    except (TypeError, ValueError):
        return None


def _candidate_transformer(diffusion_model) -> tuple[Optional[str], object]:
    for path in TRANSFORMER_ATTR_PATHS:
        candidate = _resolve_attr_path(diffusion_model, path)
        if candidate is not None and isinstance(candidate, nn.Module):
            return path, candidate
    return None, diffusion_model


def _modulelist_candidate(name: str, module_list: nn.ModuleList) -> ModuleListCandidate:
    block_classes = [module.__class__.__name__ for module in module_list]
    unique_block_classes = sorted(set(block_classes))
    first_block = module_list[0] if len(module_list) else None
    return ModuleListCandidate(
        name=name,
        length=len(module_list),
        score=_modulelist_score(name, module_list),
        first_block_class=first_block.__class__.__name__ if first_block is not None else None,
        unique_block_classes=unique_block_classes,
        forward_signature=_forward_signature(first_block) if first_block is not None else None,
    )


def discover_topology(diffusion_model) -> TopologyReport:
    model_class, model_module = _qualified_class_name(diffusion_model)
    transformer_path, transformer = _candidate_transformer(diffusion_model)
    transformer_class, transformer_module = _qualified_class_name(transformer)

    candidates = []
    for name, module in transformer.named_modules():
        if isinstance(module, nn.ModuleList):
            candidate = _modulelist_candidate(name, module)
            if candidate.score > -1000:
                candidates.append(candidate)

    if transformer is not diffusion_model:
        for name, module in diffusion_model.named_modules():
            if isinstance(module, nn.ModuleList):
                prefixed_name = name
                if transformer_path and not name.startswith(transformer_path):
                    prefixed_name = name
                candidate = _modulelist_candidate(prefixed_name, module)
                if candidate.score > -1000 and all(existing.name != candidate.name for existing in candidates):
                    candidates.append(candidate)

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    selected = candidates[0].name if candidates else None

    return TopologyReport(
        model_class=model_class,
        model_module=model_module,
        transformer_path=transformer_path,
        transformer_class=transformer_class,
        transformer_module=transformer_module,
        has_forward_before_blocks=hasattr(diffusion_model, "forward_before_blocks")
        or hasattr(transformer, "forward_before_blocks"),
        has_decoder_head=hasattr(diffusion_model, "decoder_head") or hasattr(transformer, "decoder_head"),
        modulelist_candidates=candidates[:10],
        selected_block_container=selected,
    )
