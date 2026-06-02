import pytest
import torch

from core.replay import parse_block_indices
from core.schedule import (
    estimate_last_step_index,
    estimate_total_steps,
    get_schedule_from_c,
    get_schedule_last_step_index,
    get_schedule_step_count,
    progress_from_schedule,
    should_reset_for_new_pass,
)


def test_parse_block_indices_accepts_ranges_reorders_and_deduplicates():
    assert parse_block_indices("3, 5, 3-5, 8-6", max_block_index=8) == [3, 4, 5, 6, 7, 8]


def test_parse_block_indices_ignores_out_of_range_but_requires_one_valid_index():
    assert parse_block_indices("0,9", max_block_index=3) == [0]
    with pytest.raises(RuntimeError, match="No valid block indices"):
        parse_block_indices("9,10", max_block_index=3)


@pytest.mark.parametrize("text", [None, "", "abc", "1-2-3", "a-b"])
def test_parse_block_indices_rejects_invalid_text(text):
    with pytest.raises(RuntimeError):
        parse_block_indices(text, max_block_index=4)


def test_schedule_helpers_read_sigmas_from_transformer_options():
    sigmas = torch.tensor([10.0, 7.5, 3.0, 0.0])
    c = {"transformer_options": {"sample_sigmas": sigmas}}

    extracted = get_schedule_from_c(c)
    assert torch.equal(extracted, sigmas.float())
    assert get_schedule_step_count(c) == 4
    assert get_schedule_last_step_index(c) == 3
    assert progress_from_schedule(torch.tensor([7.5]), c) == pytest.approx(1 / 3)


def test_schedule_helpers_fallback_when_schedule_is_missing():
    assert get_schedule_from_c({}) is None
    assert get_schedule_step_count({}) is None
    assert get_schedule_last_step_index({}) is None
    assert progress_from_schedule(1.0, {}) is None
    assert estimate_total_steps(current_step=6, c={}, fallback=4) == 7
    assert estimate_last_step_index(1) == 1


def test_should_reset_for_new_pass_detects_timestep_increase():
    assert should_reset_for_new_pass(timestep=10.0, last_timestep=9.0)
    assert not should_reset_for_new_pass(timestep=9.0, last_timestep=10.0)
