using System;
using System.Linq;
using BIMStructureMgd.Common;
using BIMStructureMgd.DatabaseObjects;
using HostMgd.ApplicationServices;
using Teigha.DatabaseServices;
using Teigha.Geometry;
using App = HostMgd.ApplicationServices.Application;
using SdkCommon = BIMStructureMgd.Common;

namespace CadEngine.Services
{
    public static class BimConcreteMemberService
    {
        public static object Create(BimConcreteMemberRequest request)
        {
            var values = new[] { request.X1, request.Y1, request.Z1, request.X2, request.Y2, request.Z2 };
            var kind = request.Kind?.Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(request.ProfileName) || values.Any(v => !double.IsFinite(v)) ||
                (request.X1 == request.X2 && request.Y1 == request.Y2 && request.Z1 == request.Z2) ||
                (kind != "beam" && kind != "column") ||
                (kind == "column" && (request.X1 != request.X2 || request.Y1 != request.Y2 || request.Z2 <= request.Z1)))
                return new { success = false, error = "Invalid concrete member profile or axis" };

            return MainThreadExecutor.Execute(() =>
            {
                var doc = App.DocumentManager.MdiActiveDocument;
                if (doc == null) return new { success = false, error = "No active nanoCAD document" };
                var libraryRequest = LibraryRequest.CreateDatabaseRequest();
                libraryRequest.AddCategoryCondition(LibraryObject.ConcreteProfileCategory);
                libraryRequest.AddCondition(LibraryObject.ObjectName, "=", request.ProfileName);
                var profile = libraryRequest.Execute().FirstOrDefault();
                if (profile == null)
                    return new { success = false, error = "Concrete profile not found in BIM library" };

                using var docLock = doc.LockDocument();
                var db = doc.Database;
                using var tr = db.TransactionManager.StartTransaction();
                var start = new Point3d(request.X1, request.Y1, request.Z1);
                var end = new Point3d(request.X2, request.Y2, request.Z2);
                Entity member;
                if (kind == "beam")
                {
                    var beam = ConcreteBeamFactory.Create(profile, null);
                    beam.SetLocation(start, end);
                    member = beam;
                }
                else
                {
                    var column = ConcreteColumnFactory.Create(profile, null);
                    column.SetLocation(start, end, Vector3d.XAxis);
                    member = column;
                }
                SdkCommon.Utilities.AddEntityToDatabase(db, tr, member);
                tr.Commit();
                return new
                {
                    success = true,
                    handle = member.Handle.Value.ToString("X"),
                    entity_type = member.GetType().Name,
                    kind,
                    profile_name = profile.Name
                };
            }) ?? new { success = false, error = "Timed out waiting for nanoCAD main thread" };
        }
    }
}
