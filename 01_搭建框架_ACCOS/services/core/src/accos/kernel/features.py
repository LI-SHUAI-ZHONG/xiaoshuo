"""Runtime feature switches with secure defaults."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    """Feature switches shared by API and worker composition roots."""

    real_provider_calls_enabled: bool = False
    multimodal_image_enabled: bool = False
    multimodal_audio_enabled: bool = False
    multimodal_video_enabled: bool = False
    multimodal_three_d_enabled: bool = False
    graph_enabled: bool = False
    collaboration_enabled: bool = False
    rights_enabled: bool = False
    marketplace_enabled: bool = False
    reputation_enabled: bool = False
    growth_enabled: bool = False
    knowledge_network_enabled: bool = False

    def extension_values(self) -> dict[str, bool]:
        """Return the public extension switches without exposing environment keys."""
        return {
            "multimodal_image": self.multimodal_image_enabled,
            "multimodal_audio": self.multimodal_audio_enabled,
            "multimodal_video": self.multimodal_video_enabled,
            "multimodal_three_d": self.multimodal_three_d_enabled,
            "graph": self.graph_enabled,
            "collaboration": self.collaboration_enabled,
            "rights": self.rights_enabled,
            "marketplace": self.marketplace_enabled,
            "reputation": self.reputation_enabled,
            "growth": self.growth_enabled,
            "knowledge_network": self.knowledge_network_enabled,
        }
