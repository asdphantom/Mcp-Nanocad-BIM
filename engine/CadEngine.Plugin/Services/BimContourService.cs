using System;
using System.Linq;
using BIMStructureMgd.DatabaseObjects;
using HostMgd.ApplicationServices;
using Teigha.DatabaseServices;
using Teigha.Geometry;
using SdkCommon = BIMStructureMgd.Common;
using App = HostMgd.ApplicationServices.Application;

namespace CadEngine.Services
{
    // Native architectural entities from the ncBIM SDK 26 contour factories.
    public static class BimContourService
    {
        public static object Create(BimContourRequest request)
        {
            if (string.IsNullOrWhiteSpace(request.Kind) || request.Points == null || request.Points.Length < 3 ||
                request.Points.Any(p => p == null || p.Length != 2 ||
                    !double.IsFinite(p[0]) || !double.IsFinite(p[1])) ||
                !double.IsFinite(request.BaseZ) || !double.IsFinite(request.Height) ||
                !double.IsFinite(request.Thickness) || !double.IsFinite(request.Angle) ||
                !double.IsFinite(request.Overhang))
                return new { success = false, error = "Invalid BIM contour parameters" };

            var kind = request.Kind.Trim().ToLowerInvariant();
            if ((kind == "space" && (request.Height <= 0 || request.BaseZ != 0)) ||
                ((kind == "slab" || kind == "roof") && request.Thickness <= 0) ||
                (kind == "roof" && (request.Angle <= 0 || request.Angle >= 90 || request.Overhang < 0)) ||
                (kind != "space" && kind != "slab" && kind != "roof"))
                return new { success = false, error = "Invalid BIM contour kind or dimensions" };

            var points = request.Points.Select(p => new Point2d(p[0], p[1])).ToArray();
            var area2 = 0.0;
            for (var i = 0; i < points.Length; i++)
            {
                var a = points[i];
                var b = points[(i + 1) % points.Length];
                area2 += a.X * b.Y - b.X * a.Y;
            }
            if (Math.Abs(area2) < 0.001)
                return new { success = false, error = "BIM contour has zero area" };

            return MainThreadExecutor.Execute(() =>
            {
                var doc = App.DocumentManager.MdiActiveDocument;
                if (doc == null)
                    return new { success = false, error = "No active nanoCAD document" };
                using var docLock = doc.LockDocument();
                var db = doc.Database;
                using var tr = db.TransactionManager.StartTransaction();
                Entity entity;
                switch (kind)
                {
                    case "slab":
                        var slab = BuildingSlabFactory.Create(points, request.Thickness);
                        slab.BindingMode = BuildingSlab.BindingType.Center;
                        slab.BasePoint = new Point3d(0, 0, request.BaseZ);
                        slab.UpdateElements();
                        entity = slab;
                        break;
                    case "roof":
                        var roof = BuildingRoofFactory.Create(points, request.Angle,
                            request.Overhang, request.Thickness);
                        roof.BasePoint += new Vector3d(0, 0, request.BaseZ);
                        entity = roof;
                        break;
                    default:
                        var space = SpaceEntityFactory.Create(points, request.Height);
                        if (!string.IsNullOrWhiteSpace(request.Name)) space.Name = request.Name;
                        if (!string.IsNullOrWhiteSpace(request.Number)) space.Number = request.Number;
                        entity = space;
                        break;
                }
                SdkCommon.Utilities.AddEntityToDatabase(db, tr, entity);
                tr.Commit();
                return new
                {
                    success = true,
                    handle = entity.Handle.Value.ToString("X"),
                    entity_type = entity.GetType().Name,
                    kind,
                    point_count = points.Length
                };
            }) ?? new { success = false, error = "Timed out waiting for nanoCAD main thread" };
        }
    }
}
