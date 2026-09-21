"""
AI Gym & Fitness Assistant — Angle Smoothing Filters
Phase 2.3 — Joint Angles + Squat State Machine + Rep Counting

Provides deterministic, low-latency signal smoothing filters to attenuate
high-frequency camera noise and subtle landmark jitter without introducing
perceptible phase delay in biomechanical state tracking.
"""

from collections import deque
from typing import Optional


class MovingAverageFilter:
    """
    Sliding window simple moving average (SMA) filter.
    
    Formula:
        smoothed_t = (1 / k) * sum(samples)
        where k = len(samples) <= window_size
        
    Characteristics:
        - Deterministic, explainable, and zero hyperparameter tuning.
        - Graceful startup: computes mean over all available samples when
          sample count < window_size.
        - Low latency: with window_size=5 at 30 FPS, phase delay is only
          ~2-3 frames (~66-100 ms).
    """

    def __init__(self, window_size: int = 5) -> None:
        """
        Initializes the moving average filter.
        
        Args:
            window_size: Maximum number of recent samples to average.
        """
        if window_size < 1:
            raise ValueError(f"window_size must be >= 1, got {window_size}")
        self.window_size = window_size
        self._samples: deque = deque(maxlen=window_size)

    def update(self, sample: Optional[float]) -> Optional[float]:
        """
        Ingests a new sample value and returns the smoothed moving average.
        
        Args:
            sample: The raw float sample, or None if signal is missing/invalid.
            
        Returns:
            Smoothed float value, or None if no valid samples are in the window.
        """
        if sample is None:
            return self.current_value

        self._samples.append(float(sample))
        return sum(self._samples) / len(self._samples)

    @property
    def current_value(self) -> Optional[float]:
        """Returns the current smoothed average without appending a new sample."""
        if not self._samples:
            return None
        return sum(self._samples) / len(self._samples)

    @property
    def sample_count(self) -> int:
        """Number of valid samples currently stored in the window."""
        return len(self._samples)

    def reset(self) -> None:
        """Clears the sample window."""
        self._samples.clear()


class ExponentialMovingAverageFilter:
    """
    First-order Infinite Impulse Response (IIR) exponential smoothing filter.
    
    Formula:
        S_t = alpha * X_t + (1 - alpha) * S_{t-1}
        where alpha in (0.0, 1.0] controls responsiveness vs smoothness.
    """

    def __init__(self, alpha: float = 0.3) -> None:
        """
        Initializes the EMA filter.
        
        Args:
            alpha: Smoothing factor in (0.0, 1.0]. Higher = faster response;
                   lower = smoother signal.
        """
        if not (0.0 < alpha <= 1.0):
            raise ValueError(f"alpha must be in (0.0, 1.0], got {alpha}")
        self.alpha = alpha
        self._current_value: Optional[float] = None

    def update(self, sample: Optional[float]) -> Optional[float]:
        """Ingests a new sample and returns the EMA smoothed value."""
        if sample is None:
            return self._current_value

        if self._current_value is None:
            self._current_value = float(sample)
        else:
            self._current_value = (self.alpha * float(sample)) + (
                (1.0 - self.alpha) * self._current_value
            )
        return self._current_value

    @property
    def current_value(self) -> Optional[float]:
        return self._current_value

    def reset(self) -> None:
        self._current_value = None
