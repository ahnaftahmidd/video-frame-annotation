# Consistency Check Report

`check_consistency.py` analyzes `frame_annotations.csv` **only** — it has no
access to ground truth, the same constraint a real QA reviewer would have
when auditing a vendor's delivered annotations. It found all 3 issues that
were deliberately seeded into the dataset (see `extract_and_annotate.py`,
function `inject_realistic_annotation_errors`), plus correctly reported one
of them as two related findings.

## Summary

| Metric | Value |
|---|---|
| Rows analyzed | 292 |
| Object tracks analyzed | 7 |
| Issues found | 4 |
| Ground-truth errors seeded | 3 |
| Errors detected | 3 of 3 (100%) |

## Findings

### 1. Temporal Gap — `ball_1`, video_01_bouncing_ball
> ball_1 has 1 expected sampled frame missing between frame 87 and 93.

**Root cause:** the ball's detection at frame 90 was deliberately dropped
(simulating a human annotator missing an obviously-visible object on one
frame). **Severity:** medium — a single missing frame in an otherwise
continuous track is a strong signal of a missed detection rather than a
real disappearance, since nothing in the scene explains the ball vanishing
for one frame and reappearing on the next.

### 2 & 3. Bounding Box Jump — `car_B`, video_02_traffic_lanes (two findings)
> car_B bounding box moved 185px between frame 57 and 60 (typical step: 18px)
> car_B bounding box moved 217px between frame 60 and 63 (typical step: 18px)

**Root cause:** car_B's box was deliberately shifted by a large offset at
exactly frame 60 (simulating an annotator misclick). Because the check
compares every consecutive pair, one bad frame shows up as **two**
anomalies — a large jump *into* frame 60, then a large jump *back out* of
it at frame 63. This pattern (two flagged jumps that roughly cancel out
in position) is itself a useful diagnostic: it points at a single bad
frame rather than a sustained tracking failure. **Severity:** high — a
185–217px jump against an 18px typical step is unambiguous.

### 4. Possible Identity Switch — `person_1 → person_2`, video_03_pedestrian_crossing
> Track 'person_1' ends at frame 90, and a new track 'person_2' begins at
> frame 93, only 12px away.

**Root cause:** the person's ID was deliberately relabeled from `person_1`
to `person_2` for every frame after their occlusion by `car_C` cleared
(occlusion was active frames 84–90; see `frame_annotations.csv`,
`occluded` column). This is the exact real-world failure mode described in
`annotation_guidelines.md`: an object briefly hidden behind another gets a
new ID when it reappears instead of keeping its original one.
**Severity:** high — a 12px position gap across only 3 frames, for the
same object type, immediately after an occlusion event, is very unlikely
to be two different physical objects.

## What a Reviewer Would Do With This Report
1. **Ball frame 90:** pull up the source frame, confirm the ball is visible,
   add the missing detection.
2. **Car_B frame 60:** pull up the source frame, re-draw the bounding box
   in the correct position.
3. **Person_1/person_2:** merge the two IDs into one continuous track
   (`person_1`) across the occlusion, and flag the annotator/tool for
   retraining on the ID-persistence rule in `annotation_guidelines.md`.

## Why Seed Errors on Purpose
A QA script that's only ever run against clean data doesn't prove it works
— it might just never have anything to catch. Seeding known issues and
confirming the script finds exactly those issues (and nothing else) is the
same logic as a unit test: it demonstrates the tool actually does its job,
not just that it runs without crashing.
