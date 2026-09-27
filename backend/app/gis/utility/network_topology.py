"""Utility network topology validation, graph representation, and connectivity engine."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from shapely import wkt
from shapely.geometry import Point, LineString


@dataclass
class TopologyIssue:
    issue_code: str
    severity: str
    entity_id: str
    entity_type: str
    message: str
    technical_details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_code": self.issue_code,
            "severity": self.severity,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "message": self.message,
            "technical_details": self.technical_details,
        }


class UtilityNetworkTopologyEngine:
    """Validates and analyzes network topology for linear utility segments and nodes."""

    @staticmethod
    def validate_network(
        nodes: List[Dict[str, Any]],
        segments: List[Dict[str, Any]],
        endpoint_tolerance_m: float = 0.1,
    ) -> Dict[str, Any]:
        """Validate network topology and return issues and graph connectivity statistics.
        
        nodes: list of dicts with 'id', 'geometry_wkt' or ('longitude', 'latitude')
        segments: list of dicts with 'id', 'start_node_id', 'end_node_id', 'geometry_wkt'
        """
        issues: List[TopologyIssue] = []
        node_map = {str(n["id"]): n for n in nodes}
        node_connections: Dict[str, List[str]] = defaultdict(list)
        segment_endpoints: Dict[str, Tuple[Point, Point]] = {}

        # 1. Parse segment geometries and map connections
        for seg in segments:
            seg_id = str(seg["id"])
            start_nid = str(seg.get("start_node_id") or "")
            end_nid = str(seg.get("end_node_id") or "")

            if start_nid and start_nid in node_map:
                node_connections[start_nid].append(seg_id)
            if end_nid and end_nid in node_map:
                node_connections[end_nid].append(seg_id)

            geom_wkt = seg.get("geometry_wkt")
            if geom_wkt:
                try:
                    line = wkt.loads(geom_wkt)
                    if isinstance(line, LineString) and len(line.coords) >= 2:
                        p_start = Point(line.coords[0])
                        p_end = Point(line.coords[-1])
                        segment_endpoints[seg_id] = (p_start, p_end)
                    else:
                        issues.append(TopologyIssue(
                            issue_code="UTILITY_INVALID_GEOMETRY",
                            severity="ERROR",
                            entity_id=seg_id,
                            entity_type="UTILITY_SEGMENT",
                            message=f"Segment {seg_id} does not have valid LineString geometry.",
                            technical_details={"wkt": geom_wkt},
                        ))
                except Exception as e:
                    issues.append(TopologyIssue(
                        issue_code="UTILITY_MALFORMED_WKT",
                        severity="ERROR",
                        entity_id=seg_id,
                        entity_type="UTILITY_SEGMENT",
                        message=f"Failed to parse geometry for segment {seg_id}: {str(e)}",
                        technical_details={"wkt": geom_wkt},
                    ))

        # 2. Check for duplicate or overlapping segments
        seen_pairs: Dict[Tuple[str, str], str] = {}
        for seg in segments:
            seg_id = str(seg["id"])
            s_node = str(seg.get("start_node_id") or "")
            e_node = str(seg.get("end_node_id") or "")

            if s_node and e_node:
                canonical_pair = tuple(sorted([s_node, e_node]))
                if canonical_pair in seen_pairs:
                    other_id = seen_pairs[canonical_pair]
                    issues.append(TopologyIssue(
                        issue_code="UTILITY_DUPLICATE_SEGMENT",
                        severity="WARNING",
                        entity_id=seg_id,
                        entity_type="UTILITY_SEGMENT",
                        message=f"Segment {seg_id} connects the same nodes ({s_node} <-> {e_node}) as segment {other_id}.",
                        technical_details={"duplicate_of": other_id, "nodes": list(canonical_pair)},
                    ))
                else:
                    seen_pairs[canonical_pair] = seg_id

        # 3. Check for orphan / unconnected nodes
        for node in nodes:
            nid = str(node["id"])
            conns = node_connections.get(nid, [])
            if len(conns) == 0:
                issues.append(TopologyIssue(
                    issue_code="UTILITY_NODE_WITHOUT_CONNECTION",
                    severity="WARNING",
                    entity_id=nid,
                    entity_type="UTILITY_NODE",
                    message=f"Utility node {nid} ({node.get('node_type', 'NODE')}) has no connected segments.",
                    technical_details={"node_type": node.get("node_type")},
                ))

        # 4. Check for dangling endpoints and node alignment
        for seg in segments:
            seg_id = str(seg["id"])
            start_nid = str(seg.get("start_node_id") or "")
            end_nid = str(seg.get("end_node_id") or "")

            if seg_id in segment_endpoints:
                p_start, p_end = segment_endpoints[seg_id]

                # Check start node
                if not start_nid or start_nid not in node_map:
                    issues.append(TopologyIssue(
                        issue_code="UTILITY_DANGLING_ENDPOINT",
                        severity="INFO",
                        entity_id=seg_id,
                        entity_type="UTILITY_SEGMENT",
                        message=f"Segment {seg_id} start endpoint is not anchored to a known node.",
                        technical_details={"endpoint": "start", "coord": [p_start.x, p_start.y]},
                    ))
                else:
                    # Verify spatial proximity to node
                    n_geom_wkt = node_map[start_nid].get("geometry_wkt")
                    if n_geom_wkt:
                        try:
                            n_pt = wkt.loads(n_geom_wkt)
                            if isinstance(n_pt, Point):
                                dist = p_start.distance(n_pt)
                                if dist > 0.0001:  # Roughly > 10m in degrees if not projected
                                    issues.append(TopologyIssue(
                                        issue_code="UTILITY_INVALID_CONNECTION",
                                        severity="WARNING",
                                        entity_id=seg_id,
                                        entity_type="UTILITY_SEGMENT",
                                        message=f"Segment {seg_id} start coord does not coincide with start node {start_nid}.",
                                        technical_details={"distance_deg": dist},
                                    ))
                        except Exception:
                            pass

                # Check end node
                if not end_nid or end_nid not in node_map:
                    issues.append(TopologyIssue(
                        issue_code="UTILITY_DANGLING_ENDPOINT",
                        severity="INFO",
                        entity_id=seg_id,
                        entity_type="UTILITY_SEGMENT",
                        message=f"Segment {seg_id} end endpoint is not anchored to a known node.",
                        technical_details={"endpoint": "end", "coord": [p_end.x, p_end.y]},
                    ))

        # 5. Connected components (Graph BFS)
        adj: Dict[str, Set[str]] = defaultdict(set)
        for seg in segments:
            s_node = str(seg.get("start_node_id") or "")
            e_node = str(seg.get("end_node_id") or "")
            if s_node and e_node:
                adj[s_node].add(e_node)
                adj[e_node].add(s_node)

        visited: Set[str] = set()
        components: List[List[str]] = []
        for nid in node_map:
            if nid not in visited and nid in adj:
                comp = []
                queue = [nid]
                visited.add(nid)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                components.append(comp)

        if len(components) > 1:
            for i, comp in enumerate(components[1:], start=2):
                issues.append(TopologyIssue(
                    issue_code="UTILITY_DISCONNECTED_NETWORK_ISLAND",
                    severity="WARNING",
                    entity_id=comp[0],
                    entity_type="UTILITY_NETWORK",
                    message=f"Network component #{i} with {len(comp)} nodes is disconnected from the main trunk.",
                    technical_details={"component_size": len(comp), "nodes": comp[:5]},
                ))

        return {
            "is_valid": len([i for i in issues if i.severity in ("CRITICAL", "ERROR")]) == 0,
            "total_issues": len(issues),
            "critical_errors": len([i for i in issues if i.severity == "CRITICAL"]),
            "errors": len([i for i in issues if i.severity == "ERROR"]),
            "warnings": len([i for i in issues if i.severity == "WARNING"]),
            "info": len([i for i in issues if i.severity == "INFO"]),
            "issues": [i.to_dict() for i in issues],
            "total_nodes": len(nodes),
            "total_segments": len(segments),
            "connected_components_count": len(components),
        }
