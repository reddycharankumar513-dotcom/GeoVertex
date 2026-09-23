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

## 5. 3D Digital Twin Generation (Roadmap Phase 3 & 4)

1. **2D to 3D Extrusion**:
   Building footprints with height attributes ($H_{base}, H_{roof}$) are extruded into 3D polyhedral geometries (`ST_Extrude(footprint, 0, 0, height)`).
2. **Floor Slicing**:
   Elevations $Z_0 \dots Z_n$ define bounded volumetric prisms for each floor level.
3. **CesiumJS Integration**:
   API exposes 3D geometries as GeoJSON with height properties or batched 3D Tiles (b3dm), enabling photorealistic rendering with terrain elevation models and camera clipping planes.
