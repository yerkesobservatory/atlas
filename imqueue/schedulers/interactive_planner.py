#!/usr/bin/env python3
"""Interactive nightly observation planner for Stone Edge Observatory.

Each observation is shown as a band on an altitude-vs-time plot. Drag a band
left or right to move it; bands cannot overlap and stay inside the night.
Click "Done" (or close the window) to finish. The final schedule is printed
with to_table() from astroplan_scheduler.

Two input modes:

  test     Targets come from TEST_TARGETS below ({name: exposure_sec}). They are
           placed one by one, in order, centered on the time of maximum
           altitude (moved to the nearest free slot if that time is taken).

  general  Observations (a JSON list of the same dictionaries that
           general.schedule() receives) are scheduled with the same blocks,
           constraints and SequentialScheduler as general.schedule(), and the
           resulting times are the starting positions of the bands.

Run from the repository root:

  python -m imqueue.schedulers.interactive_planner --mode test --date 2026-10-07
  python -m imqueue.schedulers.interactive_planner --mode general --observations obs.json
"""

import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.widgets import Button

import astropy.units as u
from astropy.time import Time
from astroplan import FixedTarget, ObservingBlock
from astroplan.constraints import AltitudeConstraint, AtNightConstraint, TimeConstraint
from astroplan.scheduling import Schedule, SequentialScheduler, Transitioner

from imqueue.schedulers.astroplan_scheduler import lookup, seo, to_table

NIGHT_DATE = "2026-10-07"    # evening date, local Pacific time (test mode)
MIN_ALT = 40.0               # altitude floor drawn on the plot, degrees
SUN_ALT_THRESHOLD = -18.0    # astronomical twilight, degrees
MARGIN = 0.5                 # hours of twilight shown either side of the night

# name (anything Simbad resolves) -> total exposure time in seconds
TEST_TARGETS = {
    "delta Cep": 1200,
    "3C 273": 2700,
    "V Boo": 900,
    "M31": 3600,
    "NGC 1499": 5400,
    "M13": 1800,
    "NGC 7293": 3600,
    "M57": 1800,
    "NGC 891": 3600,
}

PALETTE = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
           "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990"]


def compute_night(date_str):
    """Return (start, end) Times of astronomical night for the evening of date_str."""
    t_grid = Time(f"{date_str} 22:00:00", scale="utc") + np.arange(20 * 60) * u.minute
    below = seo.sun_altaz(t_grid).alt.deg < SUN_ALT_THRESHOLD
    if not below.any():
        raise ValueError(f"Sun never reaches {SUN_ALT_THRESHOLD} deg on {date_str}.")
    i_start = int(np.argmax(below))
    after = np.where(~below[i_start:])[0]
    i_end = i_start + int(after[0]) - 1 if after.size else len(t_grid) - 1
    return t_grid[i_start], t_grid[i_end]


def test_blocks():
    """One ObservingBlock per entry of TEST_TARGETS; unresolvable names are skipped."""
    blocks = []
    for name, exposure in TEST_TARGETS.items():
        try:
            target = FixedTarget.from_name(name)
        except Exception as exc:
            print(f"Skipping {name}: not resolved ({exc})")
            continue
        blocks.append(ObservingBlock(target, exposure * u.second, 0, configuration={}))
    return blocks


def general_schedule(observations):
    """Build the schedule general.schedule() builds for these observations.

    Returns (blocks, starts, window_start, window_end), where starts are the
    scheduled start Times of the blocks.
    """
    now = Time.now()
    sunset = seo.sun_set_time(now, which="nearest")
    sunrise = seo.sun_rise_time(now, which="next")
    if sunrise < sunset:
        sunset = seo.sun_set_time(now, which="previous")

    constraints = [AltitudeConstraint(30 * u.deg),
                   AtNightConstraint.twilight_astronomical(),
                   TimeConstraint(sunset, sunrise)]
    obstime = TimeConstraint(now - 0.5 * u.minute, sunrise)
    read_out = 1 * u.second

    blocks = []
    for obs in observations:
        target = lookup(obs)
        if not isinstance(target, FixedTarget):
            print(f"Skipping {obs.get('target')}: unable to compute RA/Dec")
            continue
        priority = obs["options"].get("priority")
        priority = float(priority) if priority else 10.0
        for filt in obs["filters"]:
            blocks.append(ObservingBlock.from_exposures(
                target, priority, max(obs["exposure_time"], 30) * u.second,
                obs["exposure_count"], read_out,
                configuration={"filter": filt}, constraints=[obstime]))

    transitioner = Transitioner(1 * u.deg / u.second, {"filter": {
        ("h-alpha", "[OIII]", "[SII]", "g-band", "r-band", "i-band", "clear"): 0.16 * u.second,
        "default": 0.1 * u.second}})
    scheduler = SequentialScheduler(constraints=constraints, observer=seo,
                                    transitioner=transitioner, gap_time=120 * u.second)
    schedule = Schedule(sunset, sunrise)
    scheduler(blocks, schedule)

    slots = [s for s in schedule.slots if hasattr(s.block, "target")]
    return [s.block for s in slots], [s.start for s in slots], sunset, sunrise


def free_start(start, dur, others, lo, hi):
    """Start (hours) closest to `start` where [start, start + dur] lies inside
    [lo, hi] and does not overlap any (begin, end) interval in `others`.
    Returns None if the block does not fit anywhere."""
    cands = [min(max(start, lo), hi - dur), lo, hi - dur]
    for s, e in others:
        cands += [e, s - dur]
    eps = 1e-9
    ok = [c for c in cands
          if lo - eps <= c <= hi - dur + eps
          and all(c >= e - eps or c + dur <= s + eps for s, e in others)]
    return min(ok, key=lambda c: abs(c - start)) if ok else None


class Planner:
    """Matplotlib window with draggable observation bands.

    Hours are measured from the start of the observing window. If `starts`
    (a list of Times) is None, blocks are placed one by one centered on their
    maximum altitude.
    """

    def __init__(self, blocks, win_start, win_end, starts=None):
        self.t0 = win_start
        self.hi = (win_end - win_start).to(u.hour).value
        self.grid = np.arange(-MARGIN, self.hi + MARGIN, 1 / 30)
        times = self.t0 + self.grid * u.hour

        self.alts = {}
        for b in blocks:
            if b.target.name not in self.alts:
                self.alts[b.target.name] = seo.altaz(times, b.target).alt.deg
        self.sun = seo.sun_altaz(times).alt.deg

        self.blocks, self.dur, self.starts = [], [], []
        for i, b in enumerate(blocks):
            dur = b.duration.to(u.hour).value
            if starts is not None:
                start = (starts[i] - self.t0).to(u.hour).value
            else:
                alt = np.where((self.grid >= 0) & (self.grid <= self.hi),
                               self.alts[b.target.name], -np.inf)
                start = round((self.grid[np.argmax(alt)] - dur / 2) * 60) / 60
                start = free_start(start, dur, list(zip(self.starts, self.ends())),
                                   0, self.hi)
            if start is None:
                print(f"No room left in the night for {self.label(b)}; not placed.")
                continue
            self.blocks.append(b)
            self.dur.append(dur)
            self.starts.append(start)
        self.initial = list(self.starts)
        self.grab = None
        self.build_figure()

    def ends(self):
        return [s + d for s, d in zip(self.starts, self.dur)]

    @staticmethod
    def label(block):
        name = block.target.name
        filt = block.configuration.get("filter")
        return f"{name.rsplit(' ', 1)[0]} [{filt}]" if filt else name

    def clock(self, hours):
        return (self.t0 + hours * u.hour).strftime("%H:%M")

    def build_figure(self):
        self.fig, self.ax = plt.subplots(figsize=(16, 7.5))
        self.fig.subplots_adjust(bottom=0.2)
        ax = self.ax

        names = list(self.alts)
        colors = {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(names)}
        for n in names:
            ax.plot(self.grid, self.alts[n], "--", color=colors[n], alpha=0.35, lw=0.9)

        ax.fill_between(self.grid, 0, 1, where=self.sun > SUN_ALT_THRESHOLD,
                        transform=ax.get_xaxis_transform(), color="#e8a000",
                        alpha=0.18, lw=0)
        ax.axhline(MIN_ALT, color="#555", ls="--", lw=1.2)

        self.rects, self.lines, self.texts = [], [], []
        for b in self.blocks:
            c = colors[b.target.name]
            self.rects.append(ax.add_patch(Rectangle((0, 0), 1, 90, color=c, alpha=0.25, lw=0)))
            self.lines.append(ax.plot([], [], "-", color=c, lw=2.6)[0])
            self.texts.append(ax.text(0, 88, f"{self.label(b)}  ({b.duration.to(u.minute).value:.0f} min)",
                                      rotation=90, ha="center", va="top", fontsize=8,
                                      color="#222", fontweight="bold"))
        for i in range(len(self.blocks)):
            self.redraw(i)

        h0 = self.t0.datetime.hour + self.t0.datetime.minute / 60 + self.t0.datetime.second / 3600
        ticks = np.arange(np.ceil(h0 - MARGIN) - h0, self.hi + MARGIN, 1.0)
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{int(round(h0 + t)) % 24:02d}:00" for t in ticks],
                           rotation=45, ha="right", fontsize=8)
        ax.set_xlim(-MARGIN, self.hi + MARGIN)
        ax.set_ylim(0, 90)
        ax.set_xlabel("UTC")
        ax.set_ylabel("Altitude (deg)")
        ax.set_title(f"{seo.name} - drag observations to adjust times")
        ax.grid(True, alpha=0.4, color="#ccc", lw=0.6)

        self.info = self.fig.text(0.5, 0.085, "", ha="center", fontsize=10)
        self.btn_reset = Button(self.fig.add_axes([0.38, 0.02, 0.1, 0.045]), "Reset")
        self.btn_done = Button(self.fig.add_axes([0.52, 0.02, 0.1, 0.045]), "Done")
        self.btn_reset.on_clicked(self.reset)
        self.btn_done.on_clicked(lambda _: plt.close(self.fig))

        self.fig.canvas.mpl_connect("button_press_event", self.on_press)
        self.fig.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.fig.canvas.mpl_connect("button_release_event", self.on_release)

    def redraw(self, i):
        start, dur = self.starts[i], self.dur[i]
        x = start + np.linspace(0, dur, 40)
        self.rects[i].set_x(start)
        self.rects[i].set_width(dur)
        self.lines[i].set_data(x, np.interp(x, self.grid, self.alts[self.blocks[i].target.name]))
        self.texts[i].set_x(start + dur / 2)

    def describe(self, i):
        start, dur = self.starts[i], self.dur[i]
        a = np.interp(start + np.linspace(0, dur, 40), self.grid,
                      self.alts[self.blocks[i].target.name])
        self.info.set_text(f"{self.label(self.blocks[i])}:  {self.clock(start)} - "
                           f"{self.clock(start + dur)} UTC   altitude {a.min():.0f} - {a.max():.0f} deg")
        self.info.set_color("red" if a.min() < MIN_ALT else "black")

    def on_press(self, event):
        if event.inaxes is not self.ax or event.button != 1 or event.xdata is None:
            return
        for i, (s, d) in enumerate(zip(self.starts, self.dur)):
            if s <= event.xdata <= s + d:
                self.grab = (i, event.xdata - s)
                self.describe(i)
                self.fig.canvas.draw_idle()
                return

    def on_motion(self, event):
        if self.grab is None or event.xdata is None:
            return
        i, offset = self.grab
        proposed = round((event.xdata - offset) * 60) / 60
        others = [(s, s + d) for j, (s, d) in enumerate(zip(self.starts, self.dur)) if j != i]
        self.starts[i] = free_start(proposed, self.dur[i], others, 0, self.hi)
        self.redraw(i)
        self.describe(i)
        self.fig.canvas.draw_idle()

    def on_release(self, event):
        self.grab = None

    def reset(self, event=None):
        self.starts = list(self.initial)
        for i in range(len(self.blocks)):
            self.redraw(i)
        self.info.set_text("")
        self.fig.canvas.draw_idle()

    def schedule(self):
        """Schedule containing the blocks at their current positions."""
        schedule = Schedule(self.t0, self.t0 + self.hi * u.hour)
        for i in np.argsort(self.starts):
            schedule.insert_slot(self.t0 + self.starts[i] * u.hour, self.blocks[i])
        return schedule

    def run(self):
        """Show the window, block until it is closed, and return the schedule."""
        plt.show()
        return self.schedule()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mode", choices=["test", "general"], default="test")
    parser.add_argument("--date", default=NIGHT_DATE, help="test mode: evening date YYYY-MM-DD")
    parser.add_argument("--observations", help="general mode: JSON file with a list of observations")
    args = parser.parse_args()

    if args.mode == "test":
        win_start, win_end = compute_night(args.date)
        blocks, starts = test_blocks(), None
    else:
        with open(args.observations) as f:
            blocks, starts, win_start, win_end = general_schedule(json.load(f))

    if not blocks:
        print("No schedulable targets.")
        return None

    schedule = Planner(blocks, win_start, win_end, starts).run()
    to_table(schedule).pprint(max_lines=-1, max_width=-1)
    return schedule


if __name__ == "__main__":
    main()
