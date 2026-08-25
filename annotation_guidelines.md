# Video Frame Annotation Guidelines

## Object Classes
| Class | Description |
|---|---|
| `ball` | Single moving sphere (video 1) |
| `car` | Vehicle rectangle (videos 2 and 3) |
| `person` | Simple head + torso figure (video 3) |
| `sign` | Static reference object, never moves (video 3) |

## Bounding Box Format
`[x1, y1, x2, y2]` in pixel coordinates, origin top-left, `x2 > x1` and
`y2 > y1`. The box should tightly enclose the object's visible extent for
that frame — not its full extent if partially occluded or off-screen.

## Frame Sampling
Every 3rd frame is annotated (source video is 12 fps, so annotations are
effectively at 4 fps). Annotating every single frame is rarely worth the
cost in real pipelines — consecutive frames at typical frame rates are
near-duplicates for a labeling task like this one. Always record the
sampling interval explicitly in project docs, since it changes what counts
as a normal vs. abnormal frame-to-frame position change (see `action` below).

## Action Vocabulary
| Action | Meaning |
|---|---|
| `entering_frame` | First sampled frame this object is visible |
| `exiting_frame` | Logged in the sequence log (not the CSV) when an object was present last sample and absent this sample |
| `moving_left` / `moving_right` / `moving_up` / `moving_down` | Dominant direction of motion since the previous sampled frame |
| `stationary` | Displacement below threshold (2px) since previous sampled frame |
| `bounced_off_<wall>` | Object's velocity reversed off a frame edge since the previous sampled frame |
| `lane_change` | Object is mid-transition between two fixed lane positions |

Direction is computed from the bounding box center's displacement between
this sampled frame and the object's previous sampled frame — not from
every raw frame, since the annotator (and this pipeline) only ever sees
the sampled frames.

## Occlusion Tagging
`occluded = True` when another object's bounding box covers more than
**30% of this object's box area** in the same frame. This is a fixed,
checkable rule rather than a subjective call, so two annotators (or an
annotator and a QA reviewer) should agree on it consistently.

## Object ID Persistence — the rule that matters most
An object keeps the **same ID** for its entire time in the scene, including
across occlusion. A new ID should only be assigned to a genuinely new
object entering the scene — never to the same physical object reappearing
after being temporarily hidden.

This is the single most common real-world video annotation mistake: an
object gets occluded, and when it reappears, either a human annotator or an
automated tracker assigns it a new ID because it "looks like a new
detection." This project's dataset deliberately contains one such error
(see `consistency_check.md`) specifically to demonstrate why this rule
exists and how a QA pass catches it.

## What a Reviewer Should Flag
- A track with a gap in an otherwise regular sampling interval (possible
  missed detection)
- A bounding box that jumps far more than that object's own typical
  frame-to-frame movement (possible misclick / wrong box)
- A track that ends and a new track of the same object type begins shortly
  after, close in position (possible identity switch — check for an
  occlusion event just before the gap)
