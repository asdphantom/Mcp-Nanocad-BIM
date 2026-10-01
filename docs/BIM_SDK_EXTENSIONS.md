# Ten native SDK operations

| MCP tool | SDK operation |
|---|---|
| `list_bim_coordinate_grids` | List model-space CoordinateGrid objects and axis data |
| `create_bim_rectangular_grid` | CoordinateGridRef.Create with X/Y/Z positions |
| `create_bim_circular_grid` | Same factory, GridType.Circle |
| `redistribute_bim_grid_axes` | Redistribute interior AxisData points |
| `assign_bim_coordinate_grid` | InterLocationObjectId assignment |
| `clear_bim_coordinate_grid` | Clear InterLocationObjectId |
| `add_bim_slab_contour` | BuildingSlab.AddContour |
| `cut_bim_slab_contour` | BuildingSlab.CutContour |
| `update_bim_slab_contour` | BuildingSlab.UpdateContour |
| `new_bim_window_mark` | GetAvailableMarkName + SetMarkName |

SDK sources: `Samples/Common/CoordinateGridUI`,
`Samples/Architecture/BuildingSlabUI`, and
`Samples/Architecture/BuildingOpeningUI` in SDK 26.

## Contracts

Grid creation requires `name`, `x`, `y`, `z` arrays of 1–100 distinct finite
positions each. Positions are sorted. Rectangular grids use absolute positions
in millimetres. Circular grids use positive radii in X and angles in degrees
in Y, from 0 inclusive to 360 exclusive; Z contains levels in millimetres.
Optional origin defaults to `[0,0,0]`; horizontal nonzero direction defaults
to `[1,0,0]` and is normalized by the native service. Labels use SDK defaults,
with numeric X labels. Grid names are not unique keys; repeated creation creates
another grid. List accepts `limit=50`, maximum 500, and reports total/truncated.

Redistribution accepts grid `handle` and `axis="x"|"y"|"z"`, requiring at
least three axes. It preserves endpoint positions and all labels. Grid binding
accepts target `handle` and `grid_handle`; only native MetalAxisEntity and
StructuralPartBase are supported. Clearing accepts target `handle`.

Slab edits accept native slab `handle` and 3–200 distinct `[x,y]` vertices in
world XY millimetres, without a duplicated closing point. Zero area and
self-intersection are rejected. SDK determines the resulting boolean topology;
these calls do not move the slab vertically or change thickness.

New opening mark accepts `handle`, optional printable `prefix="WIN"` of at
most 32 characters. SDK selects the next available mark for the opening's mark
type. Existing old catalog marks are retained.

All routes are POST `/api/bim/sdk/{operation}`; operation suffixes are
`grid-list`, `grid-create`, `grid-distribute`, `grid-assign`, `grid-clear`,
`slab-add`, `slab-cut`, `slab-update`, `window-new-mark`. Creation distinguishes
grid types through JSON `circular`. Other JSON keys match MCP argument names.

## Verification boundary

Mutations use the CAD main thread, active-document lock and native transaction.
Invalid entity classes or handles fail without commit. Python input tests and
SDK compilation do not verify CAD graphics or persistence. Live grid/binding/slab-contour/mark checks and save/reopen persistence passed
on 2026-10-01. See [report and limits](LIVE_API_2026-10-01.md).
No installed nanoCAD plugin was replaced by this development branch.

Verification: 57 new contract tests passed; complete suite 1233 passed,
257 skipped, 86.51% statement coverage. New use case: 100% statement coverage.
Release/x64 build: zero errors, 11 existing warnings.
