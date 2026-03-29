from dataclasses import dataclass
from typing import Callable, List

import torch

from .helpers import clamp01
from .model_introspection import find_best_block_container, restore_all_previous_replay_patches
from .schedule import progress_from_schedule


def parse_block_indices(block_indices_text: str, max_block_index: int) -> List[int]:
    if block_indices_text is None:
        raise RuntimeError("block_indices cannot be empty.")

    text = str(block_indices_text).strip()
    if not text:
        raise RuntimeError("block_indices cannot be empty.")

    result = set()
    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue

        if "-" in part:
            pieces = [piece.strip() for piece in part.split("-") if piece.strip()]
            if len(pieces) != 2:
                raise RuntimeError(
                    f"Invalid block range '{part}'. Use formats like '3-5' or '3,4,5,8'."
                )
            try:
                start = int(pieces[0])
                end = int(pieces[1])
            except ValueError as exc:
                raise RuntimeError(
                    f"Invalid block range '{part}'. Use integers like '3-5'."
                ) from exc

            if end < start:
                start, end = end, start

            for index in range(start, end + 1):
                if 0 <= index <= max_block_index:
                    result.add(index)
            continue

        try:
            index = int(part)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid block index '{part}'. Use integers like '3' or ranges like '3-5'."
            ) from exc

        if 0 <= index <= max_block_index:
            result.add(index)

    parsed = sorted(result)
    if not parsed:
        raise RuntimeError(
            f"No valid block indices found in '{block_indices_text}'. Valid range is 0 to {max_block_index}."
        )

    return parsed


@dataclass(frozen=True)
class ReplayConfig:
    enabled: bool
    block_indices_text: str
    denoise_start_pct: float
    denoise_end_pct: float


class ReplayController:
    def __init__(self, diffusion_model, config: ReplayConfig):
        restore_all_previous_replay_patches(diffusion_model)

        _, block_list, summary = find_best_block_container(diffusion_model)
        self.block_list = block_list
        self.block_summary = summary

        max_block_index = len(block_list) - 1
        self.selected_indices = parse_block_indices(config.block_indices_text, max_block_index)
        self.enabled = bool(config.enabled)

        denoise_start = clamp01(config.denoise_start_pct)
        denoise_end = clamp01(config.denoise_end_pct)
        if denoise_end < denoise_start:
            denoise_start, denoise_end = denoise_end, denoise_start
        self.denoise_start = denoise_start
        self.denoise_end = denoise_end

        self._warned_non_tensor = False
        self._warned_replay_error = False

    def is_active(self, timestep, c: dict) -> bool:
        if not self.enabled:
            return False

        progress = progress_from_schedule(timestep, c)
        if progress is None:
            return True
        return self.denoise_start <= progress <= self.denoise_end

    def _make_replay_forward(self, original_forward, block_index: int):
        def replay_forward(module, *args, **kwargs):
            out = original_forward(*args, **kwargs)

            if not torch.is_tensor(out):
                if not self._warned_non_tensor:
                    print(
                        f"[AnimaReplay] Block {block_index} returned non-tensor output "
                        f"({type(out)}). Falling back to original output for this block."
                    )
                    self._warned_non_tensor = True
                return out

            try:
                return original_forward(out, *args[1:], **kwargs)
            except Exception as exc:
                if not self._warned_replay_error:
                    print(
                        f"[AnimaReplay] Replay failed on block {block_index} "
                        f"with {type(exc).__name__}: {exc}. Falling back to original output."
                    )
                    self._warned_replay_error = True
                return out

        return replay_forward

    def run(self, runner: Callable[[], torch.Tensor], replay_active: bool):
        if not replay_active:
            return runner()

        patched_blocks = []
        original_forwards = []

        try:
            for index in self.selected_indices:
                block = self.block_list[index]
                original_forward = block.forward

                original_forwards.append(original_forward)
                patched_blocks.append(block)

                replay_forward = self._make_replay_forward(original_forward, index)
                block.forward = replay_forward.__get__(block, block.__class__)
                block._anima_replay_patched = True
                block._anima_replay_original_forward = original_forward

            return runner()
        finally:
            for block, original_forward in zip(patched_blocks, original_forwards):
                block.forward = original_forward
                if hasattr(block, "_anima_replay_patched"):
                    delattr(block, "_anima_replay_patched")
                if hasattr(block, "_anima_replay_original_forward"):
                    delattr(block, "_anima_replay_original_forward")
