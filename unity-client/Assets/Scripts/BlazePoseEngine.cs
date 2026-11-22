using System;
using Unity.InferenceEngine;
using UnityEngine;

namespace Arvr
{
    /// <summary>MediaPipe BlazePose run in Unity's Inference Engine: a detector finds the person once, then the landmark model runs
    /// on a tracked region each frame (the detector runs again only when tracking is lost), as in MediaPipe itself.
    /// Models: unity/inference-engine-blaze-pose (ONNX conversions of Google's pose detector and pose_landmark_full, Apache-2.0).
    /// Gives 33 landmarks with depth (z) and heel / foot points. Single person.</summary>
    public class BlazePoseEngine : IDisposable
    {
        readonly Worker detector, landmarker;
        readonly float[] detIn = new float[BlazeMath.DetSize * BlazeMath.DetSize * 3];
        readonly float[] lmIn = new float[BlazeMath.LmSize * BlazeMath.LmSize * 3];
        BlazeMath.Roi roi; bool tracking;
        public bool DetectorUsedLastFrame { get; private set; }
        /// <summary>Detector input range: true = [-1, 1] (MediaPipe's setting for the pose detector), false = [0, 1].</summary>
        public bool DetectorSigned = true;
        public float MinDetectionScore = 0.5f, MinPoseScore = 0.5f;

        public BlazePoseEngine(ModelAsset detectorAsset, ModelAsset landmarkAsset, BackendType backend = BackendType.CPU)
        {
            detector = new Worker(ModelLoader.Load(detectorAsset), backend);
            landmarker = new Worker(ModelLoader.Load(landmarkAsset), backend);
        }

        public static BlazePoseEngine FromResources(BackendType backend = BackendType.CPU) => new BlazePoseEngine(
            Resources.Load<ModelAsset>("blazepose/pose_detection"), Resources.Load<ModelAsset>("blazepose/pose_landmarks_detector_full"), backend);

        public void Reset() => tracking = false;

        /// <summary>Runs on one frame (RGB bytes, top row first, 3 per pixel). Returns 33 landmarks, or null when no person is found.</summary>
        public Lm[] Run(byte[] rgb, int w, int h)
        {
            DetectorUsedLastFrame = false;
            if (!tracking)
            {
                DetectorUsedLastFrame = true;
                if (!Detect(rgb, w, h)) return null;
            }
            Crop(rgb, w, h, roi);
            float[] raw, flag;
            using (var input = new Tensor<float>(new TensorShape(1, BlazeMath.LmSize, BlazeMath.LmSize, 3), lmIn))
            {
                landmarker.Schedule(input);
                raw = (landmarker.PeekOutput(0) as Tensor<float>).DownloadToArray();
                flag = (landmarker.PeekOutput(1) as Tensor<float>).DownloadToArray();
            }
            float f = flag[0]; if (f < 0f || f > 1f) f = BlazeMath.Sigmoid(f);
            var lm = BlazeMath.DecodeLandmarks(raw, roi, w, h, out var c, out var s);
            if (lm == null || f < MinPoseScore) { tracking = false; return null; }
            roi = BlazeMath.RoiFromKeypoints(c, s); tracking = true;
            return lm;
        }

        bool Detect(byte[] rgb, int w, int h)
        {
            int n = BlazeMath.DetSize; float side = Mathf.Max(w, h), padX = (side - w) * 0.5f, padY = (side - h) * 0.5f;
            for (int j = 0; j < n; j++)
                for (int i = 0; i < n; i++)
                {
                    float px = (i + 0.5f) / n * side - padX, py = (j + 0.5f) / n * side - padY;
                    Sample(rgb, w, h, px, py, out var r, out var g, out var b);
                    int o = (j * n + i) * 3;
                    if (DetectorSigned) { detIn[o] = r * 2f - 1f; detIn[o + 1] = g * 2f - 1f; detIn[o + 2] = b * 2f - 1f; }
                    else { detIn[o] = r; detIn[o + 1] = g; detIn[o + 2] = b; }
                }
            float[] boxes, scores;
            using (var input = new Tensor<float>(new TensorShape(1, n, n, 3), detIn))
            {
                detector.Schedule(input);
                boxes = (detector.PeekOutput(0) as Tensor<float>).DownloadToArray();
                scores = (detector.PeekOutput(1) as Tensor<float>).DownloadToArray();
            }
            if (!BlazeMath.BestDetection(boxes, scores, MinDetectionScore, out var k0, out var k1, out _)) return false;
            roi = BlazeMath.RoiFromKeypoints(BlazeMath.LetterboxToPixel(k0, w, h), BlazeMath.LetterboxToPixel(k1, w, h));
            return roi.size > 8f;
        }

        void Crop(byte[] rgb, int w, int h, BlazeMath.Roi r)
        {
            int n = BlazeMath.LmSize;
            for (int j = 0; j < n; j++)
                for (int i = 0; i < n; i++)
                {
                    var p = BlazeMath.CropToImage(r, (i + 0.5f) / n, (j + 0.5f) / n);
                    Sample(rgb, w, h, p.x, p.y, out var cr, out var cg, out var cb);
                    int o = (j * n + i) * 3; lmIn[o] = cr; lmIn[o + 1] = cg; lmIn[o + 2] = cb;
                }
        }

        /// <summary>Bilinear sample at pixel coordinates (pixel centres at +0.5); outside the image is black. Values 0..1.</summary>
        static void Sample(byte[] rgb, int w, int h, float x, float y, out float r, out float g, out float b)
        {
            r = g = b = 0f;
            x -= 0.5f; y -= 0.5f;
            int x0 = Mathf.FloorToInt(x), y0 = Mathf.FloorToInt(y);
            if (x0 < -1 || y0 < -1 || x0 >= w || y0 >= h) return;
            float fx = x - x0, fy = y - y0;
            for (int dy = 0; dy < 2; dy++)
                for (int dx = 0; dx < 2; dx++)
                {
                    int xx = x0 + dx, yy = y0 + dy;
                    if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
                    float wgt = (dx == 0 ? 1 - fx : fx) * (dy == 0 ? 1 - fy : fy); int o = (yy * w + xx) * 3;
                    r += rgb[o] * wgt; g += rgb[o + 1] * wgt; b += rgb[o + 2] * wgt;
                }
            r /= 255f; g /= 255f; b /= 255f;
        }

        public void Dispose() { detector?.Dispose(); landmarker?.Dispose(); }
    }
}
