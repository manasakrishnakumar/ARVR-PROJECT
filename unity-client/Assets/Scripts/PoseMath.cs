using System;
using System.Collections.Generic;

namespace Arvr
{
    /// <summary>One MediaPipe-style landmark: normalised image coordinates (y grows downward), relative depth, confidence.</summary>
    public struct Lm
    {
        public float x, y, z, v;
        public Lm(float x, float y, float z, float v) { this.x = x; this.y = y; this.z = z; this.v = v; }
    }

    /// <summary>Pose helpers shared by the trainer avatar, the live relay and the tests. Mirrors frontend/src/pose/trainer.ts.</summary>
    public static class PoseMath
    {
        public const int LandmarkCount = 33;
        public const float MinConfidence = 0.5f;

        public static readonly Dictionary<string, int> Index = new Dictionary<string, int>
        {
            {"LEFT_SHOULDER", 11}, {"RIGHT_SHOULDER", 12}, {"LEFT_ELBOW", 13}, {"RIGHT_ELBOW", 14}, {"LEFT_WRIST", 15}, {"RIGHT_WRIST", 16},
            {"LEFT_HIP", 23}, {"RIGHT_HIP", 24}, {"LEFT_KNEE", 25}, {"RIGHT_KNEE", 26}, {"LEFT_ANKLE", 27}, {"RIGHT_ANKLE", 28},
        };

        /// <summary>Bone pairs drawn between landmarks.</summary>
        public static readonly int[][] Bones =
        {
            new[] {11, 12}, new[] {11, 13}, new[] {13, 15}, new[] {12, 14}, new[] {14, 16}, new[] {11, 23}, new[] {12, 24},
            new[] {23, 24}, new[] {23, 25}, new[] {25, 27}, new[] {24, 26}, new[] {26, 28},
        };

        public static readonly int[] JointIndices = { 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28 };

        /// <summary>A standing figure, everything visible.</summary>
        public static Lm[] Standing()
        {
            var lm = new Lm[LandmarkCount];
            void Set(int i, float x, float y) => lm[i] = new Lm(x, y, 0f, 1f);
            Set(0, 0.5f, 0.16f); Set(7, 0.53f, 0.17f); Set(8, 0.47f, 0.17f);
            Set(11, 0.57f, 0.28f); Set(12, 0.43f, 0.28f); Set(13, 0.59f, 0.44f); Set(14, 0.41f, 0.44f); Set(15, 0.60f, 0.58f); Set(16, 0.40f, 0.58f);
            Set(23, 0.55f, 0.58f); Set(24, 0.45f, 0.58f); Set(25, 0.55f, 0.78f); Set(26, 0.45f, 0.78f); Set(27, 0.55f, 0.95f); Set(28, 0.45f, 0.95f);
            return lm;
        }

        /// <summary>Angle in degrees at b between b-&gt;a and b-&gt;c (image plane), or null if a landmark is unreliable or a segment has no length.</summary>
        public static float? Angle(Lm a, Lm b, Lm c)
        {
            if (a.v < MinConfidence || b.v < MinConfidence || c.v < MinConfidence) return null;
            float ux = a.x - b.x, uy = a.y - b.y, vx = c.x - b.x, vy = c.y - b.y;
            float nu = (float)Math.Sqrt(ux * ux + uy * uy), nv = (float)Math.Sqrt(vx * vx + vy * vy);
            if (nu < 1e-6f || nv < 1e-6f) return null;
            float cos = Math.Max(-1f, Math.Min(1f, (ux * vx + uy * vy) / (nu * nv)));
            return (float)(Math.Acos(cos) * 180.0 / Math.PI);
        }

        /// <summary>Virtual trainer: the standing figure with the exercise joint at the angle for <paramref name="progress"/> (0 = start, 1 = target).</summary>
        public static Lm[] Trainer(string[] landmarkNames, float startDeg, float targetDeg, string side, float progress)
        {
            var lm = Standing();
            int Idx(string n) => Index[n.Replace("LEFT_", side + "_")];
            int a = Idx(landmarkNames[0]), b = Idx(landmarkNames[1]), c = Idx(landmarkNames[2]);
            float p = Math.Max(0f, Math.Min(1f, progress));
            double theta = (startDeg + p * (targetDeg - startDeg)) * Math.PI / 180.0;
            Lm A = lm[a], B = lm[b], C = lm[c];
            double len = Math.Sqrt((C.x - B.x) * (C.x - B.x) + (C.y - B.y) * (C.y - B.y));
            double ux = A.x - B.x, uy = A.y - B.y, un = Math.Sqrt(ux * ux + uy * uy);
            if (un < 1e-9) un = 1;
            (float x, float y) Rot(double s) =>
                ((float)(B.x + len * (ux * Math.Cos(theta * s) - uy * Math.Sin(theta * s)) / un),
                 (float)(B.y + len * (ux * Math.Sin(theta * s) + uy * Math.Cos(theta * s)) / un));
            var c0 = Rot(1); var c1 = Rot(-1);
            // the limb moves away from the body's midline, which is how these exercises look from the front
            var best = Math.Abs(c0.x - 0.5f) >= Math.Abs(c1.x - 0.5f) ? c0 : c1;
            lm[c] = new Lm(best.x, best.y, C.z, C.v);
            return lm;
        }

        /// <summary>0..1..0 over one repetition lasting <paramref name="period"/> seconds.</summary>
        public static float Progress01(float tSeconds, float period = 4f) => (float)((1 - Math.Cos(2 * Math.PI * tSeconds / period)) / 2);

        /// <summary>Flattened [x,y,z,v, ...] (as sent by the web relay) to landmarks. Returns null unless exactly 33 landmarks.</summary>
        public static Lm[] FromFlat(float[] flat)
        {
            if (flat == null || flat.Length != LandmarkCount * 4) return null;
            var lm = new Lm[LandmarkCount];
            for (int i = 0; i < LandmarkCount; i++) lm[i] = new Lm(flat[4 * i], flat[4 * i + 1], flat[4 * i + 2], flat[4 * i + 3]);
            return lm;
        }
    }
}
