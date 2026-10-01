"""Native nBIM material catalog and targeted assignment."""
from src.application.bim_structure_use_case import BimStructureUseCase


class BimMaterialUseCase(BimStructureUseCase):
    def _list(self, scope, name=None, limit=50):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500")
        if name is not None and (not isinstance(name, str) or len(name) > 100):
            raise ValueError("name must be a string of at most 100 characters")
        return self._call("list_bim_materials", scope, name, limit)

    def list_bim_library_materials(self, name=None, limit=50):
        return self._list("library", name, limit)

    def list_bim_project_materials(self, name=None, limit=50):
        return self._list("project", name, limit)

    def list_bim_used_materials(self, name=None, limit=50):
        return self._list("used", name, limit)

    @staticmethod
    def _material_id(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 100 or any(ord(c) < 32 for c in value):
            raise ValueError("material_id must be a nonempty catalog ID of at most 100 characters")

    def add_bim_project_material(self, material_id):
        self._material_id(material_id)
        return self._call("add_bim_project_material", {"material_id": material_id})

    def assign_bim_material(self, handle, material_id):
        if not self._handle(handle) or int(handle, 16) > 0x7FFFFFFFFFFFFFFF:
            raise ValueError("Expected a positive hexadecimal entity handle")
        self._material_id(material_id)
        return self._call("assign_bim_material", {"handle": handle, "material_id": material_id})
