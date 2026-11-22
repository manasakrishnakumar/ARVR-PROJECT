namespace Arvr
{
    /// <summary>Turns MoveNet's 17 keypoints into the 33-landmark layout the rest of the app uses (MediaPipe order).
    /// MoveNet output is [1,1,17,3] = (y, x, score) per keypoint, y and x in 0..1 of the (square) input image.
    /// MoveNet has no z and no heel/foot points: z is 0 and the foot points copy the ankle with zero visibility.</summary>
    public static class MoveNetMapper
    {
        public const int Keypoints = 17;
        public const float MinScore = 0.3f;

        // COCO index -> MediaPipe index: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles
        static readonly int[] ToMediaPipe = { 0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28 };

        public static Lm[] ToLandmarks(float[] output)
        {
            var lm = new Lm[33];
            for (int i = 0; i < 33; i++) lm[i] = new Lm(0.5f, 0.5f, 0f, 0f);
            if (output == null || output.Length < Keypoints * 3) return lm;
            for (int k = 0; k < Keypoints; k++)
            {
                float y = output[k * 3], x = output[k * 3 + 1], s = output[k * 3 + 2];
                lm[ToMediaPipe[k]] = new Lm(x, y, 0f, s);
            }
            // heel / foot-index points: MoveNet has none, so they follow the ankles (visibility stays 0)
            lm[29] = new Lm(lm[27].x, lm[27].y, 0f, 0f); lm[31] = lm[29];
            lm[30] = new Lm(lm[28].x, lm[28].y, 0f, 0f); lm[32] = lm[30];
            return lm;
        }

        /// <summary>Angle at b for the three named landmarks, or null when any of the three is below the confidence threshold.</summary>
        public static float? AngleIfConfident(Lm[] lm, int a, int b, int c)
        {
            if (lm[a].v < MinScore || lm[b].v < MinScore || lm[c].v < MinScore) return null;
            return PoseMath.Angle(lm[a], lm[b], lm[c]);
        }
    }
}
