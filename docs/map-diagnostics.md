# Map-step diagnostics

When the map (LinkML-Map transformation) step is slow, uses too much memory, or
gets killed on real data, turn on diagnostics mode. It's opt-in and has **zero
cost when off**.

```bash
make map-data DM_MAP_PROFILE=true DM_INPUT_DIR=... DM_SCHEMA_NAME=... DM_OUTPUT_DIR=...
```

`DM_MAP_PROFILE=true` works on any target that runs the map step (`map-data`,
`pipeline`), and can be passed to the BDC workflow the same way.

## What it captures

For **each entity**, into `<mapped-data>/logs/<Entity>.log` and alongside it:

- **CPU / wall-clock profile** — a [py-spy](https://github.com/benfred/py-spy)
  sampling profile at `<mapped-data>/logs/<Entity>.folded`. py-spy is pulled
  ephemerally via `uv run --with py-spy`, so there's no project dependency to
  carry; it's fetched (a prebuilt wheel) only when the flag is on.
- **Peak memory + OOM evidence** — the container cgroup's `memory.peak` (bytes)
  and `memory.events` (whose `oom_kill` counter increments when the *container's*
  memory limit — not the instance — kills the process). These land as `[diag ...]`
  lines in the entity log.

The exit-code handling is unchanged: a kill still surfaces as a signal exit
(137 = SIGKILL/OOM); the cgroup line just confirms *why*.

## Reading the flamegraph

`<Entity>.folded` is collapsed/folded stacks. Easiest viewers, no install:

- **[speedscope.app](https://www.speedscope.app)** — drag the `.folded` file in.
- `flamegraph.pl <Entity>.folded > flame.svg` (Brendan Gregg's FlameGraph), or
  `uv run --with inferno-cli inferno-flamegraph < <Entity>.folded > flame.svg`.

Wide plateaus are where wall-clock goes. (In the OOM investigation this is where
the per-file `SchemaView` rebuild showed up.)

Note: with parallel entities (`-j`), `memory.peak` is the **whole container's**
peak, not per-entity — profile one entity at a time when memory attribution
matters. py-spy output is always per-process.

---

## Runbook: ad-hoc internal tracing on real data (rare)

The diagnostics above are **external** — they answer "where's the time / memory,
did it get killed" without touching linkml-map internals, which is why they're
safe to keep around. They cannot answer "*which rows vanished where inside the
engine*." That question needs internal instrumentation, and internal
instrumentation is **throwaway by nature**: the useful part is *where* you hook,
and that's specific to the bug you're chasing — you rebuild it per incident, you
don't keep a suite (a kept suite goes stale on the probe points *and* on
linkml-map's internals, and projects coverage it doesn't have).

So this is not code we keep — it's the *pattern*, so a rebuild starts from a
known-safe starting line instead of scratch:

1. **Reach for it last.** First exhaust the external signals (py-spy, cgroup),
   the exit code (see the map exit-code guard), and output-size comparisons. Only
   trace internals when those don't localize it *and* you can't reproduce off a
   small synthetic input — i.e. you must run on the real data.

2. **Inject from a dm-bip-side wrapper, don't fork.** A short script that imports
   linkml-map, monkey-patches the seams you care about (the transform loop in
   `linkml_map.transformer.engine`, the loaders in `linkml_map.loaders`), then
   invokes the CLI. Gate every hook behind an env var so it's inert unless asked.

3. **Data safety is non-negotiable on protected data.** Log **only** counts,
   table/column names, and value *types* — **never cell values**. This is the
   rule that makes running on real BDC data acceptable.

4. **Capture before the kill.** An OOM `SIGKILL` cannot be caught, so don't rely
   on a clean exit: flush counters incrementally and register `atexit` **plus** a
   `SIGTERM`/`SIGINT` handler that dumps current state, so you still get something
   when the run dies.

   The historical implementation of this pattern is archived as the linkml-map tag
   `archive/probe-ff846709` (row-flow counters + RSS-vs-tracemalloc memory
   attribution) — excavate with `git checkout tags/archive/probe-ff846709`. It's a
   reference for the shape, not something to re-adopt wholesale.
