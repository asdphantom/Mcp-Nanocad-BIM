# Native BIM editing

| Tool | Arguments | Result |
|---|---|---|
| `shift_bim_wall` | `handle`, `dx`, `dy`, optional `dz=0`, millimetres | Native wall start/end coordinates after translation |
| `get_bim_window_mark` | `handle` | Native opening mark as a string |
| `copy_bim_window_mark` | `source_handle`, target `handle` | Target native opening mark after copying |

POST routes: `/api/bim/edit/shift`, `/api/bim/edit/mark`,
`/api/bim/edit/copy-mark`; JSON argument names match the tools.
All require the in-process BIM engine and an active document.
Handles are positive signed-64-bit hexadecimal values without a prefix.
Offsets must be finite numbers; source and target must differ.
Wrong native entity types and absent handles fail without committing.

SDK references: `Architecture/BuildingWallUI` (`nBIMSDK_WallShift`),
`Architecture/BuildingOpeningUI` (`nBIMSDK_ChangeWindowMark`).
Opening tools also support other native BuildingOpening objects, not just windows.
Copy uses the SDK mark utility and retains the old project catalog mark, which
may be reused. It does not rewrite a whole series or change the library template.
Transactions and document locks cover native mutations; model regeneration
uses `UpdateElements`.

Build and Python contracts are verified; interactive appearance and save/reopen
persistence still require testing inside nanoCAD. Python coverage measures the
MCP/server path and does not establish native C# runtime coverage.

Final Python suite: 1176 passed, 257 skipped; total statement coverage 86.22%.
All seven BIM use cases and the use-case factory have 100% statement coverage.
This is not a claim of 100% branch coverage or native SDK runtime coverage.
