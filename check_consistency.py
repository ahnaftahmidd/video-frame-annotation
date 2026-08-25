"""
Analyzes frame_annotations.csv for temporal consistency issues - working
only from the delivered annotations, the way a real QA reviewer would (no
access to ground truth). Detects three issue types:

  1. temporal_gap            - an object's track has a gap larger than the
                                expected sampling interval
  2. bounding_box_jump       - an object's box moves far more than its own
                                typical frame-to-frame displacement
  3. possible_identity_switch - a track ends and a same-type track begins
                                 shortly after, very close in position -
                                 likely the same physical object re-IDed

Writes consistency_findings.json with the raw results.
"""

import csv
import json
import math
from collections import defaultdict

SAMPLE_INTERVAL = 3


def load_rows():
    with open("frame_annotations.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["frame_number"] = int(r["frame_number"])
        r["bbox_x1"] = float(r["bbox_x1"])
        r["bbox_y1"] = float(r["bbox_y1"])
        r["bbox_x2"] = float(r["bbox_x2"])
        r["bbox_y2"] = float(r["bbox_y2"])
        r["occluded"] = r["occluded"] in ("True", "true", "1")
    return rows


def center(r):
    return ((r["bbox_x1"] + r["bbox_x2"]) / 2, (r["bbox_y1"] + r["bbox_y2"]) / 2)


def build_tracks(rows):
    tracks = defaultdict(list)
    for r in rows:
        tracks[(r["video_id"], r["object_id"])].append(r)
    for k in tracks:
        tracks[k].sort(key=lambda r: r["frame_number"])
    return tracks


def check_temporal_gaps(tracks):
    findings = []
    for (video_id, object_id), track_rows in tracks.items():
        for i in range(1, len(track_rows)):
            gap = track_rows[i]["frame_number"] - track_rows[i - 1]["frame_number"]
            if gap > SAMPLE_INTERVAL:
                n_missing = gap // SAMPLE_INTERVAL - 1
                findings.append({
                    "type": "temporal_gap", "severity": "medium",
                    "video_id": video_id, "object_id": object_id,
                    "frame_before": track_rows[i - 1]["frame_number"],
                    "frame_after": track_rows[i]["frame_number"],
                    "description": (f"{object_id} has {n_missing} expected sampled frame(s) missing "
                                     f"between frame {track_rows[i-1]['frame_number']} and "
                                     f"{track_rows[i]['frame_number']}. Likely a missed detection - "
                                     f"verify against the source video."),
                })
    return findings


def check_bbox_jumps(tracks):
    findings = []
    for (video_id, object_id), track_rows in tracks.items():
        if len(track_rows) < 3:
            continue
        displacements = []
        for i in range(1, len(track_rows)):
            d = math.dist(center(track_rows[i - 1]), center(track_rows[i]))
            displacements.append(d)
        median_disp = sorted(displacements)[len(displacements) // 2]
        threshold = max(3 * median_disp, 40)
        for i, d in enumerate(displacements):
            if d > threshold:
                findings.append({
                    "type": "bounding_box_jump", "severity": "high",
                    "video_id": video_id, "object_id": object_id,
                    "frame_before": track_rows[i]["frame_number"],
                    "frame_after": track_rows[i + 1]["frame_number"],
                    "description": (f"{object_id} bounding box moved {d:.0f}px between frame "
                                     f"{track_rows[i]['frame_number']} and {track_rows[i+1]['frame_number']}, "
                                     f"vs a typical step of {median_disp:.0f}px for this object. "
                                     f"Likely a mislabeled/misplaced box - verify manually."),
                })
    return findings


def check_identity_switches(tracks):
    findings = []
    by_video_type = defaultdict(list)
    for (video_id, object_id), track_rows in tracks.items():
        by_video_type[(video_id, track_rows[0]["object_type"])].append((object_id, track_rows))

    for (video_id, obj_type), id_tracks in by_video_type.items():
        for id_a, rows_a in id_tracks:
            end_frame = rows_a[-1]["frame_number"]
            end_center = center(rows_a[-1])
            for id_b, rows_b in id_tracks:
                if id_a == id_b:
                    continue
                start_frame = rows_b[0]["frame_number"]
                if start_frame <= end_frame or (start_frame - end_frame) > SAMPLE_INTERVAL * 3:
                    continue
                dist = math.dist(end_center, center(rows_b[0]))
                if dist < 60:
                    findings.append({
                        "type": "possible_identity_switch", "severity": "high",
                        "video_id": video_id, "object_id": f"{id_a} -> {id_b}",
                        "frame_before": end_frame, "frame_after": start_frame,
                        "description": (f"Track '{id_a}' ({obj_type}) ends at frame {end_frame}, and a new "
                                         f"track '{id_b}' of the same type begins at frame {start_frame}, "
                                         f"only {dist:.0f}px away. Likely the same physical object re-IDed - "
                                         f"check for an occlusion event around these frames."),
                    })
    return findings


def main():
    rows = load_rows()
    tracks = build_tracks(rows)

    findings = (check_temporal_gaps(tracks)
                + check_bbox_jumps(tracks)
                + check_identity_switches(tracks))
    findings.sort(key=lambda f: (f["video_id"], f["frame_before"]))

    with open("consistency_findings.json", "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)

    print(f"Analyzed {len(rows)} rows across {len(tracks)} object tracks")
    print(f"Found {len(findings)} issues:\n")
    for finding in findings:
        print(f"[{finding['severity'].upper()}] {finding['type']} - {finding['video_id']} - {finding['object_id']}")
        print(f"  {finding['description']}\n")


if __name__ == "__main__":
    main()
