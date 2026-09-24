using System;
using BIMStructureMgd.DatabaseObjects;
using HostMgd.ApplicationServices;
using Teigha.Geometry;
using SdkCommon = BIMStructureMgd.Common;
using App = HostMgd.ApplicationServices.Application;

namespace CadEngine.Services
{
    public static class BimWallService
    {
        public static object Create(BimWallRequest request)
        {
            if (!double.IsFinite(request.X1) || !double.IsFinite(request.Y1) ||
                !double.IsFinite(request.X2) || !double.IsFinite(request.Y2) ||
                !double.IsFinite(request.BaseZ) || !double.IsFinite(request.Height) ||
                !double.IsFinite(request.Thickness) || request.Height <= 0 ||
                request.Thickness <= 0 ||
                (request.X1 == request.X2 && request.Y1 == request.Y2))
                return new { success = false, error = "Invalid BIM wall geometry" };

            // The SDK sample documents geometry, height and thickness. Type and
            // project level need a separately verified mapping, so reject them.
            if (!string.IsNullOrWhiteSpace(request.WallType) ||
                !string.IsNullOrWhiteSpace(request.Level))
                return new
                {
                    success = false,
                    error = "wall_type and level are not mapped to the nBIM SDK yet; omit them. No wall was created."
                };

            return MainThreadExecutor.Execute(() =>
            {
                var doc = App.DocumentManager.MdiActiveDocument;
                if (doc == null)
                    return new { success = false, error = "No active nanoCAD document" };

                var db = doc.Database;
                using var docLock = doc.LockDocument();
                using var tr = db.TransactionManager.StartTransaction();
                var start = new Point3d(request.X1, request.Y1, request.BaseZ);
                var end = new Point3d(request.X2, request.Y2, request.BaseZ);
                var wall = LinearBuildingWallFactory.Create(start, end);
                wall.Height = request.Height;
                wall.Thickness = request.Thickness;
                SdkCommon.Utilities.AddEntitiesToDatabase(db, tr, new[] { wall });
                wall.UpdateElements();
                tr.Commit();

                return new
                {
                    success = true,
                    handle = wall.Handle.Value.ToString("X"),
                    entity_type = wall.GetType().Name,
                    height = wall.Height,
                    thickness = wall.Thickness
                };
            }) ?? new { success = false, error = "Timed out waiting for nanoCAD main thread" };
        }
    }
}
