"""
MIRAS/MIDAS-style replay + pattern memory core.

This module is intentionally domain-agnostic.

It assumes only that:

  - An Episode has:
      * a timestamp,
      * a context dict (what was known),
      * an action dict (what was done),
      * an outcome dict with at least a scalar "reward",
        and optionally a "model_reward" for comparison.
  - A policy/conviction model can score a context in [0,1].
  - An outcome model can simulate or estimate a model_reward.
  - An optional utility engine can attach expected utility (EV).

It provides:

  - Episode / EvaluationResult data models.
  - Protocols for:
      * ConvictionModel      (policy scoring / gating),
      * OutcomeModel         (counterfactual or simulated outcome),
      * UtilityEngine        (expected utility / EV),
      * MetricsSink          (aggregation / logging),
      * MemoryHook           (MIRAS/MIDAS integration).
  - ReplayHarness:
      * replays chronologically ordered episodes,
      * evaluates policy vs actual outcome,
      * optionally attaches expected utility,
      * notifies metrics + memory.
  - PatternMemoryHook:
      * groups episodes into patterns (configurable),
      * maintains per-pattern rolling stats,
      * assigns each pattern a memory_strength in [0,1],
      * applies sample-size shrinkage,
      * exposes a pattern_gate(...) → (decision, weight, reason).

Numeric thresholds are conservative defaults and meant to be tuned
per project and reward scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple, Callable

import math


# -------------------------------------------------------------------
# Core data structures
# -------------------------------------------------------------------

@dataclass
class Episode:
    """
    A single decision episode.

    Attributes:
      id        : unique identifier.
      timestamp : when the decision/context actually occurred.
      context   : information available at decision time.
      action    : chosen action / decision.
      outcome   : realized result; should at least contain a scalar
                  "reward" (float) and optionally "model_reward".
      meta      : free-form metadata (flags, pattern tags, etc.).
    """
    id: str
    timestamp: datetime
    context: Dict[str, Any]
    action: Dict[str, Any]
    outcome: Dict[str, Any]
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """
    Evaluation of one episode by a model/agent.

    All fields are intentionally generic: "reward" may represent
    loss, score, utility, etc.
    """
    episode_id: str

    actual_reward: float
    model_reward: float
    performance_gap: float  # model_reward - actual_reward

    # Conviction / policy score (0..1) and gating decision.
    conviction: float
    decision_allowed: bool
    mode: str

    # Optional expected-utility fields if a UtilityEngine is attached.
    ev_value: Optional[float] = None       # expected utility (normalized)
    ev_pass: Optional[bool] = None         # above/below some EV floor
    ev_p_success: Optional[float] = None   # estimated success probability

    # Arbitrary extra/debug info.
    extra: Dict[str, Any] = field(default_factory=dict)


# -------------------------------------------------------------------
# Protocols (interfaces)
# -------------------------------------------------------------------

class ConvictionModel(Protocol):
    """
    Policy/conviction scoring used by the replay harness.
    """

    def evaluate_conviction(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a dict with at least:
          - 'score'         : float in [0, 1]
          - 'mode'          : str (e.g. 'STANDARD', 'AGGRESSIVE', 'SAFE')
          - 'threshold_pass': bool (whether this episode would be acted on)
        """
        ...


class OutcomeModel(Protocol):
    """
    Outcome modeling interface.

    Implementations can be:
      - simulators,
      - counterfactual models,
      - or any mapping from an Episode to a scalar model_reward.
    """

    def simulate_outcome(self, episode: Episode) -> Dict[str, Any]:
        """
        Returns a dict with at least:
          - 'model_reward': float
          - 'reason'      : str (brief explanation / tag)
        """
        ...


class UtilityEngine(Protocol):
    """
    Expected utility / EV engine.

    The concrete implementation is domain-specific; the harness only
    assumes that it maps (Episode, EvaluationResult) to an expected
    scalar utility and optionally a success probability.
    """

    def compute_utility(
        self,
        episode: Episode,
        evaluation: EvaluationResult,
    ) -> Dict[str, Any]:
        """
        Returns a dict with at least:
          - 'ev_value'  : float (expected utility, normalized)
          - 'pass'      : bool  (above/below a utility floor)
          - 'p_success' : float (0..1 success probability)

        Additional keys are allowed and may be attached to EvaluationResult.extra.
        """
        ...


class MetricsSink(Protocol):
    """
    Receives EvaluationResult objects for aggregation / logging.
    """

    def on_evaluation(self, evaluation: EvaluationResult, episode: Episode) -> None:
        ...


class MemoryHook(Protocol):
    """
    Hook for a MIRAS/MIDAS-style memory system.

    A hierarchical memory module can use this to:
      - observe episodes and evaluations from replay,
      - update retention / attention / promotion based on EV and stability.
    """

    def on_episode_evaluated(self, episode: Episode, evaluation: EvaluationResult) -> None:
        ...


# -------------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------------

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _sigmoid(x: float) -> float:
    """Simple sigmoid used for mapping utility into [0,1]."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _is_finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


# -------------------------------------------------------------------
# Replay Harness
# -------------------------------------------------------------------

@dataclass
class ReplayHarness:
    """
    Generic replay harness for decision agents.

    Recommended usage:

        episodes = load_or_build_episodes(...)
        episodes.sort(key=lambda ep: ep.timestamp)   # anti-lookahead
        # optional: deduplicate episodes by (task, time, action, ...)
        harness.run(episodes)

    This ensures chronological ordering and avoids memory
    "learning from the future".
    """

    conviction_model: ConvictionModel
    outcome_model: OutcomeModel
    metrics_sink: MetricsSink
    memory_hook: Optional[MemoryHook] = None
    utility_engine: Optional[UtilityEngine] = None

    def run(self, episodes: Iterable[Episode]) -> List[EvaluationResult]:
        results: List[EvaluationResult] = []

        for ep in episodes:
            ctx     = ep.context
            outcome = ep.outcome

            actual_reward = _safe_float(outcome.get("reward"), default=0.0)

            # 1) Conviction / policy score.
            conv = self.conviction_model.evaluate_conviction(ctx)
            conv_score    = float(conv.get("score", 0.0))
            conv_mode     = str(conv.get("mode", "UNSPECIFIED"))
            decision_ok   = bool(conv.get("threshold_pass", False))

            # 2) Outcome simulation / model comparison.
            sim = self.outcome_model.simulate_outcome(ep)
            model_reward = _safe_float(sim.get("model_reward"), default=0.0)
            reason       = str(sim.get("reason", "unknown"))

            performance_gap = model_reward - actual_reward

            evaluation = EvaluationResult(
                episode_id        = ep.id,
                actual_reward     = actual_reward,
                model_reward      = model_reward,
                performance_gap   = performance_gap,
                conviction        = conv_score,
                decision_allowed  = decision_ok,
                mode              = conv_mode,
                extra             = {
                    "raw_conviction": conv,
                    "raw_outcome_sim": sim,
                    "outcome_reason": reason,
                },
            )

            # 3) Optional expected-utility computation.
            if self.utility_engine is not None:
                u = self.utility_engine.compute_utility(ep, evaluation)

                evaluation.ev_value      = _safe_float(u.get("ev_value"), default=0.0)
                evaluation.ev_pass       = bool(u.get("pass")) if "pass" in u else None
                evaluation.ev_p_success  = _safe_float(u.get("p_success"), default=0.0)

                extra_u = {
                    k: v for k, v in u.items()
                    if k not in ("ev_value", "pass", "p_success")
                }
                if extra_u:
                    evaluation.extra.setdefault("utility", {}).update(extra_u)

            # 4) Metrics sink.
            self.metrics_sink.on_evaluation(evaluation, ep)

            # 5) Memory hook (MIRAS/MIDAS).
            if self.memory_hook is not None:
                self.memory_hook.on_episode_evaluated(ep, evaluation)

            results.append(evaluation)

        return results


# -------------------------------------------------------------------
# Pattern-level memory (MIRAS/MIDAS-style)
# -------------------------------------------------------------------

@dataclass
class PatternStats:
    """
    Per-pattern statistics used by the memory system.

    Fields:
      count           : number of episodes seen for this pattern.
      memory_strength : learned retention/attention weight in [0,1].
      rolling_ev      : EMA of expected utility (ev_value).
      rolling_gap     : EMA of performance_gap (model − actual).
      last_seen       : last timestamp observed.
    """
    count: int = 0
    memory_strength: float = 0.0
    rolling_ev: float = 0.0
    rolling_gap: float = 0.0
    last_seen: Optional[datetime] = None


def default_pattern_id_fn(ep: Episode, ev: EvaluationResult) -> str:
    """
    Default way to group episodes into patterns.

    For richer systems, callers can pass a custom function that hashes
    whatever dimensions they care about (agent, task, regime, etc.).
    """
    agent = ep.context.get("agent", "?")
    task  = ep.context.get("task", "?")
    mode  = ev.mode
    return f"{agent}::{task}::{mode}"


@dataclass
class PatternMemoryHook(MemoryHook):
    """
    MIDAS-style memory hook that maintains pattern-level memory_strength.

    It uses:
      - expected utility (ev_value) when available,
      - performance_gap (model vs actual),
      - sample-size shrinkage,
      - recency,

    to maintain for each pattern:
      - an effective memory_strength in [0,1],
      - rolling statistics for ev and gap,
      - a gating function that yields (decision, weight, reason).

    The numeric thresholds here are conservative defaults and should
    be tuned for each project’s reward scale and tolerance for risk.
    """

    # Learning / smoothing hyperparameters.
    lr: float = 0.15                 # learning rate toward target strength
    ema_alpha: float = 0.2           # EMA factor for rolling_ev / rolling_gap

    # Shrinkage: how many episodes until we fully trust memory_strength.
    shrinkage_n: int = 30

    # Gating thresholds (tune per application).
    gate_min_count: int = 20
    gate_max_recency_days: int = 30
    gate_min_effective_strength: float = 0.55
    gate_min_rolling_ev: float = 0.15
    gate_max_abs_gap: float = 12.5

    # Gap-based risk control.
    gap_skip_threshold: float = 30.0   # skip update if |gap| > this (units: reward scale)
    gap_halve_threshold: float = 10.0  # halve weight if |rolling_gap| > this

    # Pattern id function.
    pattern_id_fn: Callable[[Episode, EvaluationResult], str] = default_pattern_id_fn

    # Internal storage.
    pattern_stats: Dict[str, PatternStats] = field(default_factory=dict)

    def _valid_eval(self, evaluation: EvaluationResult) -> bool:
        """
        Hard gate: only update memory on valid evaluations.

        Prevents NaNs / None / extreme gaps from poisoning memory.
        """
        if evaluation.ev_value is None or not _is_finite(evaluation.ev_value):
            return False
        if not _is_finite(evaluation.performance_gap):
            return False
        if abs(evaluation.performance_gap) > self.gap_skip_threshold:
            return False
        return True

    def on_episode_evaluated(self, episode: Episode, evaluation: EvaluationResult) -> None:
        # Only update memory on valid evaluations (no "None laundering").
        if not self._valid_eval(evaluation):
            episode.meta.setdefault("pattern_memory_skip", []).append("invalid_eval")
            return

        pattern_id = self.pattern_id_fn(episode, evaluation)
        stats = self.pattern_stats.get(pattern_id)
        if stats is None:
            stats = PatternStats()
            self.pattern_stats[pattern_id] = stats

        stats.count += 1
        stats.last_seen = episode.timestamp

        # Signals.
        ev_value = evaluation.ev_value if evaluation.ev_value is not None else 0.0
        gap = evaluation.performance_gap

        # EMAs for robustness.
        a = self.ema_alpha
        stats.rolling_ev = (1 - a) * stats.rolling_ev + a * ev_value
        stats.rolling_gap = (1 - a) * stats.rolling_gap + a * gap

        # Base target strength (utility + stability).
        # Map EV into [0,1] via sigmoid, then subtract a penalty for instability.
        base = _sigmoid(ev_value)   # assumes ev_value is roughly normalized
        gap_norm = abs(gap) / 100.0  # treat as "percentage-like" scale by default
        stability_penalty = 0.5 * gap_norm
        target_strength = _clamp(base - stability_penalty, 0.0, 1.0)

        # Update memory_strength toward target.
        stats.memory_strength = (
            (1.0 - self.lr) * stats.memory_strength
            + self.lr * target_strength
        )

        # Attach metadata for downstream consumers.
        episode.meta.setdefault("pattern_id", pattern_id)
        episode.meta.setdefault("pattern_memory", {})
        episode.meta["pattern_memory"].update(
            {
                "memory_strength": stats.memory_strength,
                "rolling_ev": stats.rolling_ev,
                "rolling_gap": stats.rolling_gap,
            }
        )

    # ------------------------------------------------------------------
    # Pattern gate & sample-size shrinkage
    # ------------------------------------------------------------------

    def compute_effective_strength(self, stats: PatternStats) -> float:
        """
        Apply sample-size shrinkage to memory_strength.

        Small-sample patterns are forced back toward neutral (0.5),
        gradually trusting learned strength only as n approaches shrinkage_n.
        """
        if stats.count <= 0:
            return 0.5

        w = min(1.0, stats.count / float(self.shrinkage_n))
        return 0.5 * (1.0 - w) + stats.memory_strength * w

    def pattern_gate(self, pattern_id: str, now: Optional[datetime] = None) -> Tuple[str, float, str]:
        """
        Decide whether a pattern is usable and at what weight.

        Returns:
          (decision, weight_mult, reason)

        decision:
          - "ALLOW" or "BLOCK"
        weight_mult:
          - in [0,1], can be used as a scaling factor for allocation/attention.
        reason:
          - human-readable explanation tag.

        NOTE: this uses naive datetimes. If your project uses timezone-aware
        datetimes, adapt the recency calculation accordingly.
        """
        stats = self.pattern_stats.get(pattern_id)
        if stats is None or stats.last_seen is None:
            return ("BLOCK", 0.0, "no_stats")

        now = now or datetime.utcnow()
        recency_days = (now - stats.last_seen).days

        effective_strength = self.compute_effective_strength(stats)
        rolling_ev = stats.rolling_ev
        abs_gap = abs(stats.rolling_gap)

        # Hard gates.
        if stats.count < self.gate_min_count:
            return ("BLOCK", 0.0, "low_n")
        if recency_days > self.gate_max_recency_days:
            return ("BLOCK", 0.0, "stale")
        if effective_strength < self.gate_min_effective_strength:
            return ("BLOCK", 0.0, "low_strength")
        if rolling_ev < self.gate_min_rolling_ev:
            return ("BLOCK", 0.0, "low_ev")
        if abs_gap > self.gate_max_abs_gap:
            return ("BLOCK", 0.0, "unstable_gap")

        # Monotone weight scaler based on effective_strength.
        # Map [gate_min_effective_strength .. 0.85] -> [0 .. 1],
        # clamp outside that range.
        lower = self.gate_min_effective_strength
        upper = 0.85
        if upper <= lower:
            upper = lower + 1e-6  # avoid divide-by-zero

        weight_mult = _clamp(
            (effective_strength - lower) / (upper - lower),
            0.0,
            1.0,
        )

        # Optional extra risk control: halve weight if rolling_gap is large.
        if abs_gap > self.gap_halve_threshold:
            weight_mult *= 0.5

        return ("ALLOW", weight_mult, "ok")
