using System.Globalization;
using BIMStructureMgd.Common;
using BIMStructureMgd.DatabaseObjects;
using Teigha.DatabaseServices;
using Teigha.Geometry;
using App = HostMgd.ApplicationServices.Application;

namespace CadEngine.Services;

public sealed class BimEditRequest
{
    public string Handle { get; set; } = "";
    public string SourceHandle { get; set; } = "";
    public double Dx { get; set; }
    public double Dy { get; set; }
    public double Dz { get; set; }
}

public static class BimEditService
{
    private static object Error(string message) => new { success = false, error = message };
    private static bool HandleValue(string value, out long number) =>
        long.TryParse(value, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out number) && number > 0 && value.All(Uri.IsHexDigit);

    public static object Execute(string operation, BimEditRequest req)
    {
        if (!HandleValue(req.Handle, out var handle)) return Error("Invalid entity handle");
        long source = 0;
        if (operation == "copy-mark" && (!HandleValue(req.SourceHandle, out source) || source == handle))
            return Error("Source and target must have different valid handles");
        if (operation == "shift" && (!double.IsFinite(req.Dx) || !double.IsFinite(req.Dy) || !double.IsFinite(req.Dz)))
            return Error("Offsets must be finite");
        if (operation != "shift" && operation != "mark" && operation != "copy-mark") return Error("Invalid operation");
        return MainThreadExecutor.Execute(() =>
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            if (doc == null) return Error("No active nanoCAD document");
            using var docLock = doc.LockDocument();
            using var tr = doc.Database.TransactionManager.StartTransaction();
            ObjectId oid, sourceId = ObjectId.Null;
            try
            {
                oid = doc.Database.GetObjectId(false, new Handle(handle), 0);
                if (operation == "copy-mark") sourceId = doc.Database.GetObjectId(false, new Handle(source), 0);
            }
            catch (Exception) { return Error("Entity handle not found"); }
            var entity = tr.GetObject(oid, operation == "mark" ? OpenMode.ForRead : OpenMode.ForWrite);
            if (operation == "shift")
            {
                if (entity is not LinearBuildingWall wall) return Error("Expected native LinearBuildingWall");
                var offset = new Vector3d(req.Dx, req.Dy, req.Dz);
                wall.StartPoint += offset;
                wall.EndPoint += offset;
                wall.UpdateElements();
                tr.Commit();
                return new { success = true, handle = req.Handle, entity_type = wall.GetType().Name,
                    start = new[] { wall.StartPoint.X, wall.StartPoint.Y, wall.StartPoint.Z },
                    end = new[] { wall.EndPoint.X, wall.EndPoint.Y, wall.EndPoint.Z } };
            }
            if (entity is not BuildingOpening opening) return Error("Expected native BuildingOpening");
            if (operation == "copy-mark")
            {
                if (tr.GetObject(sourceId, OpenMode.ForRead) is not BuildingOpening template)
                    return Error("Source must be native BuildingOpening");
                if (string.IsNullOrWhiteSpace(template.Mark.ToString())) return Error("Source opening has no mark");
                BuildingOpeningMarkUtilities.SetMarkName(template.Mark, opening);
                opening.UpdateElements();
                tr.Commit();
            }
            return new { success = true, handle = req.Handle, entity_type = opening.GetType().Name, mark = opening.Mark.ToString() };
        }) ?? Error("Timed out editing native BIM entity");
    }
}
