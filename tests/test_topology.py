import torch
import torch.nn as nn

from core.topology import discover_topology


class TinyBlock(nn.Module):
    def forward(self, x, timestep=None, context=None):
        return x


class TinyAnimaModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.blocks = nn.ModuleList([TinyBlock() for _ in range(4)])
        self.norm_layers = nn.ModuleList([nn.LayerNorm(2) for _ in range(4)])

    def forward_before_blocks(self, x, timestep, context):
        return x

    def decoder_head(self, x):
        return x


class WrappedModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.transformer = TinyAnimaModel()


def test_discover_topology_reports_model_identity_and_known_methods():
    report = discover_topology(TinyAnimaModel())

    assert report.model_class == "TinyAnimaModel"
    assert report.model_module == __name__
    assert report.transformer_path is None
    assert report.transformer_class == "TinyAnimaModel"
    assert report.has_forward_before_blocks is True
    assert report.has_decoder_head is True


def test_discover_topology_ranks_block_container_above_norm_layers():
    report = discover_topology(TinyAnimaModel())

    assert report.selected_block_container == "blocks"
    assert [candidate.name for candidate in report.modulelist_candidates][:2] == ["blocks", "norm_layers"]
    block_candidate = report.modulelist_candidates[0]
    assert block_candidate.length == 4
    assert block_candidate.first_block_class == "TinyBlock"
    assert block_candidate.unique_block_classes == ["TinyBlock"]
    assert "(x, timestep=None, context=None)" in block_candidate.forward_signature


def test_discover_topology_detects_nested_transformer_object():
    report = discover_topology(WrappedModel())

    assert report.model_class == "WrappedModel"
    assert report.transformer_path == "transformer"
    assert report.transformer_class == "TinyAnimaModel"
    assert report.selected_block_container == "transformer.blocks"


def test_topology_report_is_json_serializable():
    report = discover_topology(TinyAnimaModel()).to_dict()

    assert report["model_class"] == "TinyAnimaModel"
    assert report["modulelist_candidates"][0]["name"] == "blocks"


def test_discover_topology_handles_models_without_modulelists():
    report = discover_topology(nn.Linear(2, 2))

    assert report.model_class == "Linear"
    assert report.modulelist_candidates == []
    assert report.selected_block_container is None
