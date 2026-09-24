using System;
using System.Linq;
using BIMStructureMgd.Common;

namespace CadEngine.Services
{
    public static class BimLibraryService
    {
        public static object Search(string category, string? name, int limit)
        {
            if (limit < 1 || limit > 100)
                return new { success = false, error = "limit must be between 1 and 100" };
            if (name != null && name.Length > 100)
                return new { success = false, error = "name filter is too long" };
            return MainThreadExecutor.Execute(() =>
            {
                var request = LibraryRequest.CreateDatabaseRequest();
                switch (category.ToLowerInvariant())
                {
                    case "opening":
                        request.AddCategoryCondition(LibraryObject.BuildingOpeningCategory);
                        break;
                    case "metalware":
                        request.AddCategoryCondition(LibraryObject.MetalwareCategory);
                        break;
                    case "metalware_node":
                        request.AddCategoryCondition(LibraryObject.MetalwareNodeCategory);
                        break;
                    case "concrete_profile":
                        request.AddCategoryCondition(LibraryObject.ConcreteProfileCategory);
                        break;
                    case "reinforcement":
                        request.AddCategoryCondition(LibraryObject.ReinforcementCategory);
                        break;
                    case "structural_surface":
                        request.AddCategoryCondition(LibraryObject.StructuralSurfaceCategory);
                        break;
                    default:
                        return new { success = false, error = "Unsupported BIM library category" };
                }
                if (!string.IsNullOrWhiteSpace(name))
                    request.AddCondition(LibraryObject.ObjectName, "like", "%" + name + "%");
                var objects = request.Execute().Take(limit)
                    .Select(item => new { name = item.Name, guid = item.GUID.ToString() })
                    .ToArray();
                return new { success = true, category, objects, limit };
            }) ?? new { success = false, error = "Timed out querying BIM library" };
        }
    }
}
