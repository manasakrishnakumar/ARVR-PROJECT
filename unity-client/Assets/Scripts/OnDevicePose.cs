using Unity.InferenceEngine;
using UnityEngine;

namespace Arvr
{
    /// <summary>On-device pose estimation inside Unity: webcam -> BlazePose (MediaPipe's pose models as ONNX) in Unity's Inference Engine
    /// -> 33 landmarks with depth and foot points, the same layout as the browser path. Optional feature.</summary>
    public class OnDevicePose
    {
        readonly BlazePoseEngine engine;
        readonly WebCamTexture cam;
        byte[] rgb;
        float lastRun;
        public Lm[] Latest { get; private set; }
        public float Fps { get; private set; }
        public string Error { get; private set; }
        public bool Ready => cam != null && cam.isPlaying && Error == null;

        public OnDevicePose()
        {
            if (WebCamTexture.devices.Length == 0) { Error = "No camera found."; return; }
            try
            {
                engine = BlazePoseEngine.FromResources(SystemInfo.supportsComputeShaders ? BackendType.GPUCompute : BackendType.CPU);
            }
            catch (System.Exception e) { Error = "Pose models not available: " + e.Message; return; }
            cam = new WebCamTexture(WebCamTexture.devices[0].name, 640, 480, 30);
            cam.Play();
        }

        /// <summary>Call every frame; runs the models when the camera has a new frame, at most about 30 times a second.</summary>
        public void Tick()
        {
            if (!Ready || cam.width < 32 || !cam.didUpdateThisFrame || Time.time - lastRun < 0.03f) return;
            var dt = Time.time - lastRun; lastRun = Time.time;
            int w = cam.width, h = cam.height;
            var px = cam.GetPixels32();
            if (rgb == null || rgb.Length != w * h * 3) rgb = new byte[w * h * 3];
            for (int y = 0; y < h; y++) // textures are bottom-up; the engine wants the top row first
            {
                int src = (h - 1 - y) * w, dst = y * w * 3;
                for (int x = 0; x < w; x++) { var c = px[src + x]; rgb[dst++] = c.r; rgb[dst++] = c.g; rgb[dst++] = c.b; }
            }
            Latest = engine.Run(rgb, w, h);
            if (dt > 0) Fps = Mathf.Lerp(Fps, 1f / dt, 0.2f);
        }

        public void Dispose() { if (cam != null) cam.Stop(); engine?.Dispose(); }
    }
}
