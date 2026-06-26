using System;
using System.Collections.Generic;
using System.Globalization;
using Multicad;
using Multicad.DatabaseServices;
using Multicad.Geometry;
using Multicad.Mc3D;

namespace CadEngine.Services
{
    /// <summary>
    /// Service for 3D parametric features: Hole, Extrude, Revolve, Mirror, Pattern, Sketch.
    /// Uses McObjectId.FromHandle(long) for handle→McObjectId conversion.
    /// Uses McObjectId.ToHandle(out long, out McObjectId) for McObjectId→handle.
    /// </summary>
    public class FeatureService
    {
        // ── Helpers ──────────────────────────────────────────────

        /// <summary>Convert a hex handle string to McObjectId via FromHandle.</summary>
        private static McObjectId IdFromHandle(string handle)
        {
            var h = long.Parse(handle, NumberStyles.HexNumber);
            return McObjectId.FromHandle(h);
        }

        private static Mc3dSolid? GetSolid(string handle)
        {
            try
            {
                var id = IdFromHandle(handle);
                return id.GetObject() as Mc3dSolid;
            }
            catch { return null; }
        }

        /// <summary>Get an McObjectId handle string from an McObjectId.</summary>
        private static string? HandleFromId(McObjectId id)
        {
            try
            {
                id.ToHandle(out long handleValue, out McObjectId _);
                return handleValue.ToString("X");
            }
            catch { return null; }
        }

        private static object Error(string msg) => new ErrorResponse { Error = msg };

        // ── Hole Features ────────────────────────────────────────

        public object CreateSimpleHole(string solidHandle, double diameter, double depth)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var faces = Service.GetLinkedFEVsToObject(solid.ID, EntityGeomType.kPlaneSegment, true);
                if (faces.Count == 0) return Error("No planar faces found");

                var faceId = faces[0];
                var edges = Service.GetLinkedFEVsToObject(faceId, EntityGeomType.kLine);
                if (edges.Count < 2) return Error("Need at least 2 edges on the face");

                var ipp = IppDefinition.Create(IppDefinitionType.TwoEdges);
                ipp.TargetPlaneId = faceId;
                ipp.SetAssocParams(new McGeomParam { ID = edges[0] }, new McGeomParam { ID = edges[1] });
                ipp.Param1 = 20;
                ipp.Param2 = 30;

                var hole = solid.AddHoleFeature(HoleFeatureType.Simple, ipp);
                if (hole == null) return Error("Failed to create hole feature");
                hole.Diameter = diameter;
                hole.Depth = depth;
                McObjectManager.UpdateAll();
                var hSimple = HandleFromId(hole.ID) ?? "";
                return new { success = true, handle = hSimple };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object CreateThreadedHole(string solidHandle, double diameter, double depth)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var faces = Service.GetLinkedFEVsToObject(solid.ID, EntityGeomType.kPlaneSegment, true);
                if (faces.Count == 0) return Error("No planar faces found");

                var faceId = faces[0];
                var verts = Service.GetLinkedFEVsToObject(faceId, EntityGeomType.kVertex);
                if (verts.Count < 4) return Error("Need at least 4 vertices on the face");

                var ipp = IppDefinition.Create(IppDefinitionType.TwoVertices);
                ipp.TargetPlaneId = faceId;
                ipp.SetAssocParams(new McGeomParam { ID = verts[0] }, new McGeomParam { ID = verts[3] });
                ipp.Sector = 3;
                ipp.Param1 = 20;
                ipp.Param2 = 30;

                var hole = solid.AddHoleFeature(HoleFeatureType.Threaded, ipp);
                if (hole == null) return Error("Failed to create threaded hole");
                hole.Diameter = diameter;
                hole.Depth = depth;
                McObjectManager.UpdateAll();
                var hThreaded = HandleFromId(hole.ID) ?? "";
                return new { success = true, handle = hThreaded };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object CreateStandardHole(string solidHandle, double diameter, double depth)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var faces = Service.GetLinkedFEVsToObject(solid.ID, EntityGeomType.kPlaneSegment, true);
                if (faces.Count == 0) return Error("No planar faces found");

                var faceId = faces[0];
                var edges = Service.GetLinkedFEVsToObject(faceId, EntityGeomType.kLine);
                if (edges.Count < 2) return Error("Need at least 2 edges on the face");

                var ipp = IppDefinition.Create(IppDefinitionType.TwoEdges);
                ipp.TargetPlaneId = faceId;
                ipp.SetAssocParams(new McGeomParam { ID = edges[0] }, new McGeomParam { ID = edges[1] });
                ipp.Param1 = 20;
                ipp.Param2 = 30;

                var hole = solid.AddHoleFeature(HoleFeatureType.Standard, ipp);
                if (hole == null) return Error("Failed to create standard hole");
                hole.Diameter = diameter;
                hole.Depth = depth;
                McObjectManager.UpdateAll();
                var hStandard = HandleFromId(hole.ID) ?? "";
                return new { success = true, handle = hStandard };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        // ── Mirror Feature ───────────────────────────────────────

        public object CreateMirror(string solidHandle, string planeHandle)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var planeId = IdFromHandle(planeHandle);
                var planeObj = planeId.GetObject();
                if (planeObj == null) return Error("Plane not found");

                // Get all features of the solid by iterating children in DocHistory
                var history = McDocumentsManager.GetActiveSheet()?.Get3dHistory();
                if (history == null) return Error("No 3D history available");

                var featureIds = new List<McObjectId>();
                // Get children of the solid to find its features
                var children = history.GetChildrenForItem(solid.ID, false);
                if (children != null)
                {
                    foreach (var childId in children)
                    {
                        var obj = childId.GetObject();
                        if (obj != null)
                            featureIds.Add(childId);
                    }
                }

                if (featureIds.Count == 0) return Error("No features found to mirror");

                solid.AddMirrorFeature(featureIds, planeId);
                McObjectManager.UpdateAll();
                return new { success = true };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        // ── Rectangular Pattern Feature ──────────────────────────

        public object CreateRectangularPattern(string solidHandle, string featureHandle,
            int countX, double spacingX, int countY, double spacingY)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var featureId = IdFromHandle(featureHandle);
                var feature = featureId.GetObject();
                if (feature == null) return Error("Feature not found");

                var dirX = new McGeomParam { ID = featureId, Param = 0 };
                var dirY = new McGeomParam { ID = featureId, Param = 1 };

                var features = new List<McObjectId> { featureId };
                solid.AddRectangularPatternFeature(features, dirX, countX, spacingX, dirY, countY, spacingY);
                McObjectManager.UpdateAll();
                return new { success = true };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        // ── Sketch Features ──────────────────────────────────────

        public object CreateSketch(string solidHandle)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var sketch = solid.AddPlanarSketch();
                if (sketch == null) return Error("Failed to create sketch");

                sketch.DbEntity.AddToCurrentDocument();
                var handle = HandleFromId(sketch.ID);
                return new { success = true, handle = handle ?? "" };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object AddSketchCircle(string sketchHandle,
            double cx, double cy, double cz, double radius)
        {
            try
            {
                var sketchId = IdFromHandle(sketchHandle);
                var sketch = sketchId.GetObject() as PlanarSketch;
                if (sketch == null) return Error("Sketch not found");

                var center = new Point3d(cx, cy, cz);
                sketch.AddGeometry(McObjectId.NewID(), new CircArc3d(center, Vector3d.ZAxis, radius));
                McObjectManager.UpdateAll();
                return new { success = true };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object AddSketchLine(string sketchHandle,
            double x1, double y1, double z1, double x2, double y2, double z2)
        {
            try
            {
                var sketchId = IdFromHandle(sketchHandle);
                var sketch = sketchId.GetObject() as PlanarSketch;
                if (sketch == null) return Error("Sketch not found");

                var p1 = new Point3d(x1, y1, z1);
                var p2 = new Point3d(x2, y2, z2);
                sketch.AddGeometry(McObjectId.NewID(), new LineSeg3d(p1, p2));
                McObjectManager.UpdateAll();
                return new { success = true };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object CreateProfile(string sketchHandle)
        {
            try
            {
                var sketchId = IdFromHandle(sketchHandle);
                var sketch = sketchId.GetObject() as PlanarSketch;
                if (sketch == null) return Error("Sketch not found");

                var profile = sketch.CreateProfile();
                if (profile == null) return Error("Failed to create profile from sketch");

                profile.DbEntity.Visibility = 0;
                profile.DbEntity.AddToCurrentDocument();
                profile.AutoProcessExternalContours();

                var handle = HandleFromId(profile.ID);
                return new { success = true, handle = handle ?? "" };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        // ── Extrude/Revolve Features ─────────────────────────────

        public object CreateExtrudeFeature(string solidHandle, string profileHandle,
            double height, double taperAngle = 0, bool direction = true)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var profileId = IdFromHandle(profileHandle);
                var dir = direction ? FeatureExtentDirection.Positive : FeatureExtentDirection.Negative;
                var feature = solid.AddExtrudeFeature(profileId, height, taperAngle, dir);
                if (feature == null) return Error("Failed to create extrude feature");

                McObjectManager.UpdateAll();
                var handle = HandleFromId(feature.ID);
                return new { success = true, handle = handle ?? "" };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object CreateRevolveFeature(string solidHandle, string profileHandle,
            double axisX, double axisY, double axisZ,
            double dirX, double dirY, double dirZ, double angle)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var profileId = IdFromHandle(profileHandle);
                // Create McGeomParam as the axis parameter
                var axisParam = new McGeomParam();
                // Add a sketch or other geometry to get the axis reference;
                // For axis, we use the McGeomParam with a Line3d representation
                // Actually AddRevolveFeature uses axis as McGeomParam with a work axis ID
                var history = McDocumentsManager.GetActiveSheet()?.Get3dHistory();

                // Try to find a work axis or create one through a workplane
                // For simplicity, use YZ plane normal as revolve axis direction
                if (history != null && history.DoesGCSElementExist(GCSElementType.WPL_YZ))
                {
                    var yzPlane = history.GetGCSElement(GCSElementType.WPL_YZ);
                    if (yzPlane != null)
                        axisParam.ID = yzPlane.ID;
                }
                // Fallback: create the McGeomParam with the profile's ID
                if (axisParam.ID.IsNull)
                    axisParam.ID = profileId;

                var feature = solid.AddRevolveFeature(profileId, axisParam, Util.A2R(angle));
                if (feature == null) return Error("Failed to create revolve feature");

                McObjectManager.UpdateAll();
                var handle = HandleFromId(feature.ID);
                return new { success = true, handle = handle ?? "" };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        // ── Shell Feature (stub — not supported in Free) ──
        public object CreateShell(string solidHandle, double thickness, bool outward)
            => new { success = false, error = "Shell not supported in this edition" };

        // ── Circular Pattern Feature (stub — not supported in Free) ──
        public object CreateCircularPattern(string solidHandle, string featureHandle, int count, double angle)
            => new { success = false, error = "Circular pattern not supported in this edition" };

        // ── Feature Tree Management (Phase P2) ──────────────────

        public object GetFeatureList(string solidHandle)
        {
            var solid = GetSolid(solidHandle);
            if (solid == null) return Error("Solid not found");

            try
            {
                var history = McDocumentsManager.GetActiveSheet()?.Get3dHistory();
                if (history == null) return Error("No 3D history available");

                var children = history.GetChildrenForItem(solid.ID, false);
                var features = new List<object>();

                if (children != null)
                {
                    foreach (var childId in children)
                    {
                        var obj = childId.GetObject();
                        if (obj == null) continue;

                        var handleStr = HandleFromId(childId) ?? "";
                        string typeName = obj.GetType().Name;
                        bool suppressed = false;

                        // Try to extract common properties
                        try
                        {
                            var type = obj.GetType();
                            var suppressProp = type.GetProperty("Suppress");
                            if (suppressProp != null)
                                suppressed = (bool)(suppressProp.GetValue(obj) ?? false);
                        }
                        catch { }

                        var entry = new System.Dynamic.ExpandoObject() as IDictionary<string, object>;
                        entry["handle"] = handleStr;
                        entry["type"] = typeName;
                        entry["suppressed"] = suppressed;

                        // Try to extract known feature properties (diameter, depth, height, etc.)
                        try
                        {
                            var type = obj.GetType();
                            foreach (var prop in type.GetProperties())
                            {
                                if (prop.Name == "Suppress" || prop.Name == "ID" || prop.Name == "DbEntity")
                                    continue;
                                if (prop.PropertyType == typeof(double) || prop.PropertyType == typeof(int) || prop.PropertyType == typeof(string))
                                {
                                    entry[prop.Name] = prop.GetValue(obj)?.ToString() ?? "";
                                }
                            }
                        }
                        catch { }

                        features.Add(entry);
                    }
                }

                return new { success = true, features };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object SuppressFeature(string featureHandle)
        {
            try
            {
                var id = IdFromHandle(featureHandle);
                var obj = id.GetObject();
                if (obj == null) return Error("Feature not found");

                var type = obj.GetType();

                // Try known suppress property names (case-insensitive)
                foreach (var propName in new[] { "Suppress", "Suppressed", "IsSuppressed", "Status" })
                {
                    var prop = type.GetProperty(propName,
                        System.Reflection.BindingFlags.Instance |
                        System.Reflection.BindingFlags.Public |
                        System.Reflection.BindingFlags.IgnoreCase);
                    if (prop != null && prop.PropertyType == typeof(bool))
                    {
                        prop.SetValue(obj, true);
                        McObjectManager.UpdateAll();
                        return new { success = true };
                    }
                }

                // Try method named "SetSuppress" or "Suppress"
                foreach (var methodName in new[] { "SetSuppress", "Suppress" })
                {
                    var method = type.GetMethod(methodName, new Type[] { typeof(bool) });
                    if (method != null)
                    {
                        method.Invoke(obj, new object[] { true });
                        McObjectManager.UpdateAll();
                        return new { success = true };
                    }
                }

                return Error("Feature does not support suppress (no bool Suppress/Suppressed property found)");
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object UnsuppressFeature(string featureHandle)
        {
            try
            {
                var id = IdFromHandle(featureHandle);
                var obj = id.GetObject();
                if (obj == null) return Error("Feature not found");

                var type = obj.GetType();

                // Try known suppress property names (case-insensitive)
                foreach (var propName in new[] { "Suppress", "Suppressed", "IsSuppressed", "Status" })
                {
                    var prop = type.GetProperty(propName,
                        System.Reflection.BindingFlags.Instance |
                        System.Reflection.BindingFlags.Public |
                        System.Reflection.BindingFlags.IgnoreCase);
                    if (prop != null && prop.PropertyType == typeof(bool))
                    {
                        prop.SetValue(obj, false);
                        McObjectManager.UpdateAll();
                        return new { success = true };
                    }
                }

                // Try method named "SetSuppress" or "Unsuppress"
                foreach (var methodName in new[] { "SetSuppress", "Unsuppress" })
                {
                    var method = type.GetMethod(methodName, new Type[] { typeof(bool) });
                    if (method != null)
                    {
                        method.Invoke(obj, new object[] { false });
                        McObjectManager.UpdateAll();
                        return new { success = true };
                    }
                }

                return Error("Feature does not support unsuppress");
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object EditFeatureParameter(string featureHandle, string paramName, double value)
        {
            try
            {
                var id = IdFromHandle(featureHandle);
                var obj = id.GetObject();
                if (obj == null) return Error("Feature not found");

                var type = obj.GetType();
                // Case-insensitive property lookup — feature properties
                // use PascalCase (e.g. "Diameter") while Python sends
                // snake_case or lowercase param names
                var prop = type.GetProperty(paramName,
                    System.Reflection.BindingFlags.Instance |
                    System.Reflection.BindingFlags.Public |
                    System.Reflection.BindingFlags.IgnoreCase);
                if (prop == null) return Error($"Parameter '{paramName}' not found on feature type {type.Name}");

                if (prop.PropertyType == typeof(double))
                    prop.SetValue(obj, value);
                else if (prop.PropertyType == typeof(int))
                    prop.SetValue(obj, (int)value);
                else
                    return Error($"Parameter '{paramName}' type {prop.PropertyType.Name} not supported");

                McObjectManager.UpdateAll();
                return new { success = true };
            }
            catch (Exception ex) { return Error(ex.Message); }
        }

        public object DeleteFeature(string featureHandle)
        {
            try
            {
                var id = IdFromHandle(featureHandle);
                var obj = id.GetObject();
                if (obj == null) return Error("Feature not found");
                var type = obj.GetType();

                // 1. Try DbEntity.Erase()
                var dbEntityProp = type.GetProperty("DbEntity");
                if (dbEntityProp != null)
                {
                    var dbEnt = dbEntityProp.GetValue(obj);
                    if (dbEnt != null)
                    {
                        var eraseMethod = dbEnt.GetType().GetMethod("Erase", new Type[] { typeof(bool) });
                        if (eraseMethod != null)
                        {
                            eraseMethod.Invoke(dbEnt, new object[] { false });
                            McObjectManager.UpdateAll();
                            return new { success = true };
                        }
                    }
                }

                // 2. Try direct Erase(bool)
                var eraseDirect = type.GetMethod("Erase", new Type[] { typeof(bool) });
                if (eraseDirect != null)
                {
                    eraseDirect.Invoke(obj, new object[] { false });
                    McObjectManager.UpdateAll();
                    return new { success = true };
                }

                // 3. Try database EraseObject
                try
                {
                    var hostAppType = Type.GetType("Multicad.DatabaseServices.HostApplicationServices, hostmgd");
                    if (hostAppType != null)
                    {
                        var workingDbProp = hostAppType.GetProperty("WorkingDatabase",
                            System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                        if (workingDbProp != null)
                        {
                            var db = workingDbProp.GetValue(null);
                            if (db != null)
                            {
                                var eraseObjMethod = db.GetType().GetMethod("EraseObject",
                                    new Type[] { typeof(McObjectId) });
                                if (eraseObjMethod != null)
                                {
                                    eraseObjMethod.Invoke(db, new object[] { id });
                                    McObjectManager.UpdateAll();
                                    return new { success = true };
                                }
                            }
                        }
                    }
                }
                catch { }

                // 4. Try getting solid parent and removing feature from its history
                try
                {
                    var history = McDocumentsManager.GetActiveSheet()?.Get3dHistory();
                    if (history != null)
                    {
                        var historyType = history.GetType();
                        var removeMethod = historyType.GetMethod("RemoveItem",
                            new Type[] { typeof(McObjectId) });
                        if (removeMethod != null)
                        {
                            removeMethod.Invoke(history, new object[] { id });
                            McObjectManager.UpdateAll();
                            return new { success = true };
                        }
                    }
                }
                catch { }

                return Error("Cannot delete feature: no erase method available");
            }
            catch (Exception ex) { return Error(ex.Message); }
        }
    }
}
