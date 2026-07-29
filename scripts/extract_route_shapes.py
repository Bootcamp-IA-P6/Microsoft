"""
extract_route_shapes.py
-----------------------
Extrae las polylines (shapes) de las lineas EMT que pasan por las 52 paradas in-scope.
Genera un JSON listo para usar en el frontend como GeoJSON LineStrings.

USO:
    python extract_route_shapes.py <ruta_gtfs>

Ejemplo:
    python extract_route_shapes.py ruta/a/google_transit_M6

Genera: frontend/navi_chat_v2/src/utils/routeShapes.ts
"""

import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

# Líneas in-scope (las que pasan por las 52 paradas del geofence Sol/Gran Vía)
# Usando los route_id/line codes internos de EMT (3 dígitos)
# y los labels visibles que usa el frontend
IN_SCOPE_LABELS = {
    "001", "002", "1", "2", "3", "5", "6", "9",
    "15", "17", "18", "20", "23", "26",
    "31", "32", "35", "46", "50", "51", "52", "53",
    "65", "74", "75",
    "146", "147", "148", "150",
    "M1", "M3",
    "N16", "N18", "N19", "N20", "N21", "N25", "N26",
}

# Geofence Sol/Gran Vía para filtrar solo la parte relevante
CENTER_LAT, CENTER_LON = 40.416729, -3.703339
RADIUS_KM = 1.2  # Un poco más amplio que los 600m para capturar la ruta completa


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia aproximada en km (sin math pesado)."""
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def load_routes(gtfs_path: Path) -> dict:
    """routes.txt → {route_id: route_short_name}"""
    routes = {}
    routes_file = gtfs_path / "routes.txt"
    if not routes_file.exists():
        print(f"⚠️  No se encontró {routes_file}")
        return routes
    with open(routes_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row.get("route_id", "").strip()
            short = row.get("route_short_name", "").strip()
            if rid:
                routes[rid] = short
    print(f"  routes.txt: {len(routes)} rutas cargadas")
    return routes


def load_trips(gtfs_path: Path, routes: dict) -> dict:
    """trips.txt → {shape_id: (route_id, route_label, direction_id)}
    Solo trips de líneas in-scope."""
    trips_file = gtfs_path / "trips.txt"
    if not trips_file.exists():
        print(f"⚠️  No se encontró {trips_file}")
        return {}

    shape_to_route = {}
    with open(trips_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            route_id = row.get("route_id", "").strip()
            shape_id = row.get("shape_id", "").strip()
            direction = row.get("direction_id", "0").strip()

            if not route_id or not shape_id:
                continue

            label = routes.get(route_id, route_id)

            # Filtrar solo líneas in-scope
            if label not in IN_SCOPE_LABELS and route_id not in IN_SCOPE_LABELS:
                continue

            # Quedarnos con 1 shape por route+direction (el primero encontrado)
            key = f"{label}_{direction}"
            if key not in shape_to_route:
                shape_to_route[shape_id] = (route_id, label, direction)

    print(f"  trips.txt: {len(shape_to_route)} shapes de líneas in-scope")
    return shape_to_route


def load_shapes(gtfs_path: Path, shape_ids: set) -> dict:
    """shapes.txt → {shape_id: [(lon, lat), ...]} ordenado por sequence."""
    shapes_file = gtfs_path / "shapes.txt"
    if not shapes_file.exists():
        print(f"⚠️  No se encontró {shapes_file}")
        return {}

    raw = defaultdict(list)
    with open(shapes_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row.get("shape_id", "").strip()
            if sid not in shape_ids:
                continue
            try:
                lat = float(row["shape_pt_lat"])
                lon = float(row["shape_pt_lon"])
                seq = int(row.get("shape_pt_sequence", 0))
            except (ValueError, KeyError):
                continue
            raw[sid].append((seq, lon, lat))

    # Ordenar por sequence y extraer coords
    shapes = {}
    for sid, points in raw.items():
        points.sort(key=lambda x: x[0])
        shapes[sid] = [(lon, lat) for (_, lon, lat) in points]

    print(f"  shapes.txt: {len(shapes)} shapes cargadas")
    return shapes


def filter_near_center(coords: list) -> list:
    """Filtra puntos que estén dentro del radio ampliado del geofence.
    Si la ruta pasa por la zona, recorta solo la parte cercana."""
    near = []
    in_zone = False
    for (lon, lat) in coords:
        dist = haversine_km(CENTER_LAT, CENTER_LON, lat, lon)
        if dist <= RADIUS_KM:
            in_zone = True
            near.append([lon, lat])
        elif in_zone:
            # Ya salió de la zona, agregar el último punto para cerrar
            near.append([lon, lat])
            break
    return near


def simplify_coords(coords: list, tolerance=0.00005) -> list:
    """Simplificación basica: elimina puntos casi idénticos al anterior."""
    if len(coords) <= 2:
        return coords
    result = [coords[0]]
    for i in range(1, len(coords)):
        dx = abs(coords[i][0] - result[-1][0])
        dy = abs(coords[i][1] - result[-1][1])
        if dx > tolerance or dy > tolerance:
            result.append(coords[i])
    # Siempre incluir el último
    if result[-1] != coords[-1]:
        result.append(coords[-1])
    return result


def main():
    if len(sys.argv) < 2:
        print("Uso: python extract_route_shapes.py <ruta_carpeta_gtfs>")
        print("Ejemplo: python extract_route_shapes.py C:\\Users\\under\\Downloads\\google_transit_M6")
        sys.exit(1)

    gtfs_path = Path(sys.argv[1])
    if not gtfs_path.exists():
        print(f"❌ No se encontró la carpeta: {gtfs_path}")
        sys.exit(1)

    print(f"📂 Leyendo GTFS desde: {gtfs_path}")

    # 1. Cargar routes
    routes = load_routes(gtfs_path)

    # 2. Cargar trips (filtrado por in-scope)
    shape_to_route = load_trips(gtfs_path, routes)
    if not shape_to_route:
        print("❌ No se encontraron trips de líneas in-scope")
        sys.exit(1)

    # 3. Cargar shapes
    shapes = load_shapes(gtfs_path, set(shape_to_route.keys()))

    # 4. Construir resultado: {label_direction: coords[]}
    route_shapes = {}
    for shape_id, (route_id, label, direction) in shape_to_route.items():
        if shape_id not in shapes:
            continue

        coords = shapes[shape_id]

        # Filtrar solo la parte que pasa por la zona Sol/Gran Vía
        near_coords = filter_near_center(coords)
        if len(near_coords) < 2:
            # Si no pasa por la zona, usar toda la ruta (puede ser que el geofence es estrecho)
            near_coords = coords

        # Simplificar para reducir tamaño
        simplified = simplify_coords(near_coords)

        key = f"{label}_{direction}"
        # Guardar la más larga si hay duplicados
        if key not in route_shapes or len(simplified) > len(route_shapes[key]):
            route_shapes[key] = simplified

    print(f"\n✅ {len(route_shapes)} rutas extraídas para líneas in-scope")

    # 5. Generar TypeScript
    output_path = Path(__file__).resolve().parents[1] / "frontend" / "navi_chat_v2" / "src" / "utils" / "routeShapes.ts"

    lines = ['// src/utils/routeShapes.ts']
    lines.append('// Shapes de rutas EMT in-scope — extraídas del GTFS (shapes.txt)')
    lines.append('// Generado automáticamente por scripts/extract_route_shapes.py')
    lines.append(f'// Líneas: {len(route_shapes)} rutas (label_direction)')
    lines.append('')
    lines.append('// Cada entrada: label_direction → array de [lon, lat] (GeoJSON order)')
    lines.append('export const routeShapes: Record<string, [number, number][]> = {')

    for key in sorted(route_shapes.keys()):
        coords = route_shapes[key]
        coords_str = json.dumps(coords)
        lines.append(f'  "{key}": {coords_str},')

    lines.append('};')
    lines.append('')
    lines.append('/**')
    lines.append(' * Obtener la shape de una línea como GeoJSON Feature<LineString>.')
    lines.append(' * @param label - Etiqueta visible (ej: "51", "M1", "N25")')
    lines.append(' * @param direction - 0 o 1 (dirección GTFS)')
    lines.append(' */')
    lines.append('export function getRouteShape(label: string, direction: number = 0): GeoJSON.Feature<GeoJSON.LineString> | null {')
    lines.append('  const key = `${label}_${direction}`;')
    lines.append('  const coords = routeShapes[key];')
    lines.append('  if (!coords || coords.length < 2) {')
    lines.append('    // Intentar la otra dirección')
    lines.append('    const altKey = `${label}_${direction === 0 ? 1 : 0}`;')
    lines.append('    const altCoords = routeShapes[altKey];')
    lines.append('    if (!altCoords || altCoords.length < 2) return null;')
    lines.append('    return { type: "Feature", geometry: { type: "LineString", coordinates: altCoords }, properties: {} };')
    lines.append('  }')
    lines.append('  return { type: "Feature", geometry: { type: "LineString", coordinates: coords }, properties: {} };')
    lines.append('}')
    lines.append('')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    total_points = sum(len(c) for c in route_shapes.values())
    print(f"📝 Generado: {output_path}")
    print(f"   {len(route_shapes)} rutas, {total_points} puntos totales")
    print(f"   Tamaño estimado: ~{total_points * 20 // 1024} KB")


if __name__ == "__main__":
    main()
