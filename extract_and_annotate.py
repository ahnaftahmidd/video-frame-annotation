"""
Extracts frames at a fixed sampling interval from each video, builds
frame_annotations.csv (object detections + action labels) and
frame_sequence_log.txt (human-readable per-frame event log).

Then deliberately seeds 3 realistic annotation mistakes into the final CSV -
a missed detection, an identity switch after occlusion, and a misplaced
bounding box - the same way a QA engineer writes test fixtures with known
issues to prove a checker actually catches something. This is disclosed
here, in the README, and in consistency_check.md; it is not hidden.
"""

import cv2
import json
import csv
import os

SAMPLE_INTERVAL = 3
VIDEOS = ["video_01_bouncing_ball", "video_02_traffic_lanes", "video_03_pedestrian_crossing"]


def bbox_center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def direction_label(dx, dy, threshold=2):
    if abs(dx) < threshold and abs(dy) < threshold:
        return "stationary"
    if abs(dx) >= abs(dy):
        return "moving_right" if dx > 0 else "moving_left"
    return "moving_down" if dy > 0 else "moving_up"


def extract_and_annotate():
    os.makedirs("extracted_frames", exist_ok=True)
    all_rows = []
    sequence_log_lines = []

    for video_id in VIDEOS:
        with open(f"ground_truth/{video_id}.json") as f:
            gt = json.load(f)
        frames = gt["frames"]

        out_dir = f"extracted_frames/{video_id}"
        os.makedirs(out_dir, exist_ok=True)

        cap = cv2.VideoCapture(f"videos/{video_id}.mp4")
        last_seen = {}
        present_ids_prev_sample = set()
        sequence_log_lines.append(f"\n=== {video_id} ===")

        frame_idx = 0
        ok, frame_img = cap.read()
        while ok:
            if frame_idx % SAMPLE_INTERVAL == 0:
                gt_frame = frames[frame_idx]
                frame_filename = f"{video_id}_frame_{frame_idx:04d}.jpg"
                cv2.imwrite(os.path.join(out_dir, frame_filename), frame_img)

                present_ids_this_sample = set()
                objects_summary = []
                events_summary = []

                for obj in gt_frame["objects"]:
                    oid = obj["id"]
                    present_ids_this_sample.add(oid)
                    cx, cy = bbox_center(obj["bbox"])

                    if oid not in last_seen:
                        action = "entering_frame"
                    else:
                        _, (pcx, pcy) = last_seen[oid]
                        dx, dy = cx - pcx, cy - pcy
                        action = direction_label(dx, dy)
                        if obj.get("event") == "lane_change":
                            action = "lane_change"
                        elif obj.get("event") and "bounced" in obj["event"]:
                            action = obj["event"]

                    last_seen[oid] = (frame_idx, (cx, cy))

                    all_rows.append({
                        "video_id": video_id, "frame_number": frame_idx,
                        "timestamp_sec": gt_frame["timestamp"],
                        "object_id": oid, "object_type": obj["type"],
                        "bbox_x1": obj["bbox"][0], "bbox_y1": obj["bbox"][1],
                        "bbox_x2": obj["bbox"][2], "bbox_y2": obj["bbox"][3],
                        "action": action, "occluded": obj["occluded"],
                        "annotator_notes": "",
                    })
                    tag = f"{oid}({obj['type']})" + (" [occluded]" if obj["occluded"] else "")
                    objects_summary.append(tag)
                    if obj.get("event"):
                        events_summary.append(f"{oid}: {obj['event']}")

                for oid in present_ids_prev_sample - present_ids_this_sample:
                    events_summary.append(f"{oid}: exited_frame")

                log_line = (f"[frame {frame_idx:04d}] t={gt_frame['timestamp']:.2f}s | "
                            f"objects: {', '.join(objects_summary) if objects_summary else '-'} | "
                            f"events: {', '.join(events_summary) if events_summary else '-'}")
                sequence_log_lines.append(log_line)
                present_ids_prev_sample = present_ids_this_sample

            frame_idx += 1
            ok, frame_img = cap.read()
        cap.release()

    return all_rows, sequence_log_lines


def inject_realistic_annotation_errors(rows):
    """Deliberately seeds 3 realistic mistakes for the QA script to catch."""
    # Error 1: missed detection - drop ball_1 at frame 90 despite being clearly visible
    rows = [r for r in rows if not (r["video_id"] == "video_01_bouncing_ball"
                                     and r["object_id"] == "ball_1"
                                     and r["frame_number"] == 90)]

    # Error 2: identity switch after occlusion clears - person_1 relabeled person_2
    occluded_frames = [r["frame_number"] for r in rows
                        if r["video_id"] == "video_03_pedestrian_crossing"
                        and r["object_id"] == "person_1" and r["occluded"]]
    if occluded_frames:
        last_occluded_frame = max(occluded_frames)
        for r in rows:
            if (r["video_id"] == "video_03_pedestrian_crossing"
                    and r["object_id"] == "person_1"
                    and r["frame_number"] > last_occluded_frame):
                r["object_id"] = "person_2"

    # Error 3: misplaced bounding box (simulated misclick) on one frame
    for r in rows:
        if (r["video_id"] == "video_02_traffic_lanes"
                and r["object_id"] == "car_B" and r["frame_number"] == 60):
            r["bbox_x1"] += 180
            r["bbox_x2"] += 180
            r["bbox_y1"] -= 90
            r["bbox_y2"] -= 90
            break

    return rows


def main():
    all_rows, sequence_log_lines = extract_and_annotate()
    print(f"Extracted {len(all_rows)} object-frame detections before error injection")

    all_rows = inject_realistic_annotation_errors(all_rows)
    print(f"{len(all_rows)} rows after seeding 3 intentional QA test errors")

    fieldnames = ["video_id", "frame_number", "timestamp_sec", "object_id", "object_type",
                  "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "action", "occluded", "annotator_notes"]
    with open("frame_annotations.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    with open("frame_sequence_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sequence_log_lines).strip() + "\n")

    print("Wrote frame_annotations.csv and frame_sequence_log.txt")


if __name__ == "__main__":
    main()
