# nBIM SDK 26 compatibility

This repository targets nanoCAD BIM Строительство 26 and uses the user-supplied
`ncBIM_SDK_260(7583.34101.272)` during local builds. The SDK archive and its
assemblies are not redistributed here. The sample projects are a guide to the
API, not a complete list of every public type in `ncBIMSmgd.dll`.

## Implemented native objects

| MCP tool | SDK factory or API | Verified in running nanoCAD |
|---|---|---|
| `create_bim_wall` | `LinearBuildingWallFactory.Create` | Yes, `LinearBuildingWall` |
| `search_bim_library` | `LibraryRequest` for six SDK categories | Yes, openings, metalware and concrete profiles |
| `list_bim_windows` | `LibraryRequest` / `BuildingOpeningCategory` | Yes, 52 library entries |
| `create_bim_window` | `BuildingOpeningFactory.Create`, `ConnectToSurface` | Yes, opening E67 in wall E55 |
| `create_bim_slab` | `BuildingSlabFactory.Create` | Yes, `BuildingSlab` |
| `create_bim_roof` | `BuildingRoofFactory.Create` | Yes, `BuildingRoof` |
| `create_bim_space` | `SpaceEntityFactory.Create` | Yes, `SpaceEntity` |

The older `create_wall_solid`, `create_monolithic_slab`, `complete_window_opening`
and similar construction helpers make DWG geometry. They are separate from the
native SDK tools above.

## SDK sample inventory

The supplied archive contains 102 commands across 21 sample groups. Coverage is
tracked below so that unimplemented areas remain visible. A sample command may
need multiple MCP tools or may be interactive and require redesign for automation.

| Area | Sample group | Commands in SDK sample | Native MCP coverage |
|---|---|---:|---|
| Architecture | BuildingOpeningUI | 4 | Library window list and insertion |
| Architecture | BuildingRoofUI | 12 | Create standard roof |
| Architecture | BuildingSlabUI | 4 | Create slab |
| Architecture | BuildingWallUI | 2 | Create linear wall |
| Architecture | SpaceUI | 3 | Create space |
| Common | ConstructionStages | 2 | Pending |
| Common | CoordinateGridUI | 8 | Pending |
| Common | MaterialLibraryUI | 5 | Pending |
| Common | ObjectLibraryUI | 8 | Pending |
| Common | ProjectManager | 3 | Pending |
| Common | ncBIMSmgd_sample | 1 | Pending |
| Structure | AssemblyUI | 4 | Pending |
| Structure | AssociationUI | 3 | Pending |
| Structure | ConcreteUI | 7 | Pending |
| Structure | MetalUI | 12 | Pending |
| Structure | ReinforcementUI | 7 | Pending |
| ParametricKit | EntityReloadServer | 2 | Pending |
| ParametricKit | EntitySourceComponents | 2 | Pending |
| ParametricKit | EntitySourceUI | 5 | Pending |
| ParametricObjects | ParametricSolids | 7 | Pending |
| ParametricObjects | ncBIMObjData | 1 | Pending |

## Compatibility constraints

- Native BIM operations require the in-process .NET plugin in nanoCAD BIM
  Строительство 26. The Python COM fallback cannot create these SDK entities.
- Wall `wall_type` and `level` are explicitly rejected until their SDK mappings
  are verified. Space creation currently uses elevation zero.
- The roof tool implements the standard contour roof factory; dome, loft,
  sweep and slope roof factories are still pending.
- The generic library search supports six known SDK categories and a name
  filter, returning at most 100 matches. The window catalog filters names
  containing `Окно`. The insertion
  tool requires an exact name from that catalog and a native wall handle.
- Builds require the SDK's `ncBIMSmgd.dll` at `work/ncBIM_SDK_26/include-x64`
  or a caller-provided `NCadBIMSDK` path. The installed nanoCAD libraries are
  resolved through `NanoCadPlatformRoot`.

The next implementation groups are roof variants, contour editing, grids,
material and object libraries, project management, structure and reinforcement,
and parametric objects. Each group needs a typed API contract and live checks
before it can be marked compatible.
