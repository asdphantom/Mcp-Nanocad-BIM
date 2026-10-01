using System.Globalization;
using BIMStructureMgd.Common;
using BIMStructureMgd.DatabaseObjects;
using Teigha.DatabaseServices;
using Teigha.Geometry;
using App = HostMgd.ApplicationServices.Application;

namespace CadEngine.Services;

public sealed class BimRoofSlopeDefinition
{
    public double[] Start { get; set; } = Array.Empty<double>();
    public double[] End { get; set; } = Array.Empty<double>();
    public double[][] Points { get; set; } = Array.Empty<double[]>();
    public double Angle { get; set; } = 45;
    public double Thickness { get; set; } = 150;
}

public sealed class BimRoofEditRequest
{
    public string Handle { get; set; } = "";
    public double[][] Points { get; set; } = Array.Empty<double[]>();
    public BimRoofSlopeDefinition[] Slopes { get; set; } = Array.Empty<BimRoofSlopeDefinition>();
}

public static class BimRoofEditService
{
    private static object Error(string message) => new { success = false, error = message };
    private static bool Vector(double[]? value) => value != null && value.Length == 3 && value.All(double.IsFinite);
    private static bool Slope(BimRoofSlopeDefinition? s) => s != null && Vector(s.Start) && Vector(s.End) &&
        (s.Start[0] != s.End[0] || s.Start[1] != s.End[1]) && s.Start[2] == s.End[2] &&
        double.IsFinite(s.Angle) && s.Angle > 0 && s.Angle < 90 && double.IsFinite(s.Thickness) && s.Thickness > 0 && BimSdkService.Polygon(s.Points);

    public static object Execute(string operation, BimRoofEditRequest req)
    {
        var create = operation == "create-slopes";
        var single = operation.StartsWith("slope-");
        if (!new[] { "create-slopes", "roof-add", "roof-cut", "roof-update", "slope-add", "slope-cut", "slope-update" }.Contains(operation)) return Error("Unknown roof operation");
        long handle = 0;
        if (create)
        {
            if (req.Slopes == null || req.Slopes.Length < 1 || req.Slopes.Length > 32 || req.Slopes.Any(s => !Slope(s))) return Error("Invalid slope definitions");
        }
        else
        {
            if (!long.TryParse(req.Handle,NumberStyles.HexNumber,CultureInfo.InvariantCulture,out handle) || handle <= 0 || !req.Handle.All(Uri.IsHexDigit)) return Error("Invalid roof handle");
            if (single)
            {
                if (req.Points == null || req.Points.Any(p => !Vector(p)) || !BimSdkService.Polygon(req.Points.Select(p => new[] { p[0],p[1] }).ToArray())) return Error("Invalid XYZ slope contour");
            }
            else if (!BimSdkService.Polygon(req.Points)) return Error("Invalid XY roof contour");
        }
        return MainThreadExecutor.Execute(() =>
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            if (doc == null) return Error("No active nanoCAD document");
            using var docLock = doc.LockDocument();
            using var tr = doc.Database.TransactionManager.StartTransaction();
            if (create)
            {
                var slopes = new List<BuildingRoofSlope>();
                foreach (var s in req.Slopes)
                {
                    var roof = BuildingRoofSlopeFactory.Create(new Point3d(s.Start[0],s.Start[1],s.Start[2]),
                        new Point3d(s.End[0],s.End[1],s.End[2]),s.Points.Select(p => new Point2d(p[0],p[1])).ToArray(),s.Angle,s.Thickness);
                    Utilities.AddEntityToDatabase(doc.Database,tr,roof);
                    roof.UpdateElements();
                    slopes.Add(roof);
                }
                tr.Commit();
                return new { success = true, count = slopes.Count, slopes = slopes.Select(s => new { handle = s.Handle.Value.ToString("X"), entity_type = s.GetType().Name }).ToArray() };
            }
            ObjectId oid;
            try { oid = doc.Database.GetObjectId(false,new Handle(handle),0); }
            catch (Exception) { return Error("Roof handle not found"); }
            var obj = tr.GetObject(oid,OpenMode.ForWrite);
            if (single)
            {
                if (obj is not BuildingRoofSlope roof) return Error("Expected native BuildingRoofSlope");
                if (roof.IsMultiSlope) return Error("Select a single slope; multi-slope contour edits are unsupported");
                var points = req.Points.Select(p => new Point3d(p[0],p[1],p[2])).ToList();
                if (operation == "slope-add") roof.AddContour(points);
                else if (operation == "slope-cut") roof.CutContour(points);
                else roof.UpdateContour(points);
                roof.UpdateElements();
            }
            else
            {
                if (obj is not BuildingRoof roof) return Error("Expected native BuildingRoof");
                var points = req.Points.Select(p => new Point2d(p[0],p[1])).ToList();
                if (operation == "roof-add") roof.AddContour(points);
                else if (operation == "roof-cut") roof.CutContour(points);
                else roof.UpdateContour(points);
                roof.UpdateElements();
            }
            tr.Commit();
            return new { success = true, handle = req.Handle, entity_type = obj.GetType().Name, operation, point_count = req.Points.Length };
        }) ?? Error("Timed out editing native roof");
    }
}
