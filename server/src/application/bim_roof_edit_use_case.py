"""Remaining BuildingRoofUI SDK operations."""
from src.application.bim_sdk_use_case import BimSdkUseCase


class BimRoofEditUseCase(BimSdkUseCase):
    def _roof_call(self, operation, payload):
        return self._call("bim_roof_operation", operation, payload)

    def _slope(self, start, end, points, angle, thickness):
        self._numbers(start, 3, 3)
        self._numbers(end, 3, 3)
        self._numbers([angle, thickness], 2, 2)
        self._polygon(points)
        if (start[0] == end[0] and start[1] == end[1]) or start[2] != end[2]:
            raise ValueError("Slope baseline must be nonzero and horizontal")
        if not 0 < angle < 90 or thickness <= 0:
            raise ValueError("Slope angle must be in (0,90) and thickness positive")
        return dict(start=start, end=end, points=points, angle=angle, thickness=thickness)

    def create_bim_roof_slope(self, start, end, points, angle=45, thickness=150):
        return self._roof_call("create-slopes", {"slopes": [self._slope(start, end, points, angle, thickness)]})

    def create_bim_roof_slopes(self, slopes):
        if not isinstance(slopes, (list, tuple)) or not 1 <= len(slopes) <= 32:
            raise ValueError("Supply 1 to 32 slope definitions")
        validated = []
        for slope in slopes:
            if not isinstance(slope, dict) or not {"start", "end", "points"} <= slope.keys() or slope.keys() - {"start", "end", "points", "angle", "thickness"}:
                raise ValueError("Invalid slope definition")
            validated.append(self._slope(slope["start"], slope["end"], slope["points"], slope.get("angle", 45), slope.get("thickness", 150)))
        return self._roof_call("create-slopes", {"slopes": validated})

    def _roof_contour(self, operation, handle, points, single=False):
        self._edit_handle(handle)
        if single:
            if not isinstance(points, (list, tuple)) or not 3 <= len(points) <= 200:
                raise ValueError("Contour requires 3 to 200 XYZ vertices")
            for point in points:
                self._numbers(point, 3, 3)
            self._polygon([p[:2] for p in points])
        else:
            self._polygon(points)
        return self._roof_call(operation, {"handle": handle, "points": points})

    def add_bim_roof_contour(self, handle, points):
        return self._roof_contour("roof-add", handle, points)

    def cut_bim_roof_contour(self, handle, points):
        return self._roof_contour("roof-cut", handle, points)

    def update_bim_roof_contour(self, handle, points):
        return self._roof_contour("roof-update", handle, points)

    def add_bim_roof_slope_contour(self, handle, points):
        return self._roof_contour("slope-add", handle, points, True)

    def cut_bim_roof_slope_contour(self, handle, points):
        return self._roof_contour("slope-cut", handle, points, True)

    def update_bim_roof_slope_contour(self, handle, points):
        return self._roof_contour("slope-update", handle, points, True)
