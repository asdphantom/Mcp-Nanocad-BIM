# nBIM SDK 26 sample command coverage

The supplied archive contains 102 `CommandMethod` examples. This is the agreed
coverage target. The table records the exact sample command names; a core
equivalent may differ in details such as defaults or the number of objects.
The original sample source remains in the user-provided SDK archive.

| Area | Sample | SDK command | Status |
|---|---|---|---|
| Architecture | BuildingOpeningUI | `nBIMSDK_CreateWindows` | Core equivalent: `create_bim_window` |
| Architecture | BuildingOpeningUI | `nBIMSDK_SetNewWindowMark` | Pending |
| Architecture | BuildingOpeningUI | `nBIMSDK_ChangeWindowMark` | Pending |
| Architecture | BuildingOpeningUI | `nBIMSDK_UpdateMark` | Pending |
| Architecture | BuildingRoofUI | `nBIMSDK_RoofCreate` | Core equivalent: `create_bim_roof` |
| Architecture | BuildingRoofUI | `nBIMSDK_DomeRoofCreate` | Core equivalent: `create_bim_dome_roof` |
| Architecture | BuildingRoofUI | `nBIMSDK_LoftRoofCreate` | Core equivalent: `create_bim_loft_roof` |
| Architecture | BuildingRoofUI | `nBIMSDK_SweepRoofCreate` | Core equivalent: `create_bim_sweep_roof` |
| Architecture | BuildingRoofUI | `nBIMSDK_RoofSlopeCreate` | Pending |
| Architecture | BuildingRoofUI | `nBIMSDK_RoofSlopesCreate` | Pending |
| Architecture | BuildingRoofUI | `nBIMSDK_RoofAddContour` | Pending |
| Architecture | BuildingRoofUI | `nBIMSDK_RoofCutContour` | Pending |
| Architecture | BuildingRoofUI | `nBIMSDK_RoofUpdateContour` | Pending |
| Architecture | BuildingRoofUI | `nBIMSDK_SingleSlopeAddConcour` | Pending |
| Architecture | BuildingRoofUI | `nBIMSDK_SingleSlopeCutConcour` | Pending |
| Architecture | BuildingRoofUI | `nBIMSDK_SingleSlopeUpdateContour` | Pending |
| Architecture | BuildingSlabUI | `nBIMSDK_SlabCreate` | Core equivalent: `create_bim_slab` |
| Architecture | BuildingSlabUI | `nBIMSDK_SlabAddContour` | Pending |
| Architecture | BuildingSlabUI | `nBIMSDK_SlabCutContour` | Pending |
| Architecture | BuildingSlabUI | `nBIMSDK_SlabUpdateContour` | Pending |
| Architecture | BuildingWallUI | `nBIMSDK_WallsCreate` | Core equivalent: `create_bim_wall` |
| Architecture | BuildingWallUI | `nBIMSDK_WallShift` | Pending |
| Architecture | SpaceUI | `nBIMSDK_SpaceCreate` | Core equivalent: `create_bim_space` |
| Architecture | SpaceUI | `nBIMSDK_SpaceUpdate` | Pending |
| Architecture | SpaceUI | `nBIMSDK_SpaceFromPolyline` | Pending |
| Common | ConstructionStages | `NBIM_4DSIMULATION` | Pending |
| Common | ConstructionStages | `nBIMSDK_4DSimulation` | Pending |
| Common | CoordinateGridUI | `nBIMSDK_GetAxisList` | Pending |
| Common | CoordinateGridUI | `nBIMSDK_CreateAxis` | Pending |
| Common | CoordinateGridUI | `nBIMSDK_CreateRoundAxis` | Pending |
| Common | CoordinateGridUI | `nBIMSDK_UpdateAxis` | Pending |
| Common | CoordinateGridUI | `nBIMSDK_AssignAxis` | Pending |
| Common | CoordinateGridUI | `nBIMSDK_ClearAxis` | Pending |
| Common | CoordinateGridUI | `nBIMSDK_TestAxisOnMove` | Pending |
| Common | CoordinateGridUI | `nBIMSDK_TestAxisOnOffset` | Pending |
| Common | MaterialLibraryUI | `nBIMSDK_GetUsedMaterials` | Pending |
| Common | MaterialLibraryUI | `nBIMSDK_GetProjectMaterials` | Pending |
| Common | MaterialLibraryUI | `nBIMSDK_RemoveAllMaterials` | Pending |
| Common | MaterialLibraryUI | `nBIMSDK_AddLibraryMaterials` | Pending |
| Common | MaterialLibraryUI | `nBIMSDK_AssignMaterial` | Pending |
| Common | ncBIMSmgd_sample | `nBIMSDK_objects_list` | Pending |
| Common | ObjectLibraryUI | `NBIMSDK_ReadMetalwareProfiles` | Partial: `search_bim_library` |
| Common | ObjectLibraryUI | `NBIMSDK_AddLibraryObject` | Pending |
| Common | ObjectLibraryUI | `NBIMSDK_AddLibraryObjectIntoFolder` | Pending |
| Common | ObjectLibraryUI | `NBIMSDK_ExportPreview` | Pending |
| Common | ObjectLibraryUI | `NBIMSDK_AddLibraryObjectWithPreview` | Pending |
| Common | ObjectLibraryUI | `NBIMSDK_AddObjectsWithSharedPreview` | Pending |
| Common | ObjectLibraryUI | `NBIMSDK_AddConcreteProfile` | Pending |
| Common | ObjectLibraryUI | `NBIMSDK_AddMetalProfile` | Pending |
| Common | ProjectManager | `nBIMSDK_Show_Viewport_Params` | Pending |
| Common | ProjectManager | `nBIMSDK_Show_Saved_Views` | Pending |
| Common | ProjectManager | `nBIMSDK_Export_View_Picture` | Pending |
| ParametricKit | EntityReloadServer | `nBIMSDK_EntityReloadServer_Start` | Pending |
| ParametricKit | EntityReloadServer | `nBIMSDK_EntityReloadServer_Stop` | Pending |
| ParametricKit | EntitySourceComponents | `nBIMSDK_CreateTableWithSink` | Pending |
| ParametricKit | EntitySourceComponents | `nBIMSDK_CreateTableWithStove` | Pending |
| ParametricKit | EntitySourceUI | `nBIMSDK_CreateBoxObject` | Pending |
| ParametricKit | EntitySourceUI | `nBIMSDK_CreateLadderObject` | Pending |
| ParametricKit | EntitySourceUI | `nBIMSDK_CreateHierarchyObject` | Pending |
| ParametricKit | EntitySourceUI | `nBIMSDK_CreateObjectWithVariables` | Pending |
| ParametricKit | EntitySourceUI | `nBIMSDK_CreateObjectWithComplexGrips` | Pending |
| ParametricObjects | ncBIMObjData | `nBIMSDK_DataPalette` | Pending |
| ParametricObjects | ParametricSolids | `nBIMSDK_CreateParametricBox` | Pending |
| ParametricObjects | ParametricSolids | `nBIMSDK_CreateParametricLadder` | Pending |
| ParametricObjects | ParametricSolids | `nBIMSDK_CreateExtrusion` | Pending |
| ParametricObjects | ParametricSolids | `nBIMSDK_GetExtrusionContours` | Pending |
| ParametricObjects | ParametricSolids | `nBIMSDK_CreateShapes` | Pending |
| ParametricObjects | ParametricSolids | `nBIMSDK_CreateSolids` | Pending |
| ParametricObjects | ParametricSolids | `nBIMSDK_CreateComplexSolids` | Pending |
| Structure | AssemblyUI | `nBIMSDK_AssemblyCreate` | Pending |
| Structure | AssemblyUI | `nBIMSDK_AssemblyInsert` | Pending |
| Structure | AssemblyUI | `nBIMSDK_AssemblyRemove` | Pending |
| Structure | AssemblyUI | `nBIMSDK_AssemblyAdd` | Pending |
| Structure | AssociationUI | `NBIMSDK_GetAssociations` | Pending |
| Structure | AssociationUI | `NBIMSDK_RemoveAssociations` | Pending |
| Structure | AssociationUI | `NBIMSDK_CreateAssociation` | Pending |
| Structure | ConcreteUI | `nBIMSDK_ConcreteBeamCreate` | Pending |
| Structure | ConcreteUI | `nBIMSDK_TestColumn` | Pending |
| Structure | ConcreteUI | `nBIMSDK_ConcreteColumnCreate` | Pending |
| Structure | ConcreteUI | `nBIMSDK_ConcretePlateCreate` | Pending |
| Structure | ConcreteUI | `nBIMSDK_ConcreteBeamResize` | Pending |
| Structure | ConcreteUI | `nBIMSDK_ConcreteBeamProfileUpdate` | Pending |
| Structure | ConcreteUI | `nBIMSDK_ConcreteWallCreate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalBoltJointInfo` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalBoltJointCreate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalBoltJointUpdate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalBeamCreate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalColumnCreate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalBeamProfileUpdate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalColumnProfileUpdate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalPlateCreate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalNodeCreate` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalNodeReplace` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalNodeDelete` | Pending |
| Structure | MetalUI | `nBIMSDK_MetalWeldingSeemInfo` | Pending |
| Structure | ReinforcementUI | `nBIMSDK_ReinfClipCreate` | Pending |
| Structure | ReinforcementUI | `nBIMSDK_ReinfSkewClipCreate` | Pending |
| Structure | ReinforcementUI | `nBIMSDK` | Pending |
| Structure | ReinforcementUI | `nBIMSDK` | Pending |
| Structure | ReinforcementUI | `nBIMSDK` | Pending |
| Structure | ReinforcementUI | `nBIMSDK` | Pending |
| Structure | ReinforcementUI | `nBIMSDK_CreateReinfSpiral` | Pending |
