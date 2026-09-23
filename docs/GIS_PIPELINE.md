# GEOVERTEX: GIS PIPELINE SPECIFICATION
## Geospatial Architecture, CRS Management, Topology & 3D PostGIS Processing

Version: 1.0  
Status: Authoritative Architecture Specification  
Associated Documents: [MASTER_PRD.md](MASTER_PRD.md), [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 1. Geospatial Stack & Technology Boundaries

GeoVertex leverages industry-standard open-source geospatial components:
- **Spatial Storage & Indexing**: PostgreSQL + PostGIS (with GIST R-tree spatial indexes).
- **Core Geometry Engines**: GEOS, Shapely, GDAL/OGR, PyProj.
- **Point Cloud / 3D Processing**: PDAL, Open3D, Earcut.
- **Client Cartography**: MapLibre GL (2D vector tiles) and CesiumJS (3D Digital Twin globe).

---

## 2. Coordinate Reference System (CRS) Strategy

Cadastral mapping demands high geodetic accuracy. GeoVertex implements strict CRS rules:

1. **Storage Standardization (EPSG:4326)**:
   All authoritative geometries are stored in PostGIS using the WGS 84 geographic coordinate reference system (`SRID=4326`).
2. **Dynamic Projected Transforms for Geodesic Calculations**:
   Area, distance, perimeter, and volumetric calculations must never compute raw Euclidean formulas on degree coordinates. Calculations are performed either via:
   - PostGIS `geography` type casting (`ST_Area(geom::geography)`).
   - Dynamic transformation into the appropriate local projected UTM zone (e.g., EPSG:32643 / EPSG:32644 for India) or local cadastral projection using `ST_Transform(geom, target_srid)`.
3. **Metadata Retention**:
   Original survey CRS metadata is captured and preserved upon ingestion so that precision tolerances can be audited.

---

## 3. Ingestion & Spatial Normalization Pipeline

```
RAW FILE (GeoJSON, SHP, KML, GeoTIFF, LAS)
                  │
                  ▼
         Format Validation
                  │
                  ▼
        CRS Extraction & Detection
                  │
                  ▼
         Reprojection (pyproj/GDAL) ──> EPSG:4326
                  │
                  ▼
      Topology & Geometry Sanitization
       - ST_MakeValid
       - ST_RemoveRepeatedPoints
       - ST_SimplifyPreserveTopology
                  │
                  ▼
       PostGIS Authoritative Ingestion
                  │
                  ▼
         Spatial Indexing (GIST)
```

---

## 4. Topology Validation Engine (Roadmap Phase 7)

Authoritative cadastral integrity is verified using topological integrity rules:

| Check Rule | PostGIS Operation | Severity | Description |
|---|---|---|---|
| **Invalid Geometry** | `NOT ST_IsValid(geom)` | FATAL | Self-intersections, bow-tie polygons, or degenerate rings |
| **Parcel Overlap** | `ST_Overlaps(p1.geom, p2.geom)` | ERROR | No two land parcels may occupy identical surface territory |
| **Parcel Gap** | Boundary polygon intersection test | WARNING | Unaccounted gaps between adjacent boundary surveys |
| **Building Outside Parcel** | `NOT ST_CoveredBy(b.geom, p.geom)` | ERROR | Building footprint crosses or exceeds enclosing parcel bounds |
| **Floor Clashing** | $Z_{min}(f_2) < Z_{max}(f_1)$ | ERROR | Floor vertical elevation ranges must not intersect |
| **Unit Surface Clash** | `ST_3DIntersects(u1.geom, u2.geom)` | ERROR | Vertical property units must have disjoint 3D interior volumes |

---

## 5. 3D Digital Twin & 2.5D Building Extrusion Pipeline (Phase 3 Implemented)

### 5.1 Architecture & Authoritative Storage
PostGIS remains the single source of authoritative geospatial truth. 2.5D building extrusions are structured engineering representations linked to 2D building footprints:
1. **Vertical Attributes**:
   - $H_{base}$ (`base_elevation_m`): Ground surface elevation above datum.
   - $H_{roof}$ (`height_m`): Vertical building height from base to roof ridge.
   - Datum (`vertical_datum`): Explicit vertical reference datum (`WGS84_ELLIPSOID`, `EGM96_GEOID`, `LOCAL_MSL`, `GROUND_RELATIVE`).
   - Confidence (`height_confidence`): Numeric score [0.0 - 1.0] reflecting measurement certainty.
   - Source (`source`): Survey technique (`SURVEY_ELEVATION`, `LIDAR`, `PHOTOGRAMMETRY`, `SATELLITE_STEREO`, `PERMIT_DOCUMENT`, `MANUAL_ESTIMATE`).

2. **Volumetric & Metric Derivations**:
   - Footprint area is computed using PostGIS geodesic algorithms on the WGS 84 ellipsoid (`ST_Area(geometry::geography)`).
   - Volumetric capacity is calculated in cubic meters:
     $$V = A_{\text{geodesic}} \times H_{\text{roof}}$$
   - 3D Bounding Box: Computed as `[min_lon, min_lat, min_alt, max_lon, max_lat, max_alt]` with $min\_alt = H_{base}$ and $max\_alt = H_{base} + H_{roof}$.

3. **CesiumJS 3D Extrusion Protocol**:
   - Building footprints are converted into Cesium-compatible extrusion structures with exterior rings and interior hole polygons.
   - The scene endpoint (`GET /api/v1/3d/scene`) serves optimized polygon extrusions:
     - `extrudedHeight` = $H_{base} + H_{roof}$
     - `height` = $H_{base}$
     - Coordinates in EPSG:4326 (WGS84).
   - Parcel ground boundaries are served alongside extruded structures for spatial context at altitude $0.0$.

4. **Spatial Validation & Integrity**:
   - Elevation and height values are validated before persistence: $H_{roof} \ge 0$, base elevation within plausible terrestrial ranges ($-500\text{m} \dots 9000\text{m}$).
   - Footprints are checked for boundary crossings against parent cadastral parcels using `ST_CoveredBy` and `ST_Intersection`.

5. **2D/3D Dual-Viewport Synchronization**:
   - Viewport synchronization between 2D MapLibre and 3D CesiumJS is achieved via entity identifier cross-links (`building_id`, `parcel_id`) and camera fly-to routines with pitch $-45^\circ$, range $180\text{m}$, and target centering.

