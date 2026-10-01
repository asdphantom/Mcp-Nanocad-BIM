using System.Globalization;
using BIMStructureMgd.Common;
using BIMStructureMgd.DatabaseObjects;
using BIMStructureMgd.ObjectProperties;
using Teigha.DatabaseServices;
using App = HostMgd.ApplicationServices.Application;

namespace CadEngine.Services;

public sealed class BimMaterialRequest
{
    public string MaterialId { get; set; } = "";
    public string Handle { get; set; } = "";
}

public static class BimMaterialService
{
    private static object Error(string message) => new { success = false, error = message };
    private static bool ValidId(string id) => !string.IsNullOrWhiteSpace(id) && id.Length <= 100 && !id.Any(char.IsControl);

    public static object List(string scope, string? name, int limit)
    {
        if (scope != "library" && scope != "project" && scope != "used") return Error("Invalid material scope");
        if (limit < 1 || limit > 500 || name?.Length > 100) return Error("Invalid filter or limit");
        return MainThreadExecutor.Execute(() =>
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            if (doc == null) return Error("No active nanoCAD document");
            using var docLock = doc.LockDocument();
            using var tr = doc.Database.TransactionManager.StartTransaction();
            var project = ProjectMaterialLibrary.Current;
            var rows = new List<object>();
            var total = 0;
            bool Match(string id, string? materialName) => string.IsNullOrEmpty(name) ||
                id.Contains(name, StringComparison.OrdinalIgnoreCase) ||
                (materialName?.Contains(name, StringComparison.OrdinalIgnoreCase) ?? false);
            void Row(string id, string? materialName, int? usage = null)
            {
                if (!Match(id, materialName)) return;
                ++total;
                if (rows.Count < limit) rows.Add(new { id, name = materialName, resolved = materialName != null, usage_count = usage });
            }
            if (scope == "library")
            {
                var library = new DatabaseMaterialLibrary();
                library.Load();
                foreach (var m in library.Materials.OrderBy(m => m.Id.ToString(), StringComparer.Ordinal)) Row(m.Id.ToString(), m.Name);
            }
            else if (scope == "project")
                foreach (var m in project.Materials.OrderBy(m => m.Id.ToString(), StringComparer.Ordinal)) Row(m.Id.ToString(), m.Name);
            else
            {
                var counts = new Dictionary<string, int>();
                var bt = (BlockTable)tr.GetObject(doc.Database.BlockTableId, OpenMode.ForRead);
                var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);
                foreach (ObjectId oid in ms)
                    if (tr.GetObject(oid, OpenMode.ForRead) is ParametricEntBase entity)
                    {
                        var id = entity.GetElementData().GetParameter(Parameter.Names.BuildMaterialId)?.Value;
                        if (!string.IsNullOrEmpty(id)) counts[id] = counts.GetValueOrDefault(id) + 1;
                    }
                foreach (var pair in counts.OrderBy(p => p.Key, StringComparer.Ordinal))
                    Row(pair.Key, project.GetMaterialById(pair.Key)?.Name, pair.Value);
            }
            return new { success = true, scope, materials = rows, total, limit, truncated = total > limit };
        }) ?? Error("Timed out reading materials");
    }

    public static object Add(BimMaterialRequest req)
    {
        if (!ValidId(req.MaterialId)) return Error("An exact material_id is required");
        return MainThreadExecutor.Execute(() =>
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            if (doc == null) return Error("No active nanoCAD document");
            using var docLock = doc.LockDocument();
            using var tr = doc.Database.TransactionManager.StartTransaction();
            var project = ProjectMaterialLibrary.Current;
            var existing = project.GetMaterialById(req.MaterialId);
            if (existing != null) return new { success = true, id = existing.Id.ToString(), name = existing.Name, added = false };
            var library = new DatabaseMaterialLibrary();
            library.Load();
            var material = library.GetMaterialById(req.MaterialId);
            if (material == null) return Error("Material ID not found in the component library");
            if (!project.Add(material)) return Error("Project material could not be added");
            tr.Commit();
            return new { success = true, id = material.Id.ToString(), name = material.Name, added = true };
        }) ?? Error("Timed out adding material");
    }

    public static object Assign(BimMaterialRequest req)
    {
        if (!ValidId(req.MaterialId) || string.IsNullOrEmpty(req.Handle) ||
            !req.Handle.All(Uri.IsHexDigit) ||
            !long.TryParse(req.Handle, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var h) || h <= 0)
            return Error("A material ID and positive hexadecimal handle are required");
        return MainThreadExecutor.Execute(() =>
        {
            var doc = App.DocumentManager.MdiActiveDocument;
            if (doc == null) return Error("No active nanoCAD document");
            using var docLock = doc.LockDocument();
            using var tr = doc.Database.TransactionManager.StartTransaction();
            var material = ProjectMaterialLibrary.Current.GetMaterialById(req.MaterialId);
            if (material == null) return Error("Add this material to the project first");
            ObjectId oid;
            try { oid = doc.Database.GetObjectId(false, new Handle(h), 0); }
            catch (Exception) { return Error("Entity handle not found"); }
            if (tr.GetObject(oid, OpenMode.ForWrite) is not ParametricEntBase entity)
                return Error("Material assignment requires a native ParametricEntBase");
            var data = entity.GetElementData();
            var previous = data.GetParameter(Parameter.Names.BuildMaterialId)?.Value;
            data.AddParameter(Parameter.Names.BuildMaterialId).Value = material.Id.ToString();
            data.AddParameter(Parameter.Names.BuildMaterialName).Value = material.Name;
            entity.RecordGraphicsModified(true);
            entity.UpdateElements();
            tr.Commit();
            return new { success = true, handle = req.Handle, entity_type = entity.GetType().Name,
                material_id = material.Id.ToString(), material_name = material.Name, previous_material_id = previous };
        }) ?? Error("Timed out assigning material");
    }
}
