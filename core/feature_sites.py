from dataclasses import dataclass
from typing import Callable

from .intermediate_features import detect_intermediate_feature_support


FEATURE_SITE_PRE_DECODER_HEAD = "pre_decoder_head"
FEATURE_SITE_POST_BLOCK = "post_block"


@dataclass(frozen=True)
class FeatureSite:
    id: str
    description: str
    supports: Callable[[object], bool]


def supports_pre_decoder_head(diffusion_model) -> bool:
    return detect_intermediate_feature_support(diffusion_model) is not None


PRE_DECODER_HEAD_SITE = FeatureSite(
    id=FEATURE_SITE_PRE_DECODER_HEAD,
    description="Existing Phase 2 site that forecasts the repeated block output before decoder_head/final_layer.",
    supports=supports_pre_decoder_head,
)

POST_BLOCK_SITE = FeatureSite(
    id=FEATURE_SITE_POST_BLOCK,
    description="Diagnostic site that forecasts the feature state after a selected repeated block.",
    supports=supports_pre_decoder_head,
)

AVAILABLE_FEATURE_SITES = {
    PRE_DECODER_HEAD_SITE.id: PRE_DECODER_HEAD_SITE,
    POST_BLOCK_SITE.id: POST_BLOCK_SITE,
}


def get_feature_site(site_id: str = FEATURE_SITE_PRE_DECODER_HEAD) -> FeatureSite:
    return AVAILABLE_FEATURE_SITES.get(site_id, PRE_DECODER_HEAD_SITE)
