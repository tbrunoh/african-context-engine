"""Small, dependency free geometry: distances, point in polygon, centroids and line simplification.

Coordinates are (lat, lon) pairs in degrees everywhere in ACE.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

Point = tuple[float, float]
Ring = Sequence[Sequence[float]]


def haversine_km(a: Sequence[float], b: Sequence[float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(min(1.0, h)))


def in_ring(point: Sequence[float], ring: Ring) -> bool:
    """Ray casting test. The ring is a list of (lat, lon); it need not repeat its first point."""
    y, x = point[0], point[1]
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        yi, xi = ring[i][0], ring[i][1]
        yj, xj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def in_polygons(point: Sequence[float], rings: Sequence[Ring]) -> bool:
    """True when the point falls inside an odd number of rings, so holes are respected."""
    return sum(in_ring(point, r) for r in rings) % 2 == 1


def bbox(rings: Sequence[Ring]) -> tuple[float, float, float, float]:
    lats = [p[0] for r in rings for p in r]
    lons = [p[1] for r in rings for p in r]
    return min(lats), min(lons), max(lats), max(lons)


def in_bbox(point: Sequence[float], box: Sequence[float], pad: float = 0.0) -> bool:
    return box[0] - pad <= point[0] <= box[2] + pad and box[1] - pad <= point[1] <= box[3] + pad


def ring_area_centroid(ring: Ring) -> tuple[float, float, float]:
    """Signed area and centroid of a ring in degree space; fine for picking a representative point."""
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n):
        y0, x0 = ring[i][0], ring[i][1]
        y1, x1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a /= 2
    if abs(a) < 1e-12:
        return 0.0, sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n
    return a, cy / (6 * a), cx / (6 * a)


def centroid(rings: Sequence[Ring]) -> Point:
    """Area weighted centroid of the outer rings. When it falls outside the shape, the
    nearest vertex of the largest ring is used instead, so the point is always inside or on it."""
    parts = [ring_area_centroid(r) for r in rings if len(r) >= 3]
    total = sum(abs(a) for a, _, _ in parts) or 1.0
    lat = sum(abs(a) * y for a, y, _ in parts) / total
    lon = sum(abs(a) * x for a, _, x in parts) / total
    if parts and not in_polygons((lat, lon), rings):
        largest = max((r for r in rings if len(r) >= 3), key=lambda r: abs(ring_area_centroid(r)[0]))
        lat, lon = min(largest, key=lambda p: (p[0] - lat) ** 2 + (p[1] - lon) ** 2)[:2]
    return round(lat, 4), round(lon, 4)


def simplify(ring: Ring, tolerance: float) -> list[list[float]]:
    """Douglas Peucker simplification in degree space, iterative so large rings do not hit the recursion limit."""
    pts = [list(p[:2]) for p in ring]
    if len(pts) < 4:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        start, end = stack.pop()
        (y1, x1), (y2, x2) = pts[start], pts[end]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy)
        best, index = -1.0, -1
        for i in range(start + 1, end):
            y0, x0 = pts[i]
            if norm < 1e-12:  # closed ring: the segment is a single point
                d = math.hypot(x0 - x1, y0 - y1)
            else:
                d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / norm
            if d > best:
                best, index = d, i
        if best > tolerance and index > 0:
            keep[index] = True
            stack.extend([(start, index), (index, end)])
    return [pts[i] for i in range(len(pts)) if keep[i]]


def distance_to_rings_km(point: Sequence[float], rings: Sequence[Ring]) -> float:
    """Approximate distance from a point to the nearest edge of a shape, in kilometres."""
    lat0 = math.radians(point[0])
    kx, ky = 111.32 * math.cos(lat0), 110.57
    px, py = point[1] * kx, point[0] * ky
    best = float("inf")
    for ring in rings:
        for i in range(len(ring)):
            ax, ay = ring[i - 1][1] * kx, ring[i - 1][0] * ky
            bx, by = ring[i][1] * kx, ring[i][0] * ky
            vx, vy = bx - ax, by - ay
            seg = vx * vx + vy * vy
            t = 0.0 if seg == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / seg))
            best = min(best, math.hypot(px - (ax + t * vx), py - (ay + t * vy)))
    return best
