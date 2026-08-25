"""
Generates 3 short synthetic scene videos with known ground-truth object
positions for every frame (saved to ground_truth/*.json).

Why synthetic video: there's no way to license/download real video footage
for a public portfolio repo without copyright concerns, and no real video
was supplied for this project. Generating simple animated scenes (moving
shapes with known physics) solves that cleanly - and as a bonus, gives us
exact ground truth to validate the downstream annotation + QA pipeline
against, the same way a unit test uses known-good fixtures.

Scenes:
  1. video_01_bouncing_ball    - single ball bouncing inside a frame
  2. video_02_traffic_lanes    - two cars, one performs a lane change
  3. video_03_pedestrian_crossing - person + static sign + a car that
                                     passes in front of the person,
                                     causing a temporary occlusion
"""

import cv2
import numpy as np
import json
import os

W, H = 640, 360
FPS = 12
DURATION_SEC = 15
TOTAL_FRAMES = FPS * DURATION_SEC  # 180

os.makedirs("videos", exist_ok=True)
os.makedirs("ground_truth", exist_ok=True)


def save_ground_truth(video_id, frames_gt):
    with open(f"ground_truth/{video_id}.json", "w") as f:
        json.dump({"video_id": video_id, "width": W, "height": H, "fps": FPS, "frames": frames_gt}, f, indent=2)


def new_writer(video_id):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(f"videos/{video_id}.mp4", fourcc, FPS, (W, H))


# ---------------- VIDEO 1: bouncing ball ----------------
def generate_video_01():
    video_id = "video_01_bouncing_ball"
    r = 15
    x, y = 40.0, 40.0
    vx, vy = 6.0, 4.0
    writer = new_writer(video_id)
    frames_gt = []

    for t in range(TOTAL_FRAMES):
        event = None
        x += vx
        y += vy
        if x - r < 0:
            x, vx, event = r, -vx, "bounced_off_left_wall"
        elif x + r > W:
            x, vx, event = W - r, -vx, "bounced_off_right_wall"
        if y - r < 0:
            y, vy, event = r, -vy, "bounced_off_top_wall"
        elif y + r > H:
            y, vy, event = H - r, -vy, "bounced_off_bottom_wall"

        img = np.full((H, W, 3), (245, 245, 245), dtype=np.uint8)
        cv2.rectangle(img, (5, 5), (W - 5, H - 5), (180, 180, 180), 2)
        cv2.circle(img, (int(x), int(y)), r, (60, 120, 220), -1)
        writer.write(img)

        frames_gt.append({
            "frame": t, "timestamp": round(t / FPS, 2),
            "objects": [{
                "id": "ball_1", "type": "ball",
                "bbox": [int(x - r), int(y - r), int(x + r), int(y + r)],
                "occluded": False, "event": event,
            }],
        })
    writer.release()
    save_ground_truth(video_id, frames_gt)
    print(f"Generated {video_id}: {TOTAL_FRAMES} frames")


# ---------------- VIDEO 2: two-lane traffic, one lane change ----------------
def generate_video_02():
    video_id = "video_02_traffic_lanes"
    writer = new_writer(video_id)

    car_w, car_h = 50, 25
    top_lane_y, bottom_lane_y = 130, 205
    # Scheduled after car_B has exited (~frame 125) and while car_A is still
    # comfortably on screen, so the lane-change is actually visible.
    lane_change_start, lane_change_end = 135, 150

    ax, ay = -60.0, float(top_lane_y)
    avx = 3.0
    bx, by = 700.0, float(bottom_lane_y)
    bvx = -6.0

    frames_gt = []
    for t in range(TOTAL_FRAMES):
        ax += avx
        bx += bvx

        event_a = None
        if lane_change_start <= t <= lane_change_end:
            progress = (t - lane_change_start) / (lane_change_end - lane_change_start)
            ay = top_lane_y + (bottom_lane_y - top_lane_y) * progress
            event_a = "lane_change"
        elif t > lane_change_end:
            ay = float(bottom_lane_y)

        img = np.full((H, W, 3), (200, 235, 200), dtype=np.uint8)
        cv2.rectangle(img, (0, 110), (W, 240), (90, 90, 90), -1)
        for dashx in range(0, W, 40):
            cv2.line(img, (dashx, 175), (dashx + 20, 175), (230, 230, 230), 2)

        a_visible = (ax + car_w > 0) and (ax < W)
        b_visible = (bx + car_w > 0) and (bx < W)
        objects = []

        if a_visible:
            cv2.rectangle(img, (int(ax), int(ay)), (int(ax + car_w), int(ay + car_h)), (40, 60, 200), -1)
            objects.append({"id": "car_A", "type": "car",
                             "bbox": [int(ax), int(ay), int(ax + car_w), int(ay + car_h)],
                             "occluded": False, "event": event_a})
        if b_visible:
            cv2.rectangle(img, (int(bx), int(by)), (int(bx + car_w), int(by + car_h)), (200, 60, 40), -1)
            objects.append({"id": "car_B", "type": "car",
                             "bbox": [int(bx), int(by), int(bx + car_w), int(by + car_h)],
                             "occluded": False, "event": None})

        writer.write(img)
        frames_gt.append({"frame": t, "timestamp": round(t / FPS, 2), "objects": objects})

    writer.release()
    save_ground_truth(video_id, frames_gt)
    print(f"Generated {video_id}: {TOTAL_FRAMES} frames")


# ---------------- VIDEO 3: pedestrian crossing with occlusion ----------------
def generate_video_03():
    video_id = "video_03_pedestrian_crossing"
    writer = new_writer(video_id)

    sign_bbox = [20, 20, 50, 70]
    px, py = 0.0, 180.0
    pvx = 4.0
    person_w, person_h = 20, 40
    cx, cy = -540.0, 170.0
    cvx = 10.0
    car_w, car_h = 60, 28

    def overlap_ratio(box_a, box_b):
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        area_a = (ax2 - ax1) * (ay2 - ay1)
        return inter / area_a if area_a > 0 else 0.0

    frames_gt = []
    for t in range(TOTAL_FRAMES):
        px += pvx
        cx += cvx

        img = np.full((H, W, 3), (225, 225, 225), dtype=np.uint8)
        cv2.rectangle(img, (0, 150), (W, 250), (110, 110, 110), -1)
        for stripe_x in range(10, W, 45):
            cv2.rectangle(img, (stripe_x, 160), (stripe_x + 20, 240), (240, 240, 240), -1)
        cv2.rectangle(img, tuple(sign_bbox[:2]), tuple(sign_bbox[2:]), (30, 140, 30), -1)

        person_bbox = [int(px), int(py), int(px + person_w), int(py + person_h)]
        car_bbox = [int(cx), int(cy), int(cx + car_w), int(cy + car_h)]
        person_visible = (px + person_w > 0) and (px < W)
        car_visible = (cx + car_w > 0) and (cx < W)
        overlap = overlap_ratio(person_bbox, car_bbox) if (person_visible and car_visible) else 0.0
        person_occluded = overlap > 0.3

        if person_visible:
            head = (int(px + person_w / 2), int(py + 8))
            cv2.circle(img, head, 8, (210, 170, 140), -1)
            cv2.rectangle(img, (int(px + 2), int(py + 14)), (int(px + person_w - 2), int(py + person_h)), (80, 80, 200), -1)
        if car_visible:
            cv2.rectangle(img, (int(cx), int(cy)), (int(cx + car_w), int(cy + car_h)), (40, 170, 210), -1)

        objects = [{"id": "sign_1", "type": "sign", "bbox": sign_bbox, "occluded": False, "event": None}]
        if person_visible:
            objects.append({"id": "person_1", "type": "person", "bbox": person_bbox,
                             "occluded": bool(person_occluded), "event": None})
        if car_visible:
            objects.append({"id": "car_C", "type": "car", "bbox": car_bbox, "occluded": False, "event": None})

        writer.write(img)
        frames_gt.append({"frame": t, "timestamp": round(t / FPS, 2), "objects": objects})

    writer.release()
    save_ground_truth(video_id, frames_gt)
    print(f"Generated {video_id}: {TOTAL_FRAMES} frames")


if __name__ == "__main__":
    generate_video_01()
    generate_video_02()
    generate_video_03()
