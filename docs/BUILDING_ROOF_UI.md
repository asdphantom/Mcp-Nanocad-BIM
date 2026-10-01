# BuildingRoofUI: all 12 SDK sample commands

All commands in the SDK 26 `Samples/Architecture/BuildingRoofUI/BuildingRoofUI.cs`
now have native MCP equivalents. All 12 operations were exercised in nanoCAD BIM 26 on 2026-10-01.
Native readback and save/reopen persistence passed; see [live report](LIVE_API_2026-10-01.md).

| SDK command | MCP tool | Live status |
|---|---|---|
| `nBIMSDK_RoofCreate` | `create_bim_roof` | Verified 2026-10-01 |
| `nBIMSDK_DomeRoofCreate` | `create_bim_dome_roof` | Verified 2026-10-01 |
| `nBIMSDK_LoftRoofCreate` | `create_bim_loft_roof` | Verified 2026-10-01 |
| `nBIMSDK_SweepRoofCreate` | `create_bim_sweep_roof` | Verified 2026-10-01 |
| `nBIMSDK_RoofSlopeCreate` | `create_bim_roof_slope` | Verified 2026-10-01 |
| `nBIMSDK_RoofSlopesCreate` | `create_bim_roof_slopes` | Verified 2026-10-01 |
| `nBIMSDK_RoofAddContour` | `add_bim_roof_contour` | Verified 2026-10-01 |
| `nBIMSDK_RoofCutContour` | `cut_bim_roof_contour` | Verified 2026-10-01 |
| `nBIMSDK_RoofUpdateContour` | `update_bim_roof_contour` | Verified 2026-10-01 |
| `nBIMSDK_SingleSlopeAddConcour` | `add_bim_roof_slope_contour` | Verified 2026-10-01 |
| `nBIMSDK_SingleSlopeCutConcour` | `cut_bim_roof_slope_contour` | Verified 2026-10-01 |
| `nBIMSDK_SingleSlopeUpdateContour` | `update_bim_roof_slope_contour` | Verified 2026-10-01 |

The `Concour` spelling above is the exact spelling in the supplied SDK source.

## New contracts

Slope creation accepts `start`, `end` (horizontal nonzero baseline, XYZ in mm),
`points` (simple footprint, XY in mm), `angle` (degrees, strictly between 0 and
90, default 45), and `thickness` (positive mm, default 150). The baseline Z is
passed to the factory and applied once as a BasePoint Z offset, as required
by SDK 26: the factory does not preserve the supplied baseline elevation.
The factory-computed XY position is retained. Ordered baseline endpoints determine the SDK slope orientation.

```json
{"tool":"create_bim_roof_slope","arguments":{"start":[0,0,3000],"end":[4000,0,3000],"points":[[0,0],[4000,0],[4000,3000],[0,3000]],"angle":30,"thickness":150}}
```

Batch creation accepts `slopes`, 1–32 definitions using the same keys. All are
validated before mutation and created under one transaction. The result contains
`count` and `slopes` with each native handle/type. They remain independent
BuildingRoofSlope entities, matching the SDK sample; no joined assembly is made.

Roof add/cut/update accept `handle` of a native BuildingRoof and XY `points`.
Single-slope add/cut/update accept `handle` of a BuildingRoofSlope and XYZ
`points`, matching the SDK's Point3d overload. Multi-slope objects are rejected
for these single-slope operations. Coordinates are passed to the SDK unchanged;
the native SDK determines the resulting contour topology and geometry.

All polygons contain 3–200 distinct finite vertices, without a repeated closing
vertex. XY projections must be simple and have nonzero area. Contour edits retain
the target's elevation and thickness. Prefix-free positive signed-64-bit
hexadecimal handles are required. Wrong entity types fail without commit.

POST `/api/bim/roof-edit/{operation}` uses `create-slopes`, `roof-add`,
`roof-cut`, `roof-update`, `slope-add`, `slope-cut`, `slope-update`.
Creation JSON contains a `slopes` array; edits contain `handle` and `points`.
All operations require the loaded in-process BIM engine and active document.

## Live acceptance

Create a single slope and a batch; inspect orientation, baseline elevation and
thickness. Apply an overlapping addition, a cut and a replacement to both a
native roof and a single slope. Inspect graphics after regeneration, then save
and reopen DWG to confirm geometry and entity types persist. Test wrong entity
handles and invalid batches to confirm no partial mutation. These checks passed on 2026-10-01, including invalid entity types, invalid
batches, and unchanged native properties after reopening.

Verification: 39 new roof tests passed; full suite **1272 passed, 257 skipped**,
Python statement coverage **86.68%**. New roof-edit use case: **100%**.
Release/x64 build: **0 errors, 11 existing warnings**.
