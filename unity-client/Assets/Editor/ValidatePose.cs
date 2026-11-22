using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace Arvr.Editor
{
    /// <summary>Validation harness for the on-device pose feature. Reads extracted video frames (one folder per recording, JPEG files named
    /// by frame number), runs the BlazePose pipeline on each recording in order (tracking carries over frames, as live), and writes the
    /// 33 landmarks per frame as JSON lines. A Python script then compares the angles with motion capture
    /// (backend/app/ml/unity_pose_eval.py). Run: Unity -batchmode -nographics -projectPath unity-client
    /// -executeMethod Arvr.Editor.ValidatePose.Run -valDir DIR -valOut FILE [-valSigned 0|1]</summary>
    public static class ValidatePose
    {
        static string Arg(string name, string fallback)
        {
            var a = Environment.GetCommandLineArgs();
            for (int i = 0; i < a.Length - 1; i++) if (a[i] == name) return a[i + 1];
            return fallback;
        }

        public static void Run()
        {
            string dir = Arg("-valDir", @"C:\tmp\val"), outFile = Arg("-valOut", @"C:\tmp\val_out.jsonl");
            bool signed = Arg("-valSigned", "1") == "1";
            using var engine = BlazePoseEngine.FromResources(Unity.InferenceEngine.BackendType.CPU);
            engine.DetectorSigned = signed;
            var inv = CultureInfo.InvariantCulture;
            int frames = 0, found = 0, detectorRuns = 0; double ms = 0;
            using var w = new StreamWriter(outFile, false, new UTF8Encoding(false));
            foreach (var recDir in Directory.GetDirectories(dir))
            {
                var rec = Path.GetFileName(recDir);
                engine.Reset();
                var files = Directory.GetFiles(recDir, "*.jpg"); Array.Sort(files, StringComparer.Ordinal);
                var tex = new Texture2D(2, 2, TextureFormat.RGB24, false);
                byte[] rgb = null;
                foreach (var f in files)
                {
                    tex.LoadImage(File.ReadAllBytes(f));
                    int tw = tex.width, th = tex.height;
                    var px = tex.GetPixels32();
                    if (rgb == null || rgb.Length != tw * th * 3) rgb = new byte[tw * th * 3];
                    for (int y = 0; y < th; y++) // texture rows are bottom-up
                    {
                        int src = (th - 1 - y) * tw, dst = y * tw * 3;
                        for (int x = 0; x < tw; x++) { var c = px[src + x]; rgb[dst++] = c.r; rgb[dst++] = c.g; rgb[dst++] = c.b; }
                    }
                    var sw = Stopwatch.StartNew();
                    var lm = engine.Run(rgb, tw, th);
                    sw.Stop(); ms += sw.Elapsed.TotalMilliseconds; frames++;
                    if (engine.DetectorUsedLastFrame) detectorRuns++;
                    if (lm != null) found++;
                    var sb = new StringBuilder();
                    sb.Append("{\"rec\":\"").Append(rec).Append("\",\"frame\":").Append(int.Parse(Path.GetFileNameWithoutExtension(f))).Append(",\"w\":").Append(tw).Append(",\"h\":").Append(th).Append(",\"lm\":");
                    if (lm == null) sb.Append("null");
                    else
                    {
                        sb.Append('[');
                        for (int k = 0; k < lm.Length; k++)
                        {
                            if (k > 0) sb.Append(',');
                            sb.Append(lm[k].x.ToString("R", inv)).Append(',').Append(lm[k].y.ToString("R", inv)).Append(',').Append(lm[k].z.ToString("R", inv)).Append(',').Append(lm[k].v.ToString("R", inv));
                        }
                        sb.Append(']');
                    }
                    sb.Append('}');
                    w.WriteLine(sb.ToString());
                }
                UnityEngine.Object.DestroyImmediate(tex);
                w.Flush();
                UnityEngine.Debug.Log($"VAL {rec} done: frames so far {frames}, found {found}, avg {ms / Math.Max(1, frames):F1} ms/frame");
            }
            UnityEngine.Debug.Log($"VAL SUMMARY frames={frames} found={found} detectorRuns={detectorRuns} avg_ms={ms / Math.Max(1, frames):F2} signed={signed}");
            w.Flush();
        }
    }
}
