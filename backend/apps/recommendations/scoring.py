from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreBreakdown:
    gap_coverage: float
    criticality: float
    achievable_gain: float
    history_affinity: float
    availability: float
    skip_penalty: float
    repeat_penalty: float

    @property
    def total(self) -> float:
        score = (
            0.40 * self.gap_coverage
            + 0.20 * self.criticality
            + 0.15 * self.achievable_gain
            + 0.15 * self.history_affinity
            + 0.10 * self.availability
            - self.skip_penalty
            - self.repeat_penalty
        )
        return round(max(0.0, min(score, 1.0)), 5)
