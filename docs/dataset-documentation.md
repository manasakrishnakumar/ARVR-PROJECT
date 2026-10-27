# Dataset documentation

## 1. REHAB26-ViewAngles (real recordings; used for preliminary evaluation)
- **Source**: Zenodo record https://zenodo.org/records/23018128 (DOI 10.5281/zenodo.23018128). Downloaded 2026-10-27: `jointSequences-mediapipe.zip` (686 MB), `Segmentation.csv`, `Segmentation.txt`, `Error_types.csv`, `joint_names.txt`. The 8.4 GB videos were not downloaded.
- **Licence**: CC BY-NC 4.0. Academic / non-commercial research only; attribution required. **Cite the dataset record and the related paper named on the Zenodo page** (add the exact reference to the thesis bibliography; it is not reproduced here). Raw data is not redistributed in this repository (`datasets/external/` is git-ignored).
- **Content**: 5 healthy volunteers, 3 exercises (arm abduction, squat, shoulder extension), 3 synchronised phones at 30 FPS, 1,665 labelled repetitions (832 correct, 833 deliberately incorrect), MediaPipe Pose skeletons (33 joints; x, y, z, visibility per frame). 2D coordinates are normalised 0-1 in the files although the dataset notes say pixels.
- **Labels**: per repetition, `correctness_score` (1 correct / 5 incorrect) and an intended-error code per exercise. Labels were assigned by the dataset authors.
- **How ARVR uses it** (`backend/app/ml/rehab26.py`):
  - arm abduction -> `shoulder_abduction` (right arm); squat -> `sit_to_stand` (left knee angle); shoulder extension -> `shoulder_extension` (right arm; illustrative 10 -> 45 degree image-plane range).
  - one camera per repetition: the view closest to frontal (abduction) or profile (squat, extension) *among cameras where the exercise's joints are visible in at least 80% of the frames* (visibility only, never labels). Before this rule, picking by angle alone chose cameras that could not see the arm for many extension repetitions.
  - the 2D coordinates are normalised per axis; the videos were not downloaded, so portrait 9:16 (x scaled by 0.5625) was inferred from comparing 2D and 3D skeleton scales (median estimate 0.53, 10th-90th percentile 0.46-0.59). Results with and without the correction are both saved in docs/results.
  - correct -> `acceptable`; `ERR_LOW_ABDUCTION` / `ERR_SHALLOW_SQUAT` -> `insufficient_range`; every other error -> `posture_deviation` (not expressible by one joint angle).
  - all 1,665 repetitions import (556 arm abduction, 554 squat, 555 shoulder extension).
- **Evaluation**: leave-one-participant-out (`python -m app.ml.cli lopo`). See the status document for results.
- **Limitations**: 5 people; healthy volunteers performing deliberate errors (not patients, not naturally occurring errors); iPhone footage in a controlled setting; our start/target angles are illustrative and untuned for this data; a single joint angle cannot capture most posture errors.

## 2. REHAB24-6 (real recordings; external validation)
- **Source**: Zenodo record https://zenodo.org/records/13305826 (DOI 10.5281/zenodo.13305826), downloaded 2026-10-27: 2d_joints.zip (693 MB; 30 fps and 120 fps arrays; only the 30 fps files are used), Segmentation.csv, Segmentation.txt, joints_names.txt, marker_names.txt. Markers and 3D joints were not downloaded. Of the 2.65 GB videos.zip only the 31 videos needed for arm abduction and squat (one camera each, 668 MB) were fetched, and MediaPipe Pose Full was run on the labelled repetition frames (see backend/app/ml/video_pose.py); this MediaPipe-on-video version is the like-for-like external test, the mocap-joint version is the secondary one. Extracted landmark arrays stay local (git-ignored); no video is stored by the project.
- **Licence**: CC BY-NC 4.0, academic / non-commercial use, attribution required. Cite the dataset record and its paper (authors listed on the record: Cernek, Sedmidubsky, Budikova; SISAP 2024, DOI 10.1007/978-3-031-75823-2_2: verify the exact reference on the Zenodo page before citing). Not redistributed here.
- **Content**: 10 people, 6 exercises, 1,072 repetitions, a physiotherapist-supervised mix of correct and incorrect execution. Skeletons are 26-joint optical motion-capture projections to the image (pixel coordinates), not pose-estimator output, with no per-joint confidence and no ears/heels. Labels are binary (correct / incorrect), without an error type.
- **How ARVR uses it** (`backend/app/ml/rehab24.py`): exercises 1 (arm abduction, right arm) and 6 (squat) only, mapped to the shared exercises; mocap joints mapped onto the MediaPipe layout (ear and heel landmarks invisible); camera chosen from the person's orientation; 4 repetitions flagged as erroneous mocap are excluded; 369 repetitions imported. Used **only as external validation** (train on REHAB26, test here), with features computable from both sources (no head tilt, heel lift, or depth features).
- **Limitations**: different skeleton source (mocap vs estimated), so a drop in performance mixes dataset shift with skeleton-source shift; binary labels only; 9 participants have usable arm/squat repetitions.

## 3. Synthetic sample data (pipeline testing only)
`datasets/sample/synthetic_reps.csv`, generated by `backend/app/ml/synthetic_data.py`. Labels come from the generating condition. Says nothing about real-world accuracy.

## 4. Considered but not used
- UI-PRMD (public domain; Vicon/Kinect, correct vs non-optimal): official site returned 403; a mirror was declined. May be added later from the official source.
- KIMORE, IntelliRehabDS: Kinect-based; licence/access not confirmed.
- Kaggle: no suitable movement-quality dataset found.

