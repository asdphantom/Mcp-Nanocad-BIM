using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HostMgd.ApplicationServices;
using Teigha.DatabaseServices;
using Teigha.Geometry;
using Multicad;
using Multicad.DatabaseServices;
using Multicad.Mc3D;
using App = HostMgd.ApplicationServices.Application;

namespace CadEngine
{
    public class SolidService
    {
        private static Database Db => HostApplicationServices.WorkingDatabase;
        private static Document? GetDoc()
        {
            var db = HostApplicationServices.WorkingDatabase;
            if (db == null) return null;
            try { return App.DocumentManager.GetDocument(db); }
            catch { return null; }
        }
        private ObjectId? GetId(string h)
        {
            if (!long.TryParse(h, System.Globalization.NumberStyles.HexNumber, null, out var v)) return null;
            try { var id = Db.GetObjectId(false, new Handle(v), 0); return id.IsNull ? null : id; }
            catch { return null; }
        }
        private string MkSolid(Action<Solid3d> act)
        {
            using var tr = Db.TransactionManager.StartTransaction();
            var bt = (BlockTable)tr.GetObject(Db.BlockTableId, OpenMode.ForRead);
            var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);
            var s = new Solid3d(); act(s);
            ms.AppendEntity(s); tr.AddNewlyCreatedDBObject(s, true); tr.Commit();
            using var tr2 = Db.TransactionManager.StartTransaction();
            return ((Entity)tr2.GetObject(s.ObjectId, OpenMode.ForRead)).Handle.Value.ToString("X");
        }
        public EntityResponse CreateBox(BoxRequest r) => new() { Handle = MkSolid(s => s.CreateBox(r.X, r.Y, r.Z)), Type = "SOLID3D" };
        public EntityResponse CreateSphere(SphereRequest r) => new() { Handle = MkSolid(s => s.CreateSphere(r.Radius)), Type = "SOLID3D" };
        public EntityResponse CreateCylinder(CylinderRequest r) => new() { Handle = MkSolid(s => s.CreateFrustum(r.Height, r.Radius, r.Radius, r.Radius)), Type = "SOLID3D" };
        public EntityResponse CreateCone(ConeRequest r) => new() { Handle = MkSolid(s => s.CreateFrustum(r.Height, r.RadiusBottom, r.RadiusBottom, 0)), Type = "SOLID3D" };
        public EntityResponse CreateTorus(TorusRequest r) => new() { Handle = MkSolid(s => s.CreateTorus(r.MajorRadius, r.MinorRadius)), Type = "SOLID3D" };
        public EntityResponse CreateWedge(WedgeRequest r) => new() { Handle = MkSolid(s => s.CreateWedge(r.X, r.Y, r.Z)), Type = "SOLID3D" };
        public EntityResponse CreatePyramid(PyramidRequest r) => new() { Handle = MkSolid(s => s.CreatePyramid(r.Height, r.Sides, r.Radius, 0)), Type = "SOLID3D" };
        private EntityResponse BoolOp(string h1, string h2, BooleanOperationType op)
        {
            var id1 = GetId(h1); var id2 = GetId(h2);
            if (id1 == null || id2 == null) return new EntityResponse { Handle = "", Type = "" };
            using var tr = Db.TransactionManager.StartTransaction();
            var s1 = (Solid3d)tr.GetObject(id1.Value, OpenMode.ForWrite);
            var s2 = (Solid3d)tr.GetObject(id2.Value, OpenMode.ForWrite);
            s1.BooleanOperation(op, s2); s2.Erase(); tr.Commit();
            using var tr2 = Db.TransactionManager.StartTransaction();
            var e = (Entity)tr2.GetObject(id1.Value, OpenMode.ForRead);
            return new EntityResponse { Handle = e.Handle.Value.ToString("X"), Type = "SOLID3D" };
        }
        public EntityResponse BooleanUnion(string h1, string h2) => BoolOp(h1, h2, BooleanOperationType.BoolUnite);
        public EntityResponse BooleanSubtract(string h1, string h2) => BoolOp(h1, h2, BooleanOperationType.BoolSubtract);
        public EntityResponse BooleanIntersect(string h1, string h2) => BoolOp(h1, h2, BooleanOperationType.BoolIntersect);
        public EntityResponse Extrude(ExtrudeRequest req)
        {
            var id = GetId(req.Handle);
            if (id == null) return new EntityResponse { Handle = "", Type = "" };
            using var tr = Db.TransactionManager.StartTransaction();
            var ent = (Entity)tr.GetObject(id.Value, OpenMode.ForRead);
            var crv = new DBObjectCollection();
            if (ent is Curve c) crv.Add(c);
            var reg = Teigha.DatabaseServices.Region.CreateFromCurves(crv);
            if (reg.Count == 0) throw new System.InvalidOperationException("No region");
            var s = new Solid3d(); s.Extrude((Teigha.DatabaseServices.Region)reg[0], req.Height, req.TaperAngle * Math.PI / 180.0);
            var bt = (BlockTable)tr.GetObject(Db.BlockTableId, OpenMode.ForRead);
            var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);
            ms.AppendEntity(s); tr.AddNewlyCreatedDBObject(s, true); tr.Commit();
            using var tr2 = Db.TransactionManager.StartTransaction();
            return new EntityResponse { Handle = ((Entity)tr2.GetObject(s.ObjectId, OpenMode.ForRead)).Handle.Value.ToString("X"), Type = "SOLID3D" };
        }
        public EntityResponse Revolve(RevolveRequest req)
        {
            var id = GetId(req.Handle);
            if (id == null) return new EntityResponse { Handle = "", Type = "" };
            using var tr = Db.TransactionManager.StartTransaction();
            var ent = (Entity)tr.GetObject(id.Value, OpenMode.ForRead);
            var crv = new DBObjectCollection();
            if (ent is Curve c) crv.Add(c);
            var reg = Teigha.DatabaseServices.Region.CreateFromCurves(crv);
            if (reg.Count == 0) throw new System.InvalidOperationException("No region");
            var s = new Solid3d(); s.Revolve((Teigha.DatabaseServices.Region)reg[0], new Point3d(req.AxisX, req.AxisY, req.AxisZ), new Vector3d(req.DirX, req.DirY, req.DirZ), req.Angle * Math.PI / 180.0);
            var bt = (BlockTable)tr.GetObject(Db.BlockTableId, OpenMode.ForRead);
            var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);
            ms.AppendEntity(s); tr.AddNewlyCreatedDBObject(s, true); tr.Commit();
            using var tr2 = Db.TransactionManager.StartTransaction();
            return new EntityResponse { Handle = ((Entity)tr2.GetObject(s.ObjectId, OpenMode.ForRead)).Handle.Value.ToString("X"), Type = "SOLID3D" };
        }
        public SuccessResponse MoveSolid(string h, double dx, double dy, double dz)
        {
            var id = GetId(h);
            if (id == null) return new SuccessResponse { Success = false };
            using var tr = Db.TransactionManager.StartTransaction();
            ((Entity)tr.GetObject(id.Value, OpenMode.ForWrite)).TransformBy(Matrix3d.Displacement(new Vector3d(dx, dy, dz)));
            tr.Commit(); return new SuccessResponse { Success = true };
        }
        public SuccessResponse RotateSolid(string h, double a, double cx, double cy, double cz, double ax, double ay, double az)
        {
            var id = GetId(h);
            if (id == null) return new SuccessResponse { Success = false, Error = "Invalid handle" };
            try
            {
                var result = MainThreadExecutor.Execute(() =>
                {
                    using var tr = Db.TransactionManager.StartTransaction();
                    ((Entity)tr.GetObject(id.Value, OpenMode.ForWrite)).TransformBy(
                        Matrix3d.Rotation(a * Math.PI / 180.0, new Vector3d(ax, ay, az), new Point3d(cx, cy, cz)));
                    tr.Commit();
                    return (object?)new SuccessResponse { Success = true };
                });
                return (SuccessResponse)(result ?? new SuccessResponse { Success = false });
            }
            catch (Exception ex)
            {
                return new SuccessResponse { Success = false, Error = ex.Message };
            }
        }
        public SuccessResponse Set3dView(string dir, string rm)
        {
            // Use ViewTableRecord + ed.SetCurrentView() — same safe pattern as ZoomExtents.
            // Get the ACTIVE document on the main thread (not cached CadContext),
            // because CadContext.ActiveDocument may be stale after new_document().
            try
            {
                var viewDir = dir.ToLowerInvariant() switch
                {
                    "top" => new Vector3d(0, 0, 1),
                    "bottom" => new Vector3d(0, 0, -1),
                    "left" => new Vector3d(-1, 0, 0),
                    "right" => new Vector3d(1, 0, 0),
                    "front" => new Vector3d(0, -1, 0),
                    "back" => new Vector3d(0, 1, 0),
                    "sw" => new Vector3d(-1, -1, 1),
                    "se" => new Vector3d(1, -1, 1),
                    "nw" => new Vector3d(-1, 1, 1),
                    "ne" => new Vector3d(1, 1, 1),
                    _ => new Vector3d(1, -1, 1),  // default: SE isometric
                };

                var result = MainThreadExecutor.Execute(() =>
                {
                    try
                    {
                        // Get the REAL active document on the main thread — not the stale CadContext cache
                        var doc = App.DocumentManager.MdiActiveDocument;
                        if (doc == null)
                            doc = CadContext.ActiveDocument;
                        if (doc == null)
                            return (object?)new SuccessResponse { Success = false, Error = "No active document" };
                        var ed = doc.Editor;
                        var db = HostApplicationServices.WorkingDatabase;
                        if (db == null || ed == null)
                            return (object?)new SuccessResponse { Success = false, Error = "No database or editor" };

                        // Compute extents for zoom (same as ZoomExtents)
                        using var tr = db.TransactionManager.StartTransaction();
                        double minX = double.MaxValue, minY = double.MaxValue;
                        double maxX = double.MinValue, maxY = double.MinValue;
                        double minZ = double.MaxValue, maxZ = double.MinValue;
                        bool hasEntities = false;
                        var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                        var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);
                        foreach (ObjectId id in ms)
                        {
                            try
                            {
                                var ent = (Entity)tr.GetObject(id, OpenMode.ForRead);
                                var ext = ent.GeometricExtents;
                                if (ext.MinPoint.X < minX) minX = ext.MinPoint.X;
                                if (ext.MinPoint.Y < minY) minY = ext.MinPoint.Y;
                                if (ext.MinPoint.Z < minZ) minZ = ext.MinPoint.Z;
                                if (ext.MaxPoint.X > maxX) maxX = ext.MaxPoint.X;
                                if (ext.MaxPoint.Y > maxY) maxY = ext.MaxPoint.Y;
                                if (ext.MaxPoint.Z > maxZ) maxZ = ext.MaxPoint.Z;
                                hasEntities = hasEntities || true;
                            }
                            catch { }
                        }
                        tr.Commit();

                        var vtr = new ViewTableRecord();
                        vtr.ViewDirection = viewDir;
                        if (hasEntities)
                        {
                            // Center on model center
                            double cx = (minX + maxX) / 2;
                            double cy = (minY + maxY) / 2;
                            double cz = (minZ + maxZ) / 2;
                            vtr.Target = new Point3d(cx, cy, cz);

                            // Size view to fit all entities
                            double spanX = maxX - minX;
                            double spanY = maxY - minY;
                            double spanZ = maxZ - minZ;
                            double maxSpan = Math.Max(spanX, Math.Max(spanY, spanZ));
                            double margin = maxSpan * 0.1;
                            if (margin < 1) margin = 1;
                            vtr.Height = maxSpan + 2 * margin;
                            vtr.Width = maxSpan + 2 * margin;
                        }
                        else
                        {
                            vtr.Target = new Point3d(0, 0, 0);
                            vtr.Height = 100;
                            vtr.Width = 100;
                        }

                        ed.SetCurrentView(vtr);
                        return (object?)new SuccessResponse { Success = true };
                    }
                    catch (Exception ex)
                    {
                        PluginEntry.DebugLog($"Set3dView failed: {ex.Message}");
                        return (object?)new SuccessResponse { Success = false, Error = ex.Message };
                    }
                });
                return result as SuccessResponse ?? new SuccessResponse { Success = false, Error = "Main thread executor returned null" };
            }
            catch (System.Exception ex)
            {
                PluginEntry.DebugLog($"Set3dView failed: {ex.Message}");
                return new SuccessResponse { Success = false, Error = ex.Message };
            }
        }
        public SuccessResponse ZoomExt()
        {
            // Use DocumentService.ZoomExtents which has safe SendCommand with try-catch
            return new DocumentService().ZoomExtents();
        }
        public SolidPropertiesResponse GetSolidProps(string h)
        {
            var id = GetId(h);
            if (id == null) return new SolidPropertiesResponse { Handle = h };
            using var tr = Db.TransactionManager.StartTransaction();
            var e = (Entity)tr.GetObject(id.Value, OpenMode.ForRead);
            if (e is Solid3d sol)
            {
                var mp = sol.MassProperties;
                return new SolidPropertiesResponse
                {
                    Handle = h,
                    Volume = mp.Volume,
                    Area = sol.Area,
                    CentroidX = mp.Centroid.X,
                    CentroidY = mp.Centroid.Y,
                    CentroidZ = mp.Centroid.Z,
                };
            }
            return new SolidPropertiesResponse { Handle = h };
        }

        // ── SWEEP / LOFT (command-based) ──
        // These commands require Plus/Pro edition and crash free edition via SendCommand.
        // Return graceful error instead.

        public SuccessResponse SweepSolid(string profileHandle, string pathHandle)
            => new SuccessResponse { Success = false, Error = "Sweep not supported in this edition" };

        public SuccessResponse LoftSolid(string[] sectionHandles)
            => new SuccessResponse { Success = false, Error = "Loft not supported in this edition" };

        // ── FILLET / CHAMFER (via MultiCAD API Mc3dSolid) ──

        private (List<McObjectId> faceIds, List<McObjectId> edgeIds) GetFaceAndEdgeIds(McObjectId solidId)
        {
            try
            {
                // EntityGeomType enum (kPlaneSegment=2, kLine=1?) is in M3D.dll which
                // can't be loaded for reflection (mt.dll dependency).
                // Instead, scan int values 0-10 to find the correct face/edge producers.
                var mi = typeof(Service).GetMethods(BindingFlags.Static | BindingFlags.Public)
                    .First(m => m.Name == "GetLinkedFEVsToObject" && m.GetParameters().Length == 3);

                // Scan to find face-producing enum value
                List<McObjectId> faces = new List<McObjectId>();
                for (int val = 0; val <= 10; val++)
                {
                    try
                    {
                        var raw = mi.Invoke(null, new object[] { solidId, val, true });
                        var coll = raw as System.Collections.IEnumerable;
                        if (coll != null)
                        {
                            var list = coll.Cast<McObjectId>().ToList();
                            if (list.Count > 0) { faces = list; break; }
                        }
                    }
                    catch { }
                }

                // For each face, scan 0-10 to find edge-producing enum value
                var allEdges = new HashSet<McObjectId>();
                foreach (var faceId in faces)
                {
                    for (int ev = 0; ev <= 10; ev++)
                    {
                        try
                        {
                            var ee = mi.Invoke(null, new object[] { faceId, ev, false });
                            var ec = ee as System.Collections.IEnumerable;
                            if (ec != null)
                            {
                                var el = ec.Cast<McObjectId>().ToList();
                                if (el.Count > 0)
                                {
                                    foreach (var edgeId in el) allEdges.Add(edgeId);
                                    break;
                                }
                            }
                        }
                        catch { }
                    }
                }
                return (faces, allEdges.ToList());
            }
            catch (Exception ex)
            {
                PluginEntry.DebugLog($"GetFaceAndEdgeIds failed: {ex.Message}");
                return (new List<McObjectId>(), new List<McObjectId>());
            }
        }

        /// <summary>
        /// Apply fillet or chamfer to an existing solid via MultiCAD Mc3dSolid wrapper.
        /// Uses McObjectId.FromHandle + GetObject to wrap the existing entity —
        /// does NOT erase or recreate the solid, preserving all boolean geometry.
        /// </summary>
        private SuccessResponse ApplyFeature(
            string solidHandle,
            Action<Mc3dSolid, List<McObjectId>> applyFeature)
        {
            var id = GetId(solidHandle);
            if (id == null)
                return new SuccessResponse { Success = false, Error = $"Solid not found: {solidHandle}" };

            return MainThreadExecutor.Execute(() =>
            {
                try
                {
                    PluginEntry.DebugLog($"ApplyFeature: wrapping solid {solidHandle} (oid={id.Value})");
                    var mcId = McObjectId.FromHandle(id.Value.Handle.Value);
                    var mcSolid = mcId.GetObject() as Mc3dSolid;
                    if (mcSolid == null)
                    {
                        PluginEntry.DebugLog($"ApplyFeature: Cannot wrap as Mc3dSolid, trying direct cast...");
                        return new SuccessResponse { Success = false, Error = "Cannot wrap solid as Mc3dSolid" };
                    }
                    PluginEntry.DebugLog($"ApplyFeature: Mc3dSolid OK, ID={mcSolid.ID}");

                    var (faceIds, edgeIds) = GetFaceAndEdgeIds(mcSolid.ID);
                    PluginEntry.DebugLog($"ApplyFeature: faces={faceIds.Count} edges={edgeIds.Count}");
                    if (edgeIds.Count == 0)
                        return new SuccessResponse { Success = false, Error = "No edges found on solid" };

                    applyFeature(mcSolid, edgeIds);
                    McObjectManager.UpdateAll();

                    return new SuccessResponse { Success = true, Handle = solidHandle };
                }
                catch (Exception ex)
                {
                    PluginEntry.DebugLog($"ApplyFeature failed: {ex.Message}\n{ex.StackTrace}");
                    return new SuccessResponse { Success = false, Error = ex.Message };
                }
            }) as SuccessResponse ?? new SuccessResponse { Success = false, Error = "Main thread executor returned null" };
        }

        public SuccessResponse FilletEdgeSolid(string solidHandle, double radius)
        {
            return ApplyFeature(solidHandle, (mcSolid, edgeIds) =>
            {
                PluginEntry.DebugLog($"FilletEdge: attempting {edgeIds.Count} edges, radius={radius}");
                foreach (var eid in edgeIds)
                    PluginEntry.DebugLog($"  edge: {eid}");

                var fillet = mcSolid.AddFilletFeature(edgeIds, radius);
                PluginEntry.DebugLog($"FilletEdge: AddFilletFeature returned {fillet?.GetType().Name ?? "null"}");
                fillet.DbEntity.AddToCurrentDocument();
                PluginEntry.DebugLog("FilletEdge: AddToCurrentDocument done");
                McObjectManager.UpdateAll();
                PluginEntry.DebugLog("FilletEdge: UpdateAll done");
            });
        }

        public SuccessResponse ChamferEdgeSolid(string solidHandle, double dist1, double dist2)
        {
            // Chamfer via MultiCAD Mc3dSolid wrapper with detailed logging
            return ApplyFeature(solidHandle, (mcSolid, edgeIds) =>
            {
                PluginEntry.DebugLog($"ChamferEdge: attempting {edgeIds.Count} edges, dist1={dist1} dist2={dist2}");
                var chamfer = mcSolid.AddChamferFeature(
                    edgeIds,
                    ChamferType.TwoDistances,
                    ChamferSetbackType.None,
                    dist1, dist2, 0);
                chamfer.DbEntity.AddToCurrentDocument();
                PluginEntry.DebugLog("ChamferEdge: feature created, updating...");
                McObjectManager.UpdateAll();
                PluginEntry.DebugLog("ChamferEdge: update complete");
            });
        }

        // ── Assembly / Constraints (command-based) ──
        // These require Plus/Pro edition.

        public SuccessResponse InsertPart(string blockName, double x, double y, double z)
            => new SuccessResponse { Success = false, Error = "InsertPart not supported in this edition" };

        public SuccessResponse AssemblyMate(string handle1, string handle2)
            => new SuccessResponse { Success = false, Error = "Assembly mate not supported in this edition" };

        public SuccessResponse AssemblyAngle(string handle1, string handle2, double angle)
            => new SuccessResponse { Success = false, Error = "Assembly angle not supported in this edition" };

        public SuccessResponse AssemblyTangent(string handle1, string handle2)
            => new SuccessResponse { Success = false, Error = "Assembly tangent not supported in this edition" };

        public SuccessResponse AssemblySymmetry(string handle1, string handle2, string planeHandle)
            => new SuccessResponse { Success = false, Error = "Assembly symmetry not supported in this edition" };
    }
}