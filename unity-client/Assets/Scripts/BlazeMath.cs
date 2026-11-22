using System;
using UnityEngine;

namespace Arvr
{
    /// <summary>Pure maths for the BlazePose pipeline (MediaPipe pose models run on-device): anchors, detection decoding,
    /// region-of-interest geometry and landmark back-projection. No model or camera needed, so it is unit-tested.</summary>
    public static class BlazeMath
    {
        public const int DetSize = 224, LmSize = 256, Anchors = 2254, Landmarks = 33;
        public const float MinVisibility = 0.5f;

        /// <summary>A square, possibly rotated crop region in image pixels.</summary>
        public struct Roi { public float cx, cy, size, rot; }

        public static float Sigmoid(float x) => 1f / (1f + Mathf.Exp(-x));

        static Vector2[] anchorCache;
        /// <summary>Anchor centres (normalised 0..1) of the pose detector: strides 8, 16, 32 x3 on a 224 input; anchor sizes are fixed.</summary>
        public static Vector2[] AnchorCentres()
        {
            if (anchorCache != null) return anchorCache;
            var list = new System.Collections.Generic.List<Vector2>(Anchors);
            foreach (var (stride, perCell) in new[] { (8, 2), (16, 2), (32, 6) })
            {
                int fm = Mathf.CeilToInt(DetSize / (float)stride);
                for (int y = 0; y < fm; y++)
                    for (int x = 0; x < fm; x++)
                        for (int a = 0; a < perCell; a++) list.Add(new Vector2((x + 0.5f) / fm, (y + 0.5f) / fm));
            }
            return anchorCache = list.ToArray();
        }

        /// <summary>Best detection: boxes are [2254*12] (dx, dy, w, h, then 4 keypoint x/y pairs), scores are 2254 logits.
        /// Keypoint 0 is the hip centre and keypoint 1 a point on the circle around the body. Returned in normalised padded-square coordinates.</summary>
        public static bool BestDetection(float[] boxes, float[] scores, float minScore, out Vector2 kp0, out Vector2 kp1, out float score)
        {
            kp0 = kp1 = default; score = 0f;
            if (boxes == null || scores == null || boxes.Length < Anchors * 12 || scores.Length < Anchors) return false;
            var anc = AnchorCentres();
            int best = -1; float bestLogit = float.NegativeInfinity;
            for (int i = 0; i < Anchors; i++) if (scores[i] > bestLogit) { bestLogit = scores[i]; best = i; }
            score = Sigmoid(Mathf.Clamp(bestLogit, -100f, 100f));
            if (best < 0 || score < minScore) return false;
            int o = best * 12; var a = anc[best];
            kp0 = new Vector2(boxes[o + 4] / DetSize + a.x, boxes[o + 5] / DetSize + a.y);
            kp1 = new Vector2(boxes[o + 6] / DetSize + a.x, boxes[o + 7] / DetSize + a.y);
            return true;
        }

        /// <summary>Normalised padded-square coordinates (letterboxed detector input) to image pixels.</summary>
        public static Vector2 LetterboxToPixel(Vector2 n, int w, int h)
        {
            float s = Mathf.Max(w, h);
            return new Vector2(n.x * s - (s - w) * 0.5f, n.y * s - (s - h) * 0.5f);
        }

        /// <summary>MediaPipe pose ROI: centred on the body centre, size = 2 x distance to the scale point x 1.25, rotated so the
        /// body axis (centre to scale point) points up. Inputs in image pixels.</summary>
        public static Roi RoiFromKeypoints(Vector2 centre, Vector2 scalePoint)
        {
            float dx = scalePoint.x - centre.x, dy = scalePoint.y - centre.y;
            float rot = Mathf.PI / 2f - Mathf.Atan2(-dy, dx);
            rot -= 2f * Mathf.PI * Mathf.Floor((rot + Mathf.PI) / (2f * Mathf.PI)); // normalise to [-pi, pi)
            return new Roi { cx = centre.x, cy = centre.y, size = 2f * Mathf.Sqrt(dx * dx + dy * dy) * 1.25f, rot = rot };
        }

        /// <summary>Image pixel for a point (u, v in 0..1) of the crop.</summary>
        public static Vector2 CropToImage(Roi r, float u, float v)
        {
            float lx = (u - 0.5f) * r.size, ly = (v - 0.5f) * r.size, c = Mathf.Cos(r.rot), s = Mathf.Sin(r.rot);
            return new Vector2(r.cx + c * lx - s * ly, r.cy + s * lx + c * ly);
        }

        /// <summary>Raw landmark output (39 x [x, y, z, visibility logit, presence logit], x/y/z in crop pixels) to 33 landmarks in the
        /// app's layout (x, y normalised to the image, z in x-units, v = visibility), plus the two ROI alignment points (image pixels).</summary>
        public static Lm[] DecodeLandmarks(float[] raw, Roi r, int w, int h, out Vector2 centre, out Vector2 scalePoint)
        {
            centre = scalePoint = default;
            if (raw == null || raw.Length < 35 * 5) return null;
            Vector2 P(int k) => CropToImage(r, raw[k * 5] / LmSize, raw[k * 5 + 1] / LmSize);
            var lm = new Lm[Landmarks];
            for (int k = 0; k < Landmarks; k++)
            {
                var p = P(k);
                lm[k] = new Lm(p.x / w, p.y / h, raw[k * 5 + 2] / LmSize * r.size / w, Sigmoid(Mathf.Clamp(raw[k * 5 + 3], -100f, 100f)));
            }
            centre = P(33); scalePoint = P(34);
            return lm;
        }

        /// <summary>Angle at b for three landmarks, or null when any is not confidently visible.</summary>
        public static float? AngleIfConfident(Lm[] lm, int a, int b, int c)
        {
            if (lm == null || lm[a].v < MinVisibility || lm[b].v < MinVisibility || lm[c].v < MinVisibility) return null;
            return PoseMath.Angle(lm[a], lm[b], lm[c]);
        }
    }
}
