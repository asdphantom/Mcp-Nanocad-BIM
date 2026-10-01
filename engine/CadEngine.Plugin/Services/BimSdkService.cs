using System.Globalization;
using BIMStructureMgd.Common;
using BIMStructureMgd.DatabaseObjects;
using Teigha.DatabaseServices;
using Teigha.Geometry;
using App = HostMgd.ApplicationServices.Application;

namespace CadEngine.Services;

public sealed class BimSdkRequest
{
    public string Handle { get; set; } = "";
    public string GridHandle { get; set; } = "";
    public string Name { get; set; } = "";
    public string Axis { get; set; } = "x";
    public string Prefix { get; set; } = "WIN";
    public int Limit { get; set; } = 50;
    public bool Circular { get; set; }
    public double[] X { get; set; } = Array.Empty<double>();
    public double[] Y { get; set; } = Array.Empty<double>();
    public double[] Z { get; set; } = Array.Empty<double>();
    public double[] Origin { get; set; } = new double[] { 0, 0, 0 };
    public double[] Direction { get; set; } = new double[] { 1, 0, 0 };
    public double[][] Points { get; set; } = Array.Empty<double[]>();
}

public static class BimSdkService
{
    private static object Error(string message) => new { success = false, error = message };
    private static bool ValidHandle(string value, out long number) =>
        long.TryParse(value, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out number) && number > 0 && value.All(Uri.IsHexDigit);
    private static bool Numbers(double[]? values, int min, int max) =>
        values != null && values.Length >= min && values.Length <= max && values.All(double.IsFinite);
    private static bool Positions(double[]? values) => Numbers(values, 1, 100) && values!.Distinct().Count() == values!.Length;

    internal static bool Polygon(double[][]? points)
    {
        if (points == null || points.Length < 3 || points.Length > 200 || points.Any(p => !Numbers(p, 2, 2))) return false;
        if (points.Select(p => (p[0], p[1])).Distinct().Count() != points.Length) return false;
        var area = 0.0;
        double Orient(double[] a, double[] b, double[] c) => (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
        bool Touch(double[] a, double[] b, double[] c) => Orient(a,b,c) == 0 && c[0] >= Math.Min(a[0],b[0]) && c[0] <= Math.Max(a[0],b[0]) && c[1] >= Math.Min(a[1],b[1]) && c[1] <= Math.Max(a[1],b[1]);
        for (int i = 0; i < points.Length; ++i)
        {
            var a = points[i]; var b = points[(i+1)%points.Length];
            area += a[0]*b[1]-b[0]*a[1];
            for (int j = i+2; j < points.Length; ++j)
            {
                if (i == 0 && j == points.Length-1) continue;
                var c = points[j]; var d = points[(j+1)%points.Length];
                if ((Orient(a,b,c)*Orient(a,b,d)<0 && Orient(c,d,a)*Orient(c,d,b)<0) || Touch(a,b,c) || Touch(a,b,d) || Touch(c,d,a) || Touch(c,d,b)) return false;
            }
        }
        return double.IsFinite(area) && Math.Abs(area) >= 0.001;
    }

    public static object Execute(string operation, BimSdkRequest req)
    {
        var operations = new[] { "grid-list", "grid-create", "grid-distribute", "grid-assign", "grid-clear", "slab-add", "slab-cut", "slab-update", "window-new-mark" };
        if (!operations.Contains(operation)) return Error("Unknown SDK operation");
        long handle = 0, gridHandle = 0;
        if (operation != "grid-list" && operation != "grid-create" && !ValidHandle(req.Handle, out handle)) return Error("Invalid entity handle");
        if (operation == "grid-list" && (req.Limit < 1 || req.Limit > 500)) return Error("Limit must be 1 to 500");
        if (operation == "grid-create" &&
            (string.IsNullOrWhiteSpace(req.Name) || req.Name.Length > 100 || !Positions(req.X) || !Positions(req.Y) || !Positions(req.Z) ||
             !Numbers(req.Origin,3,3) || !Numbers(req.Direction,3,3) || req.Direction[2] != 0 || (req.Direction[0] == 0 && req.Direction[1] == 0) ||
             (req.Circular && (req.X.Any(v => v <= 0) || req.Y.Any(v => v < 0 || v >= 360))))) return Error("Invalid grid geometry");
        if (operation == "grid-assign" && (!ValidHandle(req.GridHandle, out gridHandle) || gridHandle == handle)) return Error("Invalid grid target");
        if (operation == "grid-distribute" && req.Axis != "x" && req.Axis != "y" && req.Axis != "z") return Error("Axis must be x, y or z");
        if (operation.StartsWith("slab-") && !Polygon(req.Points)) return Error("A simple finite polygon with 3 to 200 distinct vertices is required");
        if (operation == "window-new-mark" && (string.IsNullOrWhiteSpace(req.Prefix) || req.Prefix.Length > 32 || req.Prefix.Any(char.IsControl))) return Error("Invalid mark prefix");

        return MainThreadExecutor.Execute(() =>
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            if (doc == null) return Error("No active nanoCAD document");
            using var docLock = doc.LockDocument();
            using var tr = doc.Database.TransactionManager.StartTransaction();
            object Axes(CoordinateGrid.AxisData a) => a.Points.Select(p => new { position = p.Position, label = p.Label }).ToArray();
            object GridRow(CoordinateGrid g) => new { handle = g.Handle.Value.ToString("X"), name = g.Name, grid_type = g.GridType.ToString(), x = Axes(g.AxisX), y = Axes(g.AxisY), z = Axes(g.AxisZ) };
            if (operation == "grid-list")
            {
                var bt = (BlockTable)tr.GetObject(doc.Database.BlockTableId, OpenMode.ForRead);
                var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);
                var grids = ms.Cast<ObjectId>().Select(id => tr.GetObject(id, OpenMode.ForRead)).OfType<CoordinateGrid>().ToArray();
                var rows = new List<object>();
                foreach (var grid in grids.Take(req.Limit))
                {
                    try
                    {
                        // SDK 26 reference grid data requires write-open access;
                        // this read transaction is rolled back without commit.
                        grid.UpgradeOpen();
                        rows.Add(GridRow(grid));
                    }
                    catch (Exception ex)
                    {
                        rows.Add(new { handle = grid.Handle.Value.ToString("X"), readable = false, error = ex.Message });
                    }
                }
                return new { success = true, grids = rows, total = grids.Length, truncated = grids.Length > req.Limit };
            }
            if (operation == "grid-create")
            {
                var grid = CoordinateGridRef.Create(new Point3d(req.Origin[0],req.Origin[1],req.Origin[2]), new Vector3d(req.Direction[0],req.Direction[1],0).GetNormal(), req.Name);
                if (req.Circular) grid.GridType = CoordinateGrid.CoordinateGridType.Circle;
                grid.AxisX.Add(req.X.OrderBy(v => v).ToArray());
                grid.AxisY.Add(req.Y.OrderBy(v => v).ToArray());
                grid.AxisZ.Add(req.Z.OrderBy(v => v).ToArray());
                grid.AxisX.LabelNaming = CoordinateGrid.AxisData.LabelNamingType.Numbers;
                Utilities.AddEntityToDatabase(doc.Database,tr,grid);
                grid.RecordGraphicsModified(true);
                tr.Commit();
                return new { success = true, grid = GridRow(grid), handle = grid.Handle.Value.ToString("X"), entity_type = grid.GetType().Name };
            }
            ObjectId oid, gridId = ObjectId.Null;
            try
            {
                oid = doc.Database.GetObjectId(false,new Handle(handle),0);
                if (operation == "grid-assign") gridId = doc.Database.GetObjectId(false,new Handle(gridHandle),0);
            }
            catch (Exception) { return Error("Entity handle not found"); }
            var obj = tr.GetObject(oid,OpenMode.ForWrite);
            if (operation == "grid-distribute")
            {
                if (obj is not CoordinateGrid grid) return Error("Expected native coordinate grid");
                var axis = req.Axis == "x" ? grid.AxisX : req.Axis == "y" ? grid.AxisY : grid.AxisZ;
                var points = axis.Points.OrderBy(p => p.Position).ToArray();
                if (points.Length < 3) return Error("Redistribution requires at least three axes");
                var start = points[0].Position;
                var step = (points[^1].Position-start)/(points.Length-1);
                for (int i = 1; i < points.Length-1; ++i) points[i].Position = start+step*i;
                grid.RecordGraphicsModified(true);
                tr.Commit();
                return new { success = true, grid = GridRow(grid) };
            }
            if (operation == "grid-assign" || operation == "grid-clear")
            {
                if (operation == "grid-assign" && tr.GetObject(gridId,OpenMode.ForRead) is not CoordinateGrid) return Error("Grid handle is not a native coordinate grid");
                if (obj is MetalAxisEntity metal) metal.InterLocationObjectId = gridId;
                else if (obj is StructuralPartBase part) part.InterLocationObjectId = gridId;
                else return Error("Expected MetalAxisEntity or StructuralPartBase");
                tr.Commit();
                return new { success = true, handle = req.Handle, grid_handle = operation == "grid-clear" ? null : req.GridHandle };
            }
            if (operation.StartsWith("slab-"))
            {
                if (obj is not BuildingSlab slab) return Error("Expected native BuildingSlab");
                var points = req.Points.Select(p => new Point2d(p[0],p[1])).ToList();
                if (operation == "slab-add") slab.AddContour(points);
                else if (operation == "slab-cut") slab.CutContour(points);
                else slab.UpdateContour(points);
                slab.UpdateElements();
                tr.Commit();
                return new { success = true, handle = req.Handle, entity_type = slab.GetType().Name, operation, point_count = points.Count };
            }
            if (obj is not BuildingOpening opening) return Error("Expected native BuildingOpening");
            var mark = BuildingOpeningMarkUtilities.GetAvailableMarkName(BuildingOpeningMarkUtilities.GetMarkType(opening),req.Prefix);
            BuildingOpeningMarkUtilities.SetMarkName(mark,opening);
            opening.UpdateElements();
            tr.Commit();
            return new { success = true, handle = req.Handle, mark = opening.Mark.ToString() };
        }) ?? Error("Timed out executing SDK operation");
    }
}
