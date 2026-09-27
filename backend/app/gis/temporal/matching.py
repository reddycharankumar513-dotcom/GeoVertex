import math
from typing import Any, Dict, List, Optional, Tuple
from shapely import wkt
from shapely.geometry import Polygon


class EntityMatchCandidate:
    """Represents a potential match between a historical entity and a current entity."""

    def __init__(
        self,
        historical_id: str,
        current_id: str,
        match_score: float,
        match_method: str,
        supporting_metrics: Dict[str, Any],
        requires_review: bool = False,
    ):
        self.historical_id = historical_id
        self.current_id = current_id
        self.match_score = match_score
        self.match_method = match_method
        self.supporting_metrics = supporting_metrics
        self.requires_review = requires_review

    def to_dict(self) -> Dict[str, Any]:
        return {
            "historical_id": self.historical_id,
            "current_id": self.current_id,
            "match_score": round(self.match_score, 4),
            "match_method": self.match_method,
            "supporting_metrics": self.supporting_metrics,
            "requires_review": self.requires_review,
        }


class TemporalEntityMatcher:
    """Matches historical entities with current entities using deterministic spatial and identifier signals."""

    @classmethod
    def match_entities(
        cls,
        historical_entities: List[Dict[str, Any]],
        current_entities: List[Dict[str, Any]],
        min_match_threshold: float = 0.3,
        review_threshold: float = 0.75,
    ) -> List[EntityMatchCandidate]:
        matches: List[EntityMatchCandidate] = []

        for hist in historical_entities:
            hist_id = str(hist.get("id", ""))
            hist_ref = hist.get("reference") or hist.get("number")
            hist_wkt = hist.get("geometry_wkt")
            hist_parcel_id = str(hist.get("parcel_id", ""))

            hist_geom = wkt.loads(hist_wkt) if hist_wkt else None

            best_candidate: Optional[EntityMatchCandidate] = None
            potential_candidates: List[EntityMatchCandidate] = []

            for curr in current_entities:
                curr_id = str(curr.get("id", ""))
                curr_ref = curr.get("reference") or curr.get("number")
                curr_wkt = curr.get("geometry_wkt")
                curr_parcel_id = str(curr.get("parcel_id", ""))

                # 1. Exact ID or reference match
                if hist_id and curr_id and hist_id == curr_id:
                    best_candidate = EntityMatchCandidate(
                        historical_id=hist_id,
                        current_id=curr_id,
                        match_score=1.0,
                        match_method="EXACT_ID_MATCH",
                        supporting_metrics={"reason": "UUID identical"},
                        requires_review=False,
                    )
                    break

                if hist_ref and curr_ref and str(hist_ref).strip() == str(curr_ref).strip():
                    best_candidate = EntityMatchCandidate(
                        historical_id=hist_id,
                        current_id=curr_id,
                        match_score=0.95,
                        match_method="EXACT_REFERENCE_MATCH",
                        supporting_metrics={"reference": hist_ref},
                        requires_review=False,
                    )
                    break

                # 2. Spatial IoU and Centroid Match
                curr_geom = wkt.loads(curr_wkt) if curr_wkt else None
                if hist_geom and curr_geom and not hist_geom.is_empty and not curr_geom.is_empty:
                    intersection = hist_geom.intersection(curr_geom)
                    union = hist_geom.union(curr_geom)
                    iou = (intersection.area / union.area) if union.area > 0 else 0.0

                    c_hist = hist_geom.centroid
                    c_curr = curr_geom.centroid
                    # Approximate centroid distance in degrees
                    deg_dist = math.sqrt((c_curr.x - c_hist.x) ** 2 + (c_curr.y - c_hist.y) ** 2)
                    approx_m = deg_dist * 111320.0

                    parcel_bonus = 0.1 if (hist_parcel_id and hist_parcel_id == curr_parcel_id) else 0.0
                    score = min(1.0, (iou * 0.8) + (max(0, 1.0 - (approx_m / 50.0)) * 0.2) + parcel_bonus)

                    if score >= min_match_threshold:
                        cand = EntityMatchCandidate(
                            historical_id=hist_id,
                            current_id=curr_id,
                            match_score=score,
                            match_method="SPATIAL_OVERLAP",
                            supporting_metrics={
                                "iou": round(iou, 4),
                                "centroid_dist_m": round(approx_m, 2),
                                "same_parcel": bool(parcel_bonus > 0),
                            },
                            requires_review=score < review_threshold,
                        )
                        potential_candidates.append(cand)

            if best_candidate:
                matches.append(best_candidate)
            elif potential_candidates:
                # Sort by match score descending
                potential_candidates.sort(key=lambda c: c.match_score, reverse=True)
                top = potential_candidates[0]
                # If multiple close candidates, mark as MATCH_REVIEW_REQUIRED
                if len(potential_candidates) > 1 and (potential_candidates[0].match_score - potential_candidates[1].match_score) < 0.15:
                    top.requires_review = True
                    top.match_method = "MULTIPLE_CANDIDATES_AMBIGUOUS"
                matches.append(top)

        return matches
