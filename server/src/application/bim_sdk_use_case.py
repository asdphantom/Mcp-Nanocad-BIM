"""Native coordinate grids, slab contours and opening marks."""
import math

from src.application.bim_structure_use_case import BimStructureUseCase


class BimSdkUseCase(BimStructureUseCase):
    def _operation(self, operation, **payload):
        return self._call("bim_sdk_operation", operation, payload)

    @staticmethod
    def _numbers(values, minimum=1, maximum=100):
        if not isinstance(values, (list, tuple)) or not minimum <= len(values) <= maximum:
            raise ValueError("Expected a bounded numeric array")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError("Expected finite numeric values")

    def list_bim_coordinate_grids(self, limit=50):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer from 1 to 500")
        return self._operation("grid-list", limit=limit)

    def _grid(self, circular, name, x, y, z, origin, direction):
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError("A grid name of at most 100 characters is required")
        for positions in (x, y, z):
            self._numbers(positions)
            if len(set(positions)) != len(positions):
                raise ValueError("Axis positions must be distinct")
        origin = [0, 0, 0] if origin is None else origin
        direction = [1, 0, 0] if direction is None else direction
        self._numbers(origin, 3, 3)
        self._numbers(direction, 3, 3)
        if direction[2] != 0 or (direction[0] == 0 and direction[1] == 0):
            raise ValueError("Direction must be a nonzero horizontal vector")
        if circular and (any(v <= 0 for v in x) or any(not 0 <= v < 360 for v in y)):
            raise ValueError("Circular radii must be positive; angles in degrees must be in [0,360)")
        return self._operation("grid-create", circular=circular, name=name, x=sorted(x), y=sorted(y), z=sorted(z), origin=origin, direction=direction)

    def create_bim_rectangular_grid(self, name, x, y, z, origin=None, direction=None):
        return self._grid(False, name, x, y, z, origin, direction)

    def create_bim_circular_grid(self, name, x, y, z, origin=None, direction=None):
        return self._grid(True, name, x, y, z, origin, direction)

    def redistribute_bim_grid_axes(self, handle, axis="x"):
        self._edit_handle(handle)
        if axis not in ("x", "y", "z"):
            raise ValueError("axis must be x, y or z")
        return self._operation("grid-distribute", handle=handle, axis=axis)

    def assign_bim_coordinate_grid(self, handle, grid_handle):
        self._edit_handle(handle)
        self._edit_handle(grid_handle)
        if int(handle, 16) == int(grid_handle, 16):
            raise ValueError("Grid and target must differ")
        return self._operation("grid-assign", handle=handle, grid_handle=grid_handle)

    def clear_bim_coordinate_grid(self, handle):
        self._edit_handle(handle)
        return self._operation("grid-clear", handle=handle)

    def _polygon(self, points):
        if not isinstance(points, (list, tuple)) or not 3 <= len(points) <= 200:
            raise ValueError("Contour requires 3 to 200 vertices")
        for p in points:
            self._numbers(p, 2, 2)
        vertices = [tuple(p) for p in points]
        if len(set(vertices)) != len(vertices):
            raise ValueError("Contour vertices must be distinct; omit closing duplicate")
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(vertices, vertices[1:] + vertices[:1]))
        if not math.isfinite(area) or abs(area) < 0.001:
            raise ValueError("Contour must have nonzero area")
        # Reject crossings before handing polygon topology to the native SDK.
        def orient(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        def touches(a, b, c):
            return orient(a, b, c) == 0 and min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
        for i, a in enumerate(vertices):
            b = vertices[(i+1) % len(vertices)]
            for j in range(i+2, len(vertices)):
                if i == 0 and j == len(vertices)-1:
                    continue
                c, d = vertices[j], vertices[(j+1) % len(vertices)]
                if (orient(a,b,c)*orient(a,b,d) < 0 and orient(c,d,a)*orient(c,d,b) < 0) or any((touches(a,b,c), touches(a,b,d), touches(c,d,a), touches(c,d,b))):
                    raise ValueError("Contour must not self-intersect")

    def _slab(self, operation, handle, points):
        self._edit_handle(handle)
        self._polygon(points)
        return self._operation(operation, handle=handle, points=points)

    def add_bim_slab_contour(self, handle, points):
        return self._slab("slab-add", handle, points)

    def cut_bim_slab_contour(self, handle, points):
        return self._slab("slab-cut", handle, points)

    def update_bim_slab_contour(self, handle, points):
        return self._slab("slab-update", handle, points)

    def new_bim_window_mark(self, handle, prefix="WIN"):
        self._edit_handle(handle)
        if not isinstance(prefix, str) or not prefix.strip() or len(prefix) > 32 or any(ord(c) < 32 for c in prefix):
            raise ValueError("Mark prefix must have 1 to 32 printable characters")
        return self._operation("window-new-mark", handle=handle, prefix=prefix)
