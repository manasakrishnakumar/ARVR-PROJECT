using NUnit.Framework;
using UnityEngine;

namespace Arvr.Tests
{
    public class PoseMathTests
    {
        static Lm P(float x, float y, float v = 1f) => new Lm(x, y, 0f, v);

        [Test]
        public void Angle_MeasuresTheAngleAtTheMiddlePoint()
        {
            Assert.AreEqual(90f, PoseMath.Angle(P(1, 0), P(0, 0), P(0, 1)).Value, 0.01f);
            Assert.AreEqual(180f, PoseMath.Angle(P(-1, 0), P(0, 0), P(1, 0)).Value, 0.01f);
            Assert.AreEqual(0f, PoseMath.Angle(P(1, 0), P(0, 0), P(2, 0)).Value, 0.01f);
        }

        [Test]
        public void Angle_IsNullInsteadOfGuessingWhenUnreliable()
        {
            Assert.IsNull(PoseMath.Angle(P(1, 0, 0.1f), P(0, 0), P(0, 1)));   // low confidence
            Assert.IsNull(PoseMath.Angle(P(0, 0), P(0, 0), P(0, 1)));          // zero-length segment
        }

        [TestCase(new[] { "LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST" }, 160f, 50f, "LEFT")]
        [TestCase(new[] { "LEFT_HIP", "LEFT_SHOULDER", "LEFT_ELBOW" }, 20f, 90f, "LEFT")]
        [TestCase(new[] { "LEFT_HIP", "LEFT_SHOULDER", "LEFT_ELBOW" }, 20f, 90f, "RIGHT")]
        [TestCase(new[] { "LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE" }, 170f, 95f, "LEFT")]
        public void Trainer_SetsTheExerciseJointToTheStartAndTargetAngles(string[] names, float start, float target, string side)
        {
            foreach (var (progress, want) in new[] { (0f, start), (1f, target), (0.5f, (start + target) / 2f) })
            {
                var lm = PoseMath.Trainer(names, start, target, side, progress);
                int Idx(string n) => PoseMath.Index[n.Replace("LEFT_", side + "_")];
                var angle = PoseMath.Angle(lm[Idx(names[0])], lm[Idx(names[1])], lm[Idx(names[2])]);
                Assert.IsNotNull(angle);
                Assert.AreEqual(want, angle.Value, 0.5f, $"progress {progress}");
            }
        }

        [Test]
        public void Trainer_ClampsProgressAndKeepsAllLandmarks()
        {
            var names = new[] { "LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST" };
            Assert.AreEqual(PoseMath.LandmarkCount, PoseMath.Trainer(names, 160, 50, "LEFT", 0.3f).Length);
            var over = PoseMath.Trainer(names, 160, 50, "LEFT", 5f);
            var one = PoseMath.Trainer(names, 160, 50, "LEFT", 1f);
            Assert.AreEqual(one[15].x, over[15].x, 1e-5f);
        }

        [Test]
        public void Progress01_GoesOutAndBackOverOnePeriod()
        {
            Assert.AreEqual(0f, PoseMath.Progress01(0f), 1e-4f);
            Assert.AreEqual(1f, PoseMath.Progress01(2f), 1e-4f);
            Assert.AreEqual(0f, PoseMath.Progress01(4f), 1e-4f);
        }

        [Test]
        public void FromFlat_AcceptsExactly33LandmarksOnly()
        {
            var flat = new float[132];
            flat[0] = 0.25f; flat[3] = 0.9f;
            var lm = PoseMath.FromFlat(flat);
            Assert.AreEqual(0.25f, lm[0].x); Assert.AreEqual(0.9f, lm[0].v);
            Assert.IsNull(PoseMath.FromFlat(new float[10]));
            Assert.IsNull(PoseMath.FromFlat(null));
        }

        [Test]
        public void Standing_HasTheJointsTheFigureNeeds()
        {
            var lm = PoseMath.Standing();
            foreach (var i in PoseMath.JointIndices) Assert.AreEqual(1f, lm[i].v, $"joint {i}");
            Assert.Less(lm[0].y, lm[11].y);   // head above shoulders (y grows downward)
            Assert.Less(lm[11].y, lm[23].y);  // shoulders above hips
        }
    }

    public class XrTests
    {
        [Test]
        public void XrStatus_SaysDesktopModeWhenNoHeadsetIsActive()
        {
            Assert.IsFalse(XrStatus.Active);            // edit mode: no XR device
            StringAssert.Contains("no headset", XrStatus.Describe());
        }
    }

    public class ProtocolTests
    {
        [Test]
        public void AnalysisClient_Parses_State_Rep_And_Calibrated_Messages()
        {
            var state = JsonUtility.FromJson<AnalysisClient.Msg>("{\"type\":\"state\",\"phase\":\"target\",\"counted_reps\":2,\"angle\":52.5,\"progress\":0.9,\"calibrating\":false}");
            Assert.AreEqual("state", state.type); Assert.AreEqual("target", state.phase); Assert.AreEqual(2, state.counted_reps); Assert.AreEqual(52.5f, state.angle, 1e-4f);
            var rep = JsonUtility.FromJson<AnalysisClient.Msg>("{\"type\":\"rep\",\"label\":\"acceptable\",\"score\":1.0,\"feedback\":\"Good repetition.\",\"counted\":true}");
            Assert.AreEqual("acceptable", rep.label); Assert.IsTrue(rep.counted); StringAssert.Contains("Good", rep.feedback);
            var cal = JsonUtility.FromJson<AnalysisClient.Msg>("{\"type\":\"calibrated\",\"start\":154.0,\"target\":52.0}");
            Assert.AreEqual(154f, cal.start); Assert.AreEqual(52f, cal.target);
            var hello = JsonUtility.FromJson<AnalysisClient.Msg>("{\"type\":\"hello\",\"target_reps\":5,\"calibrating\":true}");
            Assert.AreEqual(5, hello.target_reps); Assert.IsTrue(hello.calibrating);
        }

        [Test]
        public void AnalysisClient_BuildsTheSameUrlsAsTheWebApp()
        {
            Assert.AreEqual("ws://127.0.0.1:8000/api/ws/analysis?exercise_id=elbow_flexion&difficulty=2",
                AnalysisClient.BuildUrl("http://127.0.0.1:8000/", "elbow_flexion", 2));
            var u = AnalysisClient.BuildUrl("https://example.test", "sit_to_stand", 1, "abc", "k e y", true);
            StringAssert.StartsWith("wss://example.test/api/ws/analysis", u);
            StringAssert.Contains("&session_id=abc&key=k%20e%20y", u);
            StringAssert.EndsWith("&calibrate=auto", u);
        }

        [Test]
        public void RelayClient_BuildsTheUrlAndParsesOnlyValidFrames()
        {
            Assert.AreEqual("ws://127.0.0.1:8000/api/ws/relay/ABC123?role=subscriber", RelayClient.BuildUrl("http://127.0.0.1:8000", "ABC123"));
            var flat = new string[132]; for (int i = 0; i < 132; i++) flat[i] = "0.5";
            var json = "{\"lm\":[" + string.Join(",", flat) + "],\"angle\":90.0,\"has_angle\":true,\"phase\":\"rest\",\"counted_reps\":3,\"target_reps\":5,\"feedback\":\"ok\",\"label\":\"acceptable\"}";
            var f = RelayClient.ParseFrame(json);
            Assert.IsNotNull(f); Assert.AreEqual(3, f.counted_reps); Assert.IsTrue(f.has_angle);
            Assert.IsNull(RelayClient.ParseFrame("{\"type\":\"joined\",\"room\":\"ABC123\"}"));  // control messages are ignored
            Assert.IsNull(RelayClient.ParseFrame("{\"lm\":[1,2,3]}"));                            // wrong length
            Assert.IsNull(RelayClient.ParseFrame("not json"));
        }

        [Test]
        public void ExerciseApi_ParsesTheBackendList_AndSurvivesGarbage()
        {
            var list = ExerciseApi.Parse("[{\"id\":\"elbow_flexion\",\"name\":\"Elbow flexion\",\"landmarks\":[\"LEFT_SHOULDER\",\"LEFT_ELBOW\",\"LEFT_WRIST\"],\"start_angle_deg\":160,\"target_angle_deg\":50,\"difficulty_levels\":{\"1\":{\"target_reps\":5}}}]");
            Assert.AreEqual(1, list.Length);
            Assert.AreEqual("elbow_flexion", list[0].id); Assert.AreEqual(3, list[0].landmarks.Length); Assert.AreEqual(50f, list[0].target_angle_deg);
            Assert.AreEqual(0, ExerciseApi.Parse("").Length);
            Assert.AreEqual(0, ExerciseApi.Parse("not json").Length);
        }
    }

    public class HudMathTests
    {
        [TestCase(0, 5, 0f)]
        [TestCase(2, 5, 0.4f)]
        [TestCase(5, 5, 1f)]
        [TestCase(9, 5, 1f)]   // never past full
        [TestCase(3, 0, 0f)]   // no target known yet
        public void ProgressFraction_IsClampedAndSafeWithoutATarget(int reps, int target, float expected)
        {
            Assert.AreEqual(expected, HudMath.ProgressFraction(reps, target), 0.001f);
        }

        [Test]
        public void PhaseColor_IsGreenOnlyAtTheTarget()
        {
            Assert.AreEqual(HudMath.Target, HudMath.PhaseColor("target"));
            Assert.AreEqual(HudMath.Moving, HudMath.PhaseColor("moving_out"));
            Assert.AreEqual(HudMath.Moving, HudMath.PhaseColor("returning"));
            Assert.AreEqual(HudMath.Rest, HudMath.PhaseColor("rest"));
            Assert.AreEqual(HudMath.Rest, HudMath.PhaseColor(null));
        }

        [Test]
        public void PhaseLabel_IsReadableAndNeverEmpty()
        {
            Assert.AreEqual("Moving out", HudMath.PhaseLabel("moving_out"));
            Assert.AreEqual("Waiting", HudMath.PhaseLabel(""));
            Assert.AreEqual("Waiting", HudMath.PhaseLabel(null));
        }
    }

    public class OnDevicePoseTests
    {
        static float[] Raw(float x, float y, float vis)
        {
            var raw = new float[195];
            for (int k = 0; k < 39; k++) { raw[k * 5] = x; raw[k * 5 + 1] = y; raw[k * 5 + 3] = vis; }
            return raw;
        }

        [Test]
        public void Anchors_AreTheDetectorsExpectedCount()
        {
            Assert.AreEqual(BlazeMath.Anchors, BlazeMath.AnchorCentres().Length);
        }

        [Test]
        public void Roi_UprightBodyHasNoRotationAndTheRightSize()
        {
            var r = BlazeMath.RoiFromKeypoints(new Vector2(300, 400), new Vector2(300, 300)); // scale point straight above the centre
            Assert.AreEqual(0f, r.rot, 1e-4f);
            Assert.AreEqual(2f * 100f * 1.25f, r.size, 1e-3f);
        }

        [Test]
        public void Roi_BodyTiltedRightGivesAQuarterTurnMapping()
        {
            var r = BlazeMath.RoiFromKeypoints(new Vector2(300, 400), new Vector2(400, 400)); // scale point to the right of the centre
            var top = BlazeMath.CropToImage(r, 0.5f, 0f);   // crop top-middle must land on the body-axis side (to the right)
            Assert.Greater(top.x, 300f); Assert.AreEqual(400f, top.y, 1e-2f);
        }

        [Test]
        public void Crop_CentreMapsToRoiCentre()
        {
            var p = BlazeMath.CropToImage(new BlazeMath.Roi { cx = 120, cy = 80, size = 200, rot = 0.7f }, 0.5f, 0.5f);
            Assert.AreEqual(120f, p.x, 1e-3f); Assert.AreEqual(80f, p.y, 1e-3f);
        }

        [Test]
        public void Decode_KeepsDepthAndFootPoints()
        {
            var raw = Raw(128f, 128f, 5f);               // every landmark at the crop centre, clearly visible
            raw[31 * 5 + 2] = 64f;                        // landmark 31 (foot index) with depth
            var lm = BlazeMath.DecodeLandmarks(raw, new BlazeMath.Roi { cx = 320, cy = 240, size = 256, rot = 0f }, 640, 480, out var c, out var s);
            Assert.AreEqual(33, lm.Length);
            Assert.AreEqual(0.5f, lm[29].x, 1e-4f); Assert.AreEqual(0.5f, lm[29].y, 1e-4f); // heel present
            Assert.Greater(lm[29].v, 0.9f);
            Assert.AreEqual(64f / 256f * 256f / 640f, lm[31].z, 1e-4f);                      // depth kept
            Assert.AreEqual(320f, c.x, 1e-3f);
        }

        [Test]
        public void Angle_IsNullWhenAJointIsNotConfident()
        {
            var lm = BlazeMath.DecodeLandmarks(Raw(128f, 128f, 5f), new BlazeMath.Roi { cx = 320, cy = 240, size = 256 }, 640, 480, out _, out _);
            lm[13] = new Lm(lm[13].x, lm[13].y, 0f, 0.1f);
            Assert.IsNull(BlazeMath.AngleIfConfident(lm, 11, 13, 15));
        }

        [Test]
        public void BestDetection_PicksTheHighestScoreAndRejectsWeakOnes()
        {
            var boxes = new float[BlazeMath.Anchors * 12]; var scores = new float[BlazeMath.Anchors];
            for (int i = 0; i < scores.Length; i++) scores[i] = -10f;
            Assert.IsFalse(BlazeMath.BestDetection(boxes, scores, 0.5f, out _, out _, out _));
            scores[100] = 4f;
            Assert.IsTrue(BlazeMath.BestDetection(boxes, scores, 0.5f, out var k0, out _, out var sc));
            Assert.Greater(sc, 0.9f);
            Assert.AreEqual(BlazeMath.AnchorCentres()[100].x, k0.x, 1e-5f);
        }

        [Test]
        public void Models_LoadAndRunWithoutAPersonInTheFrame()
        {
            using var engine = BlazePoseEngine.FromResources();
            var blank = new byte[320 * 240 * 3];
            for (int i = 0; i < blank.Length; i++) blank[i] = 128;
            Assert.IsNull(engine.Run(blank, 320, 240)); // a flat grey frame has no person
            Assert.IsTrue(engine.DetectorUsedLastFrame);
        }
    }
}
