using System;
using System.Globalization;
using System.Linq;
using BIMStructureMgd.Common;
using BIMStructureMgd.DatabaseObjects;
using HostMgd.ApplicationServices;
using Teigha.DatabaseServices;
using App = HostMgd.ApplicationServices.Application;
using SdkCommon = BIMStructureMgd.Common;

namespace CadEngine.Services
{
    public static class BimWindowService
    {
        public static object ListWindows()
        {
            return MainThreadExecutor.Execute(() =>
            {
                var request = LibraryRequest.CreateDatabaseRequest();
                request.AddCategoryCondition(LibraryObject.BuildingOpeningCategory);
                request.AddCondition(LibraryObject.ObjectName, "like", "%Окно%");
                var windows = request.Execute()
                    .Select(item => new { name = item.Name, guid = item.GUID.ToString() })
                    .ToArray();
                return new { success = true, windows };
            }) ?? new { success = false, error = "Timed out querying the BIM library" };
        }

        public static object Create(BimWindowRequest request)
        {
            if (string.IsNullOrWhiteSpace(request.WallHandle) ||
                string.IsNullOrWhiteSpace(request.LibraryName) ||
                !double.IsFinite(request.SillHeight) || request.SillHeight < 0 ||
                !double.IsFinite(request.OpeningDepth) || request.OpeningDepth <= 0 ||
                (request.Position.HasValue && !double.IsFinite(request.Position.Value)))
                return new { success = false, error = "Invalid BIM window parameters" };

            if (!long.TryParse(request.WallHandle, NumberStyles.HexNumber,
                               CultureInfo.InvariantCulture, out var handleValue))
                return new { success = false, error = "wall_handle must be hexadecimal" };

            return MainThreadExecutor.Execute(() =>
            {
                var doc = App.DocumentManager.MdiActiveDocument;
                if (doc == null)
                    return new { success = false, error = "No active nanoCAD document" };

                var libraryRequest = LibraryRequest.CreateDatabaseRequest();
                libraryRequest.AddCategoryCondition(LibraryObject.BuildingOpeningCategory);
                libraryRequest.AddCondition(LibraryObject.ObjectName, "=", request.LibraryName);
                var libraryObject = libraryRequest.Execute().FirstOrDefault();
                if (libraryObject == null)
                    return new { success = false, error = "Window not found in the BIM library" };

                using var docLock = doc.LockDocument();
                var db = doc.Database;
                using var tr = db.TransactionManager.StartTransaction();
                var wallId = db.GetObjectId(false, new Handle(handleValue), 0);
                var wall = tr.GetObject(wallId, OpenMode.ForWrite) as BuildingWallBase;
                if (wall == null)
                    return new { success = false, error = "wall_handle is not a native BIM wall" };

                var window = BuildingOpeningFactory.Create(libraryObject);
                var position = request.Position ?? wall.Length / 2;
                if (position < window.Width / 2 ||
                    position > wall.Length - window.Width / 2)
                    return new { success = false, error = "Window does not fit at this wall position" };

                window.Elevation = request.SillHeight;
                window.DimDepth = request.OpeningDepth;
                window.Position = position;
                SdkCommon.Utilities.AddEntityToDatabase(db, tr, window);
                window.ConnectToSurface(wall);
                var mark = BuildingOpeningMarkUtilities.GetAvailableMarkName(
                    BuildingOpeningMarkUtilities.MarkType.Window);
                BuildingOpeningMarkUtilities.SetMarkName(mark, window);
                window.UpdateElements();
                tr.Commit();

                return new
                {
                    success = true,
                    handle = window.Handle.Value.ToString("X"),
                    entity_type = window.GetType().Name,
                    wall_handle = request.WallHandle,
                    library_name = libraryObject.Name,
                    position,
                    sill_height = window.Elevation,
                    width = window.Width,
                    height = window.Height,
                    mark
                };
            }) ?? new { success = false, error = "Timed out waiting for nanoCAD main thread" };
        }
    }
}
