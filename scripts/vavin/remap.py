"""The vertical remap: raising the x-height without wrecking the letters.

The naive way to raise an x-height is to scale the lowercase by s about the
baseline. That works for the body of the letter but it also multiplies the
ascender by s, so the font grows, and every horizontal stroke gets s times
thicker while the vertical stems stay put.

The naive fix - a piecewise-linear y-map with a breakpoint at the x-height -
puts a visible crease wherever an outline crosses the breakpoint.

What we do instead is define a *slope profile* g(y) and integrate it:

    f(y) = integral from 0 to y of g(t) dt

Because g > 0 everywhere, f is strictly increasing: an outline can never fold
onto itself. Because g is continuous, f is C1: no kinks. And because we choose
where g dips, we control exactly which part of the letter absorbs the change:

    g = s   from the baseline up past the x-height  -> the body of the letter
            (bowls, shoulders, counters) is a *pure uniform scale*. Not
            distorted, just bigger.

    g = k   through the middle of the ascender      -> this is a straight
            vertical stem. Compressing a straight vertical line changes
            nothing about its shape. The compression is mathematically
            invisible here, which is why we put all of it here.

    g = 1   through the ascender terminal           -> the serif and its
            bracket are *translated*, not scaled, so they keep their drawn
            weight and shape.

k is solved numerically so that f(ascender) lands exactly on target.
"""

from __future__ import annotations

from dataclasses import dataclass


def _smoothstep(t: float) -> float:
    """C1 Hermite blend, 0 at t=0, 1 at t=1, zero derivative at both ends."""
    return t * t * (3.0 - 2.0 * t)


def _smoothstep_integral(t: float) -> float:
    """Integral of _smoothstep from 0 to t, for t in [0, 1]."""
    return t**3 - 0.5 * t**4


@dataclass(frozen=True)
class _Segment:
    """A slope segment. Slope goes s0 -> s1 across [y0, y1] via smoothstep."""

    y0: float
    y1: float
    s0: float
    s1: float

    @property
    def span(self) -> float:
        return self.y1 - self.y0

    def integral(self, y: float) -> float:
        """Integral of the slope from self.y0 up to y (y clamped to segment)."""
        if y <= self.y0:
            return 0.0
        span = self.span
        if span <= 0:
            return 0.0
        t = min(1.0, (y - self.y0) / span)
        return span * (self.s0 * t + (self.s1 - self.s0) * _smoothstep_integral(t))

    def total(self) -> float:
        return self.integral(self.y1)

    def slope_at(self, y: float) -> float:
        span = self.span
        if span <= 0:
            return self.s1
        t = min(1.0, max(0.0, (y - self.y0) / span))
        return self.s0 + (self.s1 - self.s0) * _smoothstep(t)


class VerticalRemap:
    """A monotone, C1 map from source y to target y, pinned at the baseline.

    Build it from measured proportions, not from declared metadata.
    """

    def __init__(
        self,
        *,
        x_height: float,
        ascender: float,
        x_scale: float,
        ascender_scale: float = 1.0,
        pure_scale_headroom: float = 90.0,
        blend_width: float = 70.0,
        terminal_depth: float = 70.0,
        blend_at_terminal: float = 40.0,
        descender_mode: str = "uniform",
        descender: float = -290.0,
        descender_scale: float = 0.95,
    ) -> None:
        self.x_height = x_height
        self.ascender = ascender
        self.s = x_scale
        self.target_ascender = ascender * ascender_scale
        self.descender_mode = descender_mode
        self.descender = descender

        p = x_height + pure_scale_headroom
        b = blend_width
        t = ascender - terminal_depth
        b2 = blend_at_terminal

        if not (p + b <= t and t + b2 <= ascender):
            raise ValueError(
                "remap bands overlap: need "
                f"x_height+headroom+blend ({p + b:.0f}) <= ascender-terminal ({t:.0f}) "
                f"and ({t + b2:.0f}) <= ascender ({ascender:.0f}). "
                "Reduce PURE_SCALE_HEADROOM / BLEND_WIDTH / TERMINAL_DEPTH."
            )

        self._p, self._b, self._t, self._b2 = p, b, t, b2
        self.k = self._solve_k()
        self._segments = self._build(self.k)

        # Below the baseline.
        if descender_mode == "uniform":
            self._below_slope_near = self.s
            self._below_slope_far = self.s
        elif descender_mode == "compress":
            self._below_slope_near = self.s
            # slope that lands the descender on descender * descender_scale
            self._below_slope_far = self._solve_descender_slope(descender_scale)
        else:
            raise ValueError(f"unknown descender_mode {descender_mode!r}")

    # -- construction ------------------------------------------------------

    def _build(self, k: float) -> list[_Segment]:
        s, p, b, t, b2 = self.s, self._p, self._b, self._t, self._b2
        return [
            _Segment(0.0, p, s, s),
            _Segment(p, p + b, s, k),
            _Segment(p + b, t, k, k),
            _Segment(t, t + b2, k, 1.0),
            # Slope 1 above the ascender, so anything sitting up there (tall
            # accents, ascending Greek) is translated, not scaled. Finite on
            # purpose: an infinite span makes the smoothstep integral evaluate
            # inf * 0 = nan, which silently poisons the solver.
            _Segment(t + b2, t + b2 + 10.0 * self.ascender, 1.0, 1.0),
        ]

    def _f_at_ascender(self, k: float) -> float:
        total = 0.0
        for seg in self._build(k):
            if seg.y0 >= self.ascender:
                break
            total += seg.integral(min(seg.y1, self.ascender))
        return total

    def _solve_k(self) -> float:
        """Bisect on k so that f(ascender) == target_ascender."""
        lo, hi = -5.0, 5.0
        target = self.target_ascender
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if self._f_at_ascender(mid) < target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def _solve_descender_slope(self, descender_scale: float) -> float:
        """Slope for the deep part of the descender, blended from s."""
        depth = abs(self.descender)
        target = -depth * descender_scale
        blend = min(self._b, depth * 0.5)
        lo, hi = 0.01, self.s
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            # segment 1: [-blend, 0] at slope s ; segment 2: below, s -> mid
            val = -(blend * self.s)
            seg = _Segment(0.0, depth - blend, self.s, mid)
            val -= seg.integral(depth - blend)
            if val < target:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    # -- evaluation --------------------------------------------------------

    def __call__(self, y: float) -> float:
        if y >= 0:
            last = self._segments[-1]
            if y > last.y1:
                # Beyond the modelled range: pure translation, slope 1.
                return self(last.y1) + (y - last.y1)
            total = 0.0
            for seg in self._segments:
                if y <= seg.y0:
                    break
                total += seg.integral(y)
            return total

        # Below the baseline, mirrored.
        depth = -y
        if self.descender_mode == "uniform":
            return -depth * self.s
        blend = min(self._b, abs(self.descender) * 0.5)
        if depth <= blend:
            return -depth * self.s
        seg = _Segment(0.0, abs(self.descender) - blend, self.s, self._below_slope_far)
        return -(blend * self.s) - seg.integral(depth - blend)

    def slope_at(self, y: float) -> float:
        if y < 0:
            return self.s if self.descender_mode == "uniform" else self._below_slope_far
        for seg in self._segments:
            if y <= seg.y1:
                return seg.slope_at(y)
        return 1.0

    @property
    def x_height_delta(self) -> float:
        """How far the x-height rose, in font units."""
        return self(self.x_height) - self.x_height

    def describe(self) -> str:
        rows = [
            "  vertical remap",
            "  " + "-" * 58,
            f"    x-height scale s        {self.s:.4f}  ({(self.s - 1) * 100:+.1f}%)",
            f"    stem compression k      {self.k:.4f}",
            f"    pure-scale zone         0 .. {self._p:.0f}",
            f"    blend                   {self._p:.0f} .. {self._p + self._b:.0f}",
            f"    compressed stem         {self._p + self._b:.0f} .. {self._t:.0f}",
            f"    terminal blend          {self._t:.0f} .. {self._t + self._b2:.0f}",
            f"    rigid translation       {self._t + self._b2:.0f} and above",
            f"    descender mode          {self.descender_mode}",
            "",
            "    checkpoints",
        ]
        for label, y in (
            ("baseline", 0.0),
            ("x-height", self.x_height),
            ("n/m/r shoulder", self.x_height + 25),
            ("t top", self.x_height + 70),
            ("ascender", self.ascender),
            ("descender", self.descender),
        ):
            rows.append(
                f"      {label:<16} {y:>7.0f} -> {self(y):>7.0f}"
                f"   ({self(y) - y:+.0f}, slope {self.slope_at(y):.3f})"
            )
        return "\n".join(rows)
