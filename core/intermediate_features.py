from dataclasses import dataclass, replace
from typing import Any, Iterable, Optional

import torch
import torch.nn as nn


_COMMON_MODEL_ATTRS = (
    "model",
    "net",
    "inner_model",
    "diffusion_model",
    "unet",
)

_COMMON_BLOCK_PATHS = (
    "blocks",
    "net.blocks",
    "model.blocks",
)


@dataclass(frozen=True)
class IntermediateFeatureSupport:
    model_type: str
    block_count: int
    block_container_name: str
    resolved_model_path: str
    api_variant: str


@dataclass(frozen=True)
class IntermediateFeatureState:
    x: torch.Tensor
    affline_emb_B_D: torch.Tensor
    crossattn_emb: torch.Tensor
    crossattn_mask: Optional[torch.Tensor]
    rope_emb_L_1_1_D: Optional[torch.Tensor]
    adaln_lora_B_3D: Optional[torch.Tensor]
    original_shape: Any
    extra_pos_emb_B_T_H_W_D_or_T_H_W_B_D: Optional[torch.Tensor]


class UnsupportedIntermediateFeatureModel(RuntimeError):
    pass


def _resolve_attr_path(obj, path: str):
    current = obj
    if not path:
        return current
    for part in path.split("."):
        if not hasattr(current, part):
            return None
        current = getattr(current, part)
    return current


def _iter_candidate_models(root_model) -> Iterable[tuple[str, Any]]:
    queue = [("", root_model)]
    visited = set()

    while queue:
        path, candidate = queue.pop(0)
        if candidate is None:
            continue
        marker = id(candidate)
        if marker in visited:
            continue
        visited.add(marker)
        yield path, candidate

        for attr in _COMMON_MODEL_ATTRS:
            if hasattr(candidate, attr):
                child = getattr(candidate, attr)
                if child is not None:
                    child_path = f"{path}.{attr}" if path else attr
                    queue.append((child_path, child))


def _find_block_container(candidate) -> tuple[str, Any]:
    for block_path in _COMMON_BLOCK_PATHS:
        blocks = _resolve_attr_path(candidate, block_path)
        if isinstance(blocks, (nn.ModuleList, nn.ModuleDict)) and len(blocks) >= 1:
            return block_path, blocks
    raise UnsupportedIntermediateFeatureModel(
        "Phase 2 intermediate-feature path requires a repeated block container."
    )


def _detect_api_variant(candidate) -> Optional[str]:
    if hasattr(candidate, "forward_before_blocks") and hasattr(candidate, "decoder_head"):
        return "cosmos_forward_before_blocks"

    predict2_attrs = (
        "prepare_embedded_sequence",
        "t_embedder",
        "t_embedding_norm",
        "final_layer",
        "unpatchify",
    )
    if all(hasattr(candidate, attr) for attr in predict2_attrs):
        return "predict2_minidit"

    return None


def resolve_intermediate_feature_model(diffusion_model) -> tuple[Any, IntermediateFeatureSupport]:
    for model_path, candidate in _iter_candidate_models(diffusion_model):
        api_variant = _detect_api_variant(candidate)
        if api_variant is None:
            continue

        try:
            block_container_name, blocks = _find_block_container(candidate)
        except UnsupportedIntermediateFeatureModel:
            continue

        return candidate, IntermediateFeatureSupport(
            model_type=candidate.__class__.__name__,
            block_count=len(blocks),
            block_container_name=block_container_name,
            resolved_model_path=model_path or "<root>",
            api_variant=api_variant,
        )

    raise UnsupportedIntermediateFeatureModel(
        "Phase 2 intermediate-feature path currently supports Anima-style diffusion models "
        "with either forward_before_blocks()/decoder_head() or MiniTrainDIT-style "
        "prepare_embedded_sequence()/final_layer()/unpatchify() APIs."
    )


def detect_intermediate_feature_support(diffusion_model) -> Optional[IntermediateFeatureSupport]:
    try:
        _, support = resolve_intermediate_feature_model(diffusion_model)
    except UnsupportedIntermediateFeatureModel:
        return None
    return support


def require_intermediate_feature_support(diffusion_model) -> IntermediateFeatureSupport:
    _, support = resolve_intermediate_feature_model(diffusion_model)
    return support


def _iter_blocks(diffusion_model) -> Iterable[nn.Module]:
    target_model, support = resolve_intermediate_feature_model(diffusion_model)
    blocks = _resolve_attr_path(target_model, support.block_container_name)
    if isinstance(blocks, nn.ModuleList):
        return list(blocks)
    if isinstance(blocks, nn.ModuleDict):
        return list(blocks.values())
    raise UnsupportedIntermediateFeatureModel(
        f"Unsupported block container type for Phase 2 path: {type(blocks).__name__}."
    )


def batch_size_from_intermediate_feature_state(state: IntermediateFeatureState) -> int:
    return int(state.x.shape[0])


def _slice_batch_value(value: Any, index_tensor: torch.Tensor, batch_size: int) -> Any:
    if torch.is_tensor(value) and value.dim() > 0 and value.shape[0] == batch_size:
        return value[index_tensor.to(value.device)]
    return value


def _slice_original_shape(original_shape: Any, sliced_batch_size: int, batch_size: int) -> Any:
    if isinstance(original_shape, tuple) and len(original_shape) >= 1 and original_shape[0] == batch_size:
        return (sliced_batch_size, *original_shape[1:])
    if isinstance(original_shape, list) and len(original_shape) >= 1 and original_shape[0] == batch_size:
        new_shape = original_shape.copy()
        new_shape[0] = sliced_batch_size
        return new_shape
    return original_shape


def slice_intermediate_feature_state(
    state: IntermediateFeatureState,
    index_tensor: torch.Tensor,
) -> IntermediateFeatureState:
    batch_size = batch_size_from_intermediate_feature_state(state)
    sliced_batch_size = int(index_tensor.numel())
    return IntermediateFeatureState(
        x=_slice_batch_value(state.x, index_tensor, batch_size),
        affline_emb_B_D=_slice_batch_value(state.affline_emb_B_D, index_tensor, batch_size),
        crossattn_emb=_slice_batch_value(state.crossattn_emb, index_tensor, batch_size),
        crossattn_mask=_slice_batch_value(state.crossattn_mask, index_tensor, batch_size),
        rope_emb_L_1_1_D=_slice_batch_value(state.rope_emb_L_1_1_D, index_tensor, batch_size),
        adaln_lora_B_3D=_slice_batch_value(state.adaln_lora_B_3D, index_tensor, batch_size),
        original_shape=_slice_original_shape(state.original_shape, sliced_batch_size, batch_size),
        extra_pos_emb_B_T_H_W_D_or_T_H_W_B_D=_slice_batch_value(
            state.extra_pos_emb_B_T_H_W_D_or_T_H_W_B_D,
            index_tensor,
            batch_size,
        ),
    )


def replace_intermediate_feature_x(
    state: IntermediateFeatureState,
    x: torch.Tensor,
) -> IntermediateFeatureState:
    return replace(state, x=x)


def _extract_cosmos_style_state(
    target_model,
    x: torch.Tensor,
    timesteps: torch.Tensor,
    context: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
    fps: Optional[torch.Tensor] = None,
    image_size: Optional[torch.Tensor] = None,
    padding_mask: Optional[torch.Tensor] = None,
    scalar_feature: Optional[torch.Tensor] = None,
    data_type: Any = None,
    latent_condition: Optional[torch.Tensor] = None,
    latent_condition_sigma: Optional[torch.Tensor] = None,
    condition_video_augment_sigma: Optional[torch.Tensor] = None,
    **kwargs,
) -> IntermediateFeatureState:
    before_blocks_kwargs = dict(
        x=x,
        timesteps=timesteps,
        crossattn_emb=context,
        crossattn_mask=attention_mask,
        fps=fps,
        image_size=image_size,
        padding_mask=padding_mask,
        scalar_feature=scalar_feature,
        latent_condition=latent_condition,
        latent_condition_sigma=latent_condition_sigma,
        condition_video_augment_sigma=condition_video_augment_sigma,
        **kwargs,
    )
    if data_type is not None:
        before_blocks_kwargs["data_type"] = data_type

    inputs = target_model.forward_before_blocks(**before_blocks_kwargs)
    return IntermediateFeatureState(
        x=inputs["x"],
        affline_emb_B_D=inputs["affline_emb_B_D"],
        crossattn_emb=inputs["crossattn_emb"],
        crossattn_mask=inputs["crossattn_mask"],
        rope_emb_L_1_1_D=inputs["rope_emb_L_1_1_D"],
        adaln_lora_B_3D=inputs["adaln_lora_B_3D"],
        original_shape=inputs["original_shape"],
        extra_pos_emb_B_T_H_W_D_or_T_H_W_B_D=inputs["extra_pos_emb_B_T_H_W_D_or_T_H_W_B_D"],
    )


def _extract_predict2_style_state(
    target_model,
    x: torch.Tensor,
    timesteps: torch.Tensor,
    context: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
    fps: Optional[torch.Tensor] = None,
    padding_mask: Optional[torch.Tensor] = None,
    **kwargs,
) -> IntermediateFeatureState:
    del attention_mask, kwargs
    try:
        import comfy.ldm.common_dit
    except ImportError as exc:
        raise UnsupportedIntermediateFeatureModel(
            "Phase 2 predict2/Anima path requires comfy.ldm.common_dit."
        ) from exc

    original_shape = list(x.shape)
    x = comfy.ldm.common_dit.pad_to_patch_size(
        x,
        (target_model.patch_temporal, target_model.patch_spatial, target_model.patch_spatial),
    )
    x_B_T_H_W_D, rope_emb_L_1_1_D, extra_pos_emb = target_model.prepare_embedded_sequence(
        x,
        fps=fps,
        padding_mask=padding_mask,
    )

    timesteps_B_T = timesteps
    if timesteps_B_T.ndim == 1:
        timesteps_B_T = timesteps_B_T.unsqueeze(1)
    affline_emb_B_D, adaln_lora_B_3D = target_model.t_embedder[1](
        target_model.t_embedder[0](timesteps_B_T).to(x_B_T_H_W_D.dtype)
    )
    affline_emb_B_D = target_model.t_embedding_norm(affline_emb_B_D)

    if x_B_T_H_W_D.dtype == torch.float16:
        x_B_T_H_W_D = x_B_T_H_W_D.float()

    if rope_emb_L_1_1_D is not None:
        rope_emb_L_1_1_D = rope_emb_L_1_1_D.unsqueeze(1).unsqueeze(0)

    return IntermediateFeatureState(
        x=x_B_T_H_W_D,
        affline_emb_B_D=affline_emb_B_D,
        crossattn_emb=context,
        crossattn_mask=None,
        rope_emb_L_1_1_D=rope_emb_L_1_1_D,
        adaln_lora_B_3D=adaln_lora_B_3D,
        original_shape=original_shape,
        extra_pos_emb_B_T_H_W_D_or_T_H_W_B_D=extra_pos_emb,
    )


def extract_intermediate_feature_state(
    diffusion_model,
    x: torch.Tensor,
    timesteps: torch.Tensor,
    context: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
    fps: Optional[torch.Tensor] = None,
    image_size: Optional[torch.Tensor] = None,
    padding_mask: Optional[torch.Tensor] = None,
    scalar_feature: Optional[torch.Tensor] = None,
    data_type: Any = None,
    latent_condition: Optional[torch.Tensor] = None,
    latent_condition_sigma: Optional[torch.Tensor] = None,
    condition_video_augment_sigma: Optional[torch.Tensor] = None,
    **kwargs,
) -> IntermediateFeatureState:
    target_model, support = resolve_intermediate_feature_model(diffusion_model)

    if support.api_variant == "cosmos_forward_before_blocks":
        return _extract_cosmos_style_state(
            target_model,
            x=x,
            timesteps=timesteps,
            context=context,
            attention_mask=attention_mask,
            fps=fps,
            image_size=image_size,
            padding_mask=padding_mask,
            scalar_feature=scalar_feature,
            data_type=data_type,
            latent_condition=latent_condition,
            latent_condition_sigma=latent_condition_sigma,
            condition_video_augment_sigma=condition_video_augment_sigma,
            **kwargs,
        )

    if support.api_variant == "predict2_minidit":
        return _extract_predict2_style_state(
            target_model,
            x=x,
            timesteps=timesteps,
            context=context,
            attention_mask=attention_mask,
            fps=fps,
            padding_mask=padding_mask,
            **kwargs,
        )

    raise UnsupportedIntermediateFeatureModel(
        f"Unknown Phase 2 API variant: {support.api_variant}."
    )


def run_blocks_from_intermediate_state(
    diffusion_model,
    state: IntermediateFeatureState,
    start_block: int = 0,
    end_block: Optional[int] = None,
    transformer_options: Optional[dict] = None,
) -> IntermediateFeatureState:
    target_model, support = resolve_intermediate_feature_model(diffusion_model)
    blocks = list(_iter_blocks(diffusion_model))
    total_blocks = len(blocks)
    stop = total_blocks if end_block is None else min(int(end_block), total_blocks)
    start = max(0, int(start_block))
    if stop < start:
        stop = start

    x = state.x
    extra_pos = state.extra_pos_emb_B_T_H_W_D_or_T_H_W_B_D
    if extra_pos is not None:
        extra_pos = extra_pos.to(x.dtype)

    if support.api_variant == "cosmos_forward_before_blocks":
        block_kwargs = {
            "crossattn_mask": state.crossattn_mask,
            "rope_emb_L_1_1_D": state.rope_emb_L_1_1_D,
            "adaln_lora_B_3D": state.adaln_lora_B_3D,
            "extra_per_block_pos_emb": extra_pos,
            "transformer_options": transformer_options or {},
        }
    elif support.api_variant == "predict2_minidit":
        block_kwargs = {
            "rope_emb_L_1_1_D": state.rope_emb_L_1_1_D,
            "adaln_lora_B_T_3D": state.adaln_lora_B_3D,
            "extra_per_block_pos_emb": extra_pos,
            "transformer_options": transformer_options or {},
        }
    else:
        raise UnsupportedIntermediateFeatureModel(
            f"Unknown Phase 2 API variant: {support.api_variant}."
        )

    for block in blocks[start:stop]:
        x = block(
            x,
            state.affline_emb_B_D,
            state.crossattn_emb,
            **block_kwargs,
        )

    return replace(state, x=x)

def decode_intermediate_feature_state(diffusion_model, state: IntermediateFeatureState) -> torch.Tensor:
    target_model, support = resolve_intermediate_feature_model(diffusion_model)

    if support.api_variant == "cosmos_forward_before_blocks":
        return target_model.decoder_head(
            x_B_T_H_W_D=state.x,
            emb_B_D=state.affline_emb_B_D,
            crossattn_emb=state.crossattn_emb,
            origin_shape=state.original_shape,
            crossattn_mask=state.crossattn_mask,
            adaln_lora_B_3D=state.adaln_lora_B_3D,
        )

    if support.api_variant == "predict2_minidit":
        x_B_T_H_W_O = target_model.final_layer(
            state.x.to(state.crossattn_emb.dtype),
            state.affline_emb_B_D,
            adaln_lora_B_T_3D=state.adaln_lora_B_3D,
        )
        return target_model.unpatchify(x_B_T_H_W_O)[
            :,
            :,
            : state.original_shape[-3],
            : state.original_shape[-2],
            : state.original_shape[-1],
        ]

    raise UnsupportedIntermediateFeatureModel(
        f"Unknown Phase 2 API variant: {support.api_variant}."
    )


def run_full_intermediate_path(
    diffusion_model,
    state: IntermediateFeatureState,
    transformer_options: Optional[dict] = None,
) -> torch.Tensor:
    final_state = run_blocks_from_intermediate_state(
        diffusion_model,
        state,
        start_block=0,
        end_block=None,
        transformer_options=transformer_options,
    )
    return decode_intermediate_feature_state(diffusion_model, final_state)



