using System;
using System.Linq;
using BIMStructureMgd.DatabaseObjects;
using HostMgd.ApplicationServices;
using Teigha.DatabaseServices;
using Teigha.Geometry;
using App = HostMgd.ApplicationServices.Application;
using SdkCommon = BIMStructureMgd.Common;

namespace CadEngine.Services
{
    public static class BimRoofVariantService
    {
        private static bool ValidContour(double[][]? points) =>
            points != null && points.Length >= 3 &&
            points.All(p => p != null && p.Length == 2 &&
                double.IsFinite(p[0]) && double.IsFinite(p[1]));

        public static object Create(BimRoofVariantRequest request)
        {
            if (string.IsNullOrWhiteSpace(request.Kind) ||
                !ValidContour(request.ContourA) ||
                !double.IsFinite(request.BaseZ) ||
                !double.IsFinite(request.Thickness) ||
                !double.IsFinite(request.Height))
                return new { success = false, error = "Invalid BIM roof parameters" };
            var kind = request.Kind.ToLowerInvariant();
            if (kind != "dome" && kind != "loft" && kind != "sweep")
                return new { success = false, error = "Unsupported BIM roof kind" };
            if (kind == "dome" && request.Thickness <= 0 ||
                kind == "loft" && request.Height <= 0 ||
                kind != "dome" && !ValidContour(request.ContourB))
                return new { success = false, error = "Invalid BIM roof dimensions or second contour" };

            var a = request.ContourA.Select(p => new Point2d(p[0], p[1])).ToArray();
            var b = (request.ContourB ?? Array.Empty<double[]>()).Select(p => new Point2d(p[0], p[1])).ToArray();
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
                    case "dome":
                        var dome = BuildingRoofDomeFactory.Create(a, request.Thickness);
                        dome.BasePoint = new Point3d(0, 0, request.BaseZ);
                        entity = dome;
                        break;
                    case "loft":
                        var loft = BuildingRoofLoftFactory.Create(a, b, request.Height);
                        loft.BasePoint = new Point3d(0, 0, request.BaseZ);
                        entity = loft;
                        break;
                    default:
                        var sweep = BuildingRoofSweepFactory.Create(a, b);
                        sweep.BasePoint = new Point3d(0, 0, request.BaseZ);
                        entity = sweep;
                        break;
                }
                SdkCommon.Utilities.AddEntityToDatabase(db, tr, entity);
                tr.Commit();
                return new
                {
                    success = true,
                    handle = entity.Handle.Value.ToString("X"),
                    entity_type = entity.GetType().Name,
                    kind
                };
            }) ?? new { success = false, error = "Timed out waiting for nanoCAD main thread" };
        }
    }
}
