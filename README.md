# Video Frame Annotation Project

A portfolio project demonstrating video annotation and tracking-QA skills:
frame sampling, multi-object bounding box + action annotation, occlusion
handling, and a consistency-check pass that catches seeded tracking errors
without access to ground truth.

## Overview
- **Source:** 3 short synthetic scene videos (15s, 12fps, 640x360),
  generated programmatically with known ground-truth object positions —
  see "Why Synthetic Video" below.
- **Sampling:** every 3rd frame extracted and annotated (60 frames/video,
  180 raw frames each → 292 total object-frame detections across all
  videos and objects).
- **Task:** bounding box + object ID + action label + occlusion flag per
  object per sampled frame, plus a QA pass that flags tracking problems.

## Why Synthetic Video
There's no way to license real footage for a shareable public repo without
copyright concerns, and none was supplied for this project. Generating
short animated scenes with known physics (a bouncing ball, cars changing
lanes, a pedestrian crossing) solves that cleanly, and it has a real
benefit: because the generator knows the exact ground-truth position of
every object in every frame, the "human-style" annotations it produces are
provably accurate — which means any errors found later are either (a) real
bugs in the pipeline, or (b) the 3 errors intentionally seeded for QA
demonstration (see below). Nothing is hidden — this is disclosed here and
in `consistency_check.md`.

## Scenes
| Video | What happens |
|---|---|
| `video_01_bouncing_ball` | A ball bounces off all 4 walls (3 bounce events) |
| `video_02_traffic_lanes` | Two cars pass through frame; one performs a lane change after the other has exited |
| `video_03_pedestrian_crossing` | A person walks past a static sign while a faster car passes in front of them, causing ~9 frames of occlusion |

## Files
| File | Description |
|---|---|
| `generate_videos.py` | Builds the 3 synthetic videos + per-frame ground truth JSON |
| `videos/` | The 3 generated `.mp4` files |
| `ground_truth/` | Per-frame object positions used to generate the videos (for reproducibility/validation only — a real annotator wouldn't have this) |
| `extract_and_annotate.py` | Samples frames, extracts them as `.jpg`, builds the annotation CSV, and seeds 3 intentional QA test errors |
| `extracted_frames/` | 180 extracted `.jpg` frames (60 per video) |
| `frame_annotations.csv` | 292 object-detection rows: bbox, action, occlusion, notes |
| `frame_sequence_log.txt` | Human-readable chronological event log per video |
| `annotation_guidelines.md` | Object classes, bbox format, action vocabulary, occlusion rule, ID-persistence rule |
| `check_consistency.py` | QA script — analyzes the CSV alone (no ground truth) and flags tracking issues |
| `consistency_check.md` | Narrative write-up of what the QA script found and why |

## Results Summary
- **292** object-frame detections across **7** object tracks
- **3** intentional errors seeded (missed detection, misplaced bounding
  box, identity switch after occlusion)
- **check_consistency.py found 3 of 3** seeded errors (surfaced as 4
  findings, since one misplaced box shows up as two jump anomalies —
  in and out of the bad frame)
- **9 frames** of genuine occlusion in video 3, correctly distinguished
  from the seeded identity-switch error by cross-referencing the
  `occluded` column

## Methodology
1. Generated synthetic scenes with known physics so ground truth is exact.
2. Extracted every 3rd frame (documented sampling rate — see
   `annotation_guidelines.md` for why this matters for the "was this
   movement normal?" checks later).
3. Built annotations directly from ground truth (bbox, action derived from
   position deltas between sampled frames, occlusion from bbox overlap
   >30%).
4. Deliberately seeded 3 realistic annotation mistakes — the same logic as
   a unit test fixture — so the QA script had real issues to find.
5. Wrote `check_consistency.py` to work **only** from the delivered CSV
   (no ground truth access), matching how a real QA reviewer audits a
   vendor's annotations, and validated it against the known seeded errors.

## How to Reproduce
```bash
python3 generate_videos.py        # writes videos/ and ground_truth/
python3 extract_and_annotate.py   # writes extracted_frames/, frame_annotations.csv, frame_sequence_log.txt
python3 check_consistency.py      # writes consistency_findings.json, prints the 4 findings
```

## A Note on Repo Size
This repo includes small `.mp4` videos and `.jpg` frames (~3.4 MB total) so
the pipeline is fully self-contained and reproducible from a clone. In a
real production repo with larger or higher-resolution footage, the usual
practice is to `.gitignore` raw video/frame binaries (or use Git LFS) and
keep only the code + annotation CSVs under normal version control.

## Skills Demonstrated
- Frame extraction and sampling-rate decisions (OpenCV)
- Multi-object annotation schema design (bbox + ID + action + occlusion)
- Occlusion detection and the ID-persistence problem in video tracking
- QA methodology that works from delivered data only, validated against
  known-seeded errors (same rigor as the data-cleaning project's
  issues-log approach)
- Clear documentation: guidelines, methodology, and a reviewable findings report
