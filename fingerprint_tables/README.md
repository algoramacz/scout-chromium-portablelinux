# Scout fingerprint combination tables

**This directory (`fingerprint_tables/` at the repo root) is the live, tracked,
editable source of truth** for the per-seed fingerprint value tables (patch 032
— entropy variance). The seed-pick *logic* stays in C++; only the value rows live
here, so you can update a table — most often **adding a freshly-released Chrome
version** — without hunting through C++. On each build, `scripts/build.sh` syncs
these JSON into the patched tree and regenerates the `.inc` (see
`generate_fingerprint_tables` in `scripts/shared.sh`), so a plain edit + rebuild
is all it takes. (Patch `033-fingerprint-tables-json` ships an identical in-tree
default copy so a patch-only build still works, but **edit the files here**.)

## Files

| JSON | Drives | Consumed in |
|------|--------|-------------|
| `chrome_versions.json`   | spoofed Chrome major + full build + weight | `embedder_support/user_agent_utils.cc` |
| `platform_versions.json` | Windows `sec-ch-ua-platform-version` + weight | `blink/common/user_agent/user_agent_metadata.cc` |
| `archetypes.json`        | coherent machine tuples (cores/RAM/GPU/screen) | `components/ungoogled/ungoogled_switches.cc` |
| `gpu_models.json`        | WebGL/WebGPU GPU model pool | `blink/renderer/modules/webgl/gpu_info.cc` |
| `optional_voices.json`   | seed-added Microsoft speech voices | `blink/renderer/modules/speech/speech_synthesis.cc` |
| `optional_fonts.json`    | seed-varied optional Windows fonts | `blink/renderer/platform/fonts/font_cache.cc` |

Each `<name>.json` is a JSON **array of row objects**. `generate.py` turns it
into `<name>.inc` (just the C++ initializer rows); the `.cc` keeps its `struct`
+ `constexpr T kTable[] = { #include "....inc" };` and the seed-pick logic.

## Updating a table (e.g. a new Chrome release)

1. Edit the JSON. Example — when Chrome 150 ships, bump `chrome_versions.json`
   and reweight (newest dominant, real Stable/Windows build strings only):
   ```json
   [
     {"major": 150, "full": "150.0.7900.XX", "weight": 55},
     {"major": 149, "full": "149.0.7827.53", "weight": 30},
     {"major": 148, "full": "148.0.7778.218", "weight": 15}
   ]
   ```
2. Rebuild. The build syncs this dir into the tree and runs `generate.py`
   automatically, regenerating the `.inc` so the affected file recompiles.
3. Commit the edited JSON in this directory (it is tracked in the repo). The
   patch-033 in-tree default is optional to keep in sync — the build always
   sources from here.

Run the codegen manually anytime with: `python3 generate.py`
(or `python3 generate.py --check` to verify the `.inc` are in sync — used as a guard).

## JSON value encoding

The key order in each row **must match the C++ struct field order**. Then:

| JSON | → C++ |
|------|-------|
| `123` / `1.5`        | bare number |
| `true` / `false`     | bare bool |
| `"text"`             | quoted C string |
| `"@GpuVendor::kAmd"` | bare token (for enums/constants — note the leading `@`) |
| `"_comment": "..."`  | trailing `// ...` note on that row (keys starting `_` are not values) |

## Constraints (don't make these a *tell*)

- Use only **real** values: real Chrome Stable build strings, real GPU model
  names + PCI device ids + matching ANGLE vendor, real Windows fonts/voices,
  real `platformVersion` numbers.
- Keep `device_memory_gb` ∈ {4, 8} (spec cap), weights summing to the table's
  `TotalWeight` constant (currently 100 where one exists).
- Keep archetypes **coherent** (no 4-core + halo GPU) and **frequency-matched**
  to reality (1920×1080 dominant, Intel iGPU the largest GPU share). Over-
  flattening a marginal to uniform is itself a correlation signal.
- The spoofed Chrome version should track the binary's real Chromium era — don't
  drift the list far from the version you actually build.
