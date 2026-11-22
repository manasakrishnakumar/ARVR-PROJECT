using Unity.InferenceEngine;
using UnityEngine;

namespace Arvr
{
    /// <summary>On-device pose estimation inside Unity: webcam -> MoveNet Lightning (ONNX, Apache-2.0) run by Unity's Inference Engine
    /// (formerly Sentis) -> 33-landmark array. Optional feature; the browser MediaPipe path is unchanged.
    /// Accuracy is NOT validated here (the project's angle errors were measured for MediaPipe on REHAB data, not for this model).</summary>
    public class OnDevicePose
    {
        public const int Size = 192; // MoveNet Lightning input: 1x192x192x3, int 0..255
        readonly Worker worker;
        readonly WebCamTexture cam;
        readonly RenderTexture rt;
        readonly Texture2D readback;
        float lastRun;
        public Lm[] Latest { get; private set; }
        public float Fps { get; private set; }
        public string Error { get; private set; }
        public bool Ready => cam != null && cam.isPlaying && Error == null;

        public OnDevicePose(ModelAsset modelAsset)
        {
            if (modelAsset == null) { Error = "Pose model not assigned (Assets/Resources/movenet_lightning.onnx)."; return; }
            if (WebCamTexture.devices.Length == 0) { Error = "No camera found."; return; }
            worker = new Worker(ModelLoader.Load(modelAsset), BackendType.CPU);
            cam = new WebCamTexture(WebCamTexture.devices[0].name, 640, 480, 30);
            cam.Play();
            rt = new RenderTexture(Size, Size, 0, RenderTextureFormat.ARGB32);
            readback = new Texture2D(Size, Size, TextureFormat.RGB24, false);
        }

        /// <summary>Call every frame; runs the model at most about 20 times a second.</summary>
        public void Tick()
        {
            if (!Ready || cam.width < 32 || !cam.didUpdateThisFrame || Time.time - lastRun < 0.05f) return;
            var dt = Time.time - lastRun; lastRun = Time.time;
            Graphics.Blit(cam, rt); // squashes the frame to 192x192 (the input must be square)
            var prev = RenderTexture.active; RenderTexture.active = rt;
            readback.ReadPixels(new Rect(0, 0, Size, Size), 0, 0); RenderTexture.active = prev;
            var raw = readback.GetRawTextureData<byte>();
            var data = new int[Size * Size * 3];
            for (int i = 0; i < data.Length; i++) data[i] = raw[i];
            // ReadPixels is bottom-up; the model wants top-down, so flip rows
            for (int y = 0; y < Size / 2; y++)
                for (int x = 0; x < Size * 3; x++) { int a = y * Size * 3 + x, b = (Size - 1 - y) * Size * 3 + x; (data[a], data[b]) = (data[b], data[a]); }
            using var input = new Tensor<int>(new TensorShape(1, Size, Size, 3), data);
            worker.Schedule(input);
            var output = worker.PeekOutput() as Tensor<float>;
            var arr = output.DownloadToArray();
            Latest = MoveNetMapper.ToLandmarks(arr);
            if (dt > 0) Fps = Mathf.Lerp(Fps, 1f / dt, 0.2f);
        }

        public void Dispose()
        {
            if (cam != null) cam.Stop();
            worker?.Dispose();
            if (rt != null) rt.Release();
        }
    }
}
