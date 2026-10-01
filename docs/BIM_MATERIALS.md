# Native BIM materials

Implemented against nanoCAD BIM Construction SDK 26, sample
`Samples/Common/MaterialLibraryUI/MaterialLibraryUI.cs`.

| MCP tool | Operation |
|---|---|
| `list_bim_library_materials` | Component database catalog |
| `list_bim_project_materials` | Active project catalog |
| `list_bim_used_materials` | IDs assigned to direct native BIM entities in model space |
| `add_bim_project_material` | Add one exact library ID; existing project ID returns `added=false` |
| `assign_bim_material` | Assign an existing project material to one native entity by handle |

Read tools accept optional `name` (case-insensitive name/ID substring, up to
100 characters) and `limit` (1–500, default 50). Results contain `materials`,
`total`, `limit`, and `truncated`; rows contain `id`, `name`, `resolved`, and
optional `usage_count`. Used-material scanning excludes nested blocks and layouts.
Unknown assigned IDs remain visible with `resolved=false`.

REST: GET `/api/bim/materials?scope=library|project|used&name=...&limit=50`,
POST `/api/bim/materials/add` with `material_id`, POST
`/api/bim/materials/assign` with `material_id` and `handle`.

IDs must be nonempty catalog IDs up to 100 characters. Handles must be positive
hexadecimal signed-64-bit values without a prefix. Assignment rejects ordinary
DWG objects and IDs absent from the project. Mutations run on the CAD thread,
under document lock and transaction, using native `BuildMaterialId` and
`BuildMaterialName` parameters. No COM geometry fallback.

## Workflow and verification

List library → select an exact ID → add it to the project → assign it to a native
entity → inspect used materials. For live acceptance, also inspect object
properties, save/reopen DWG, and confirm the assigned ID persists.

Release/x64 build: 0 errors, 11 existing warnings. Python suite:
1120 passed, 257 skipped, coverage 85.80%. New material tests: 15.
Live nanoCAD assignment and persistence have **not** been verified.
The rebuilt plugin is in `engine/dist`; the running installation was not replaced.

This branch starts at `983481b`. Uncommitted work in the main checkout is excluded.
