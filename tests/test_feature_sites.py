import torch.nn as nn

from core.feature_sites import (
    FEATURE_SITE_POST_BLOCK,
    FEATURE_SITE_PRE_DECODER_HEAD,
    POST_BLOCK_SITE,
    PRE_DECODER_HEAD_SITE,
    get_feature_site,
)


class UnsupportedModel(nn.Module):
    pass


def test_current_feature_site_id_is_stable():
    assert PRE_DECODER_HEAD_SITE.id == FEATURE_SITE_PRE_DECODER_HEAD
    assert POST_BLOCK_SITE.id == FEATURE_SITE_POST_BLOCK
    assert get_feature_site("missing") is PRE_DECODER_HEAD_SITE


def test_current_feature_site_rejects_unsupported_model():
    assert PRE_DECODER_HEAD_SITE.supports(UnsupportedModel()) is False
