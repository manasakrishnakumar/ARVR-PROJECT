using System.Collections;
using UnityEngine;

namespace Arvr
{
    /// <summary>
    /// Desktop 3D rehabilitation room. Attach to an empty GameObject (the scene "Assets/Scenes/RehabRoom.unity" already does) and press Play.
    ///
    /// Angle sources:
    ///  - Trainer demo: a synthetic sweep between the exercise's illustrative start and target angles (sent as a DEMO session);
    ///  - Manual slider: you set the angle;
    ///  - Live from browser: the web app's 3D room page publishes your real webcam pose to a room code on the local backend
    ///    and this client shows it (pose estimation stays in the browser; the browser also does the counting).
    /// The backend, not Unity, counts repetitions and assesses quality. Research prototype; not a medical device.
    /// </summary>
    public class RehabRoom : MonoBehaviour
    {
        public string backendUrl = "http://127.0.0.1:8000";
        public string exerciseId = "elbow_flexion";
        public int level = 1;
        public float sendHz = 15f;
        public bool calibrate = true;

        enum Source { TrainerDemo, ManualSlider, LiveFromBrowser, OnDeviceCamera }
        OnDevicePose onDevice;
        Source source = Source.TrainerDemo;
        ExerciseApi.Exercise[] exercises = new ExerciseApi.Exercise[0];
        int exerciseIndex;
        bool running;
        float t0, lastSend, manualProgress = 0f;
        float angle = float.NaN;
        string roomCode = "";
        AnalysisClient client;
        RelayClient relay;
        SessionApi.Created session;
        SessionApi.Completed result;
        string phase = "waiting", feedback = "", status = "Press Start.", calibratedText = "";
        int reps, target;
        LandmarkFigure trainer, user;
        Vector2 scroll;
        GUIStyle bigStyle, titleStyle, pillStyle;
        Texture2D white;

        ExerciseApi.Exercise Current => exercises.Length > 0 ? exercises[Mathf.Clamp(exerciseIndex, 0, exercises.Length - 1)] : null;

        IEnumerator Start()
        {
            BuildRoom();
            trainer = new LandmarkFigure("Trainer", new Color(0.98f, 0.75f, 0.14f));
            user = new LandmarkFigure("You", new Color(0.18f, 0.83f, 0.75f));
            yield return ExerciseApi.Load(backendUrl, e => exercises = e);
            if (exercises.Length == 0)
            {
                // the backend is not up yet: keep the room usable with the default exercise
                exercises = new[] { new ExerciseApi.Exercise { id = "elbow_flexion", name = "Elbow flexion",
                    landmarks = new[] { "LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST" }, start_angle_deg = 160, target_angle_deg = 50 } };
                status = "Backend not reachable: using the built-in elbow flexion. Start the backend and press Play again for all exercises.";
            }
            exerciseIndex = Mathf.Max(0, System.Array.FindIndex(exercises, x => x.id == exerciseId));
        }

        void BuildRoom()
        {
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.transform.localScale = new Vector3(0.6f, 1, 0.5f);
            floor.GetComponent<Renderer>().material.color = new Color(0.17f, 0.23f, 0.26f);
            var wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wall.transform.position = new Vector3(0, 1.5f, 2.5f);
            wall.transform.localScale = new Vector3(8, 3, 0.1f);
            wall.GetComponent<Renderer>().material.color = new Color(0.11f, 0.16f, 0.19f);
            var light = new GameObject("Light").AddComponent<Light>();
            light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(50, -30, 0);
            Camera.main.transform.position = new Vector3(0, 1.3f, -3.6f);
            Camera.main.transform.LookAt(new Vector3(0, 1.0f, 0));
            Camera.main.clearFlags = CameraClearFlags.SolidColor;
            Camera.main.backgroundColor = new Color(0.05f, 0.08f, 0.11f);
            // floor grid and a teal rim light so the figures stand out
            var gridColor = new Color(0.20f, 0.34f, 0.38f);
            for (int i = -6; i <= 6; i++)
            {
                GridLine(new Vector3(i * 0.5f, 0.005f, 0), new Vector3(0.012f, 0.004f, 5.0f), gridColor);
                GridLine(new Vector3(0, 0.005f, i * 0.4f), new Vector3(6.0f, 0.004f, 0.012f), gridColor);
            }
            var rim = new GameObject("Rim light").AddComponent<Light>();
            rim.type = LightType.Point; rim.color = new Color(0.18f, 0.83f, 0.75f); rim.intensity = 1.2f; rim.range = 7f;
            rim.transform.position = new Vector3(0, 2.4f, 1.8f);
        }

        static void GridLine(Vector3 pos, Vector3 scale, Color color)
        {
            var g = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Destroy(g.GetComponent<Collider>());
            g.transform.position = pos; g.transform.localScale = scale;
            g.GetComponent<Renderer>().material.color = color;
        }

        string Side => "LEFT";

        IEnumerator StartSession()
        {
            var ex = Current;
            if (ex == null) yield break;
            result = null; reps = 0; target = 0; calibratedText = ""; feedback = ""; phase = "waiting"; angle = float.NaN;
            if (source == Source.LiveFromBrowser)
            {
                if (string.IsNullOrWhiteSpace(roomCode)) { status = "Type the room code shown on the web app's 3D room page."; yield break; }
                relay = new RelayClient();
                var rtask = relay.ConnectAsync(backendUrl, roomCode.Trim().ToUpperInvariant());
                while (!rtask.IsCompleted) yield return null;
                status = relay.Connected ? "Connected. Start the camera on the web page and move." : $"Could not join the room ({relay.LastError}).";
                running = relay.Connected;
                yield break;
            }
            status = "Creating session...";
            bool synthetic = source != Source.OnDeviceCamera; // the demo and the slider are synthetic: always a demo session; a real camera is not
            yield return SessionApi.Create(backendUrl, ex.id, level, synthetic, s => session = s);
            client = new AnalysisClient();
            var task = client.ConnectAsync(backendUrl, ex.id, level, session?.id, session?.ws_key, calibrate);
            while (!task.IsCompleted) yield return null;
            status = client.Connected ? (calibrate ? "Streaming. Calibrating to the range you move in (about 5 seconds)." : "Streaming to the backend.")
                                      : $"Backend not reachable ({client.LastError}); the room still runs.";
            if (source == Source.OnDeviceCamera)
            {
                onDevice = new OnDevicePose(Resources.Load<Unity.InferenceEngine.ModelAsset>("movenet_lightning"));
                if (onDevice.Error != null) { status = onDevice.Error; onDevice = null; yield break; }
                status = "On-device pose (MoveNet via Unity Inference Engine). Stand in view of the camera.";
            }
            t0 = Time.time; running = true;
        }

        IEnumerator StopSession()
        {
            running = false;
            client?.Dispose(); client = null;
            relay?.Dispose(); relay = null;
            onDevice?.Dispose(); onDevice = null;
            if (session != null && reps > 0) yield return SessionApi.Complete(backendUrl, session.id, c => result = c);
            session = null;
            status = "Stopped.";
        }

        void Update()
        {
            var ex = Current;
            if (ex == null) return;
            // the trainer always shows the exercise's illustrative movement
            trainer.Apply(PoseMath.Trainer(ex.landmarks, ex.start_angle_deg, ex.target_angle_deg, Side, PoseMath.Progress01(Time.time)), -1.1f);
            // the exercising joint is the middle landmark of the exercise's three; it is coloured by the counter phase
            int joint = ex.landmarks != null && ex.landmarks.Length >= 2 && PoseMath.Index.TryGetValue(ex.landmarks[1], out var li) ? li : -1;
            trainer.Highlight(joint, HudMath.Moving);
            user.Highlight(joint, HudMath.PhaseColor(phase));
            if (!running) { user.SetVisible(false); return; }

            if (source == Source.LiveFromBrowser)
            {
                if (relay != null && relay.TryGetLatest(out var f))
                {
                    user.Apply(PoseMath.FromFlat(f.lm), 1.1f);
                    angle = f.has_angle ? f.angle : float.NaN;
                    phase = f.phase; reps = f.counted_reps; target = f.target_reps;
                    if (!string.IsNullOrEmpty(f.feedback)) feedback = $"{f.label}: {f.feedback}";
                }
                if (relay != null && !relay.Connected) status = $"Relay disconnected ({relay.LastError}).";
                return;
            }

            var t = Time.time - t0;
            if (source == Source.OnDeviceCamera && onDevice != null)
            {
                onDevice.Tick();
                if (onDevice.Latest != null)
                {
                    user.Apply(onDevice.Latest, 1.1f);
                    var names = ex.landmarks;
                    if (names != null && names.Length >= 3 && PoseMath.Index.TryGetValue(names[0], out var ia) && PoseMath.Index.TryGetValue(names[1], out var ib) && PoseMath.Index.TryGetValue(names[2], out var ic))
                    {
                        var a = MoveNetMapper.AngleIfConfident(onDevice.Latest, ia, ib, ic);
                        angle = a ?? float.NaN;
                        if (a.HasValue && client != null && Time.time - lastSend >= 1f / sendHz) { lastSend = Time.time; client.Send(t, a.Value); }
                    }
                }
                DrainClient();
                return;
            }
            float progress = source == Source.TrainerDemo ? PoseMath.Progress01(t) : manualProgress;
            angle = ex.start_angle_deg + progress * (ex.target_angle_deg - ex.start_angle_deg);
            user.Apply(PoseMath.Trainer(ex.landmarks, ex.start_angle_deg, ex.target_angle_deg, Side, progress), 1.1f);
            if (client != null && Time.time - lastSend >= 1f / sendHz) { lastSend = Time.time; client.Send(t, angle); }
            DrainClient();
        }

        void DrainClient()
        {
            while (client != null && client.TryDequeue(out var m))
            {
                if (m.type == "hello") target = m.target_reps;
                else if (m.type == "calibrated") { calibratedText = $"Calibrated range: {m.start:F0}° to {m.target:F0}° (what you demonstrated, not a target)."; status = "Streaming to the backend."; }
                else if (m.type == "state") { phase = m.phase; reps = m.counted_reps; }
                else if (m.type == "rep") feedback = $"{m.label} ({m.score:F2}): {m.feedback}";
                else if (m.type == "error") status = m.detail;
            }
        }

        void OnGUI()
        {
            EnsureStyles();
            GUILayout.BeginArea(new Rect(12, 12, 470, Screen.height - 24), GUI.skin.box);
            GUILayout.Label("ARVR Rehabilitation Room", titleStyle);
            GUILayout.Label("Research prototype, not a medical device");
            var ex = Current;
            if (!running)
            {
                GUILayout.Label("Exercise:");
                scroll = GUILayout.BeginScrollView(scroll, GUILayout.Height(84));
                var names = new string[exercises.Length];
                for (int i = 0; i < names.Length; i++) names[i] = exercises[i].name;
                exerciseIndex = GUILayout.SelectionGrid(exerciseIndex, names, 2);
                GUILayout.EndScrollView();
                GUILayout.BeginHorizontal();
                GUILayout.Label("Level:");
                for (int l = 1; l <= 3; l++) if (GUILayout.Toggle(level == l, l.ToString(), GUI.skin.button, GUILayout.Width(40))) level = l;
                calibrate = GUILayout.Toggle(calibrate, "Calibrate to my range");
                GUILayout.EndHorizontal();
                source = (Source)GUILayout.Toolbar((int)source, new[] { "Trainer demo", "Manual slider", "Live from browser", "On-device camera" });
                if (source == Source.LiveFromBrowser)
                {
                    GUILayout.BeginHorizontal(); GUILayout.Label("Room code:"); roomCode = GUILayout.TextField(roomCode, 12); GUILayout.EndHorizontal();
                }
                if (GUILayout.Button("Start")) StartCoroutine(StartSession());
            }
            else
            {
                if (source == Source.ManualSlider) manualProgress = GUILayout.HorizontalSlider(manualProgress, 0f, 1f);
                if (GUILayout.Button("Stop and save")) StartCoroutine(StopSession());
            }
            GUILayout.Label($"{ex?.name}  ·  level {level}  ·  {backendUrl}  ·  {XrStatus.Describe()}");
            GUILayout.BeginHorizontal();
            GUILayout.Label($"{reps} / {(target > 0 ? target.ToString() : "-")}", bigStyle, GUILayout.Width(150));
            var prev = GUI.color; GUI.color = HudMath.PhaseColor(phase);
            GUILayout.Label(HudMath.PhaseLabel(phase), pillStyle, GUILayout.Width(130));
            GUI.color = prev;
            GUILayout.Label($"Angle: {(float.IsNaN(angle) ? "n/a" : angle.ToString("F0") + "°")}");
            GUILayout.EndHorizontal();
            var bar = GUILayoutUtility.GetRect(1, 12, GUILayout.ExpandWidth(true));
            GUI.color = new Color(1, 1, 1, 0.18f); GUI.DrawTexture(bar, white);
            GUI.color = HudMath.Target; GUI.DrawTexture(new Rect(bar.x, bar.y, bar.width * HudMath.ProgressFraction(reps, target), bar.height), white);
            GUI.color = prev;
            if (!string.IsNullOrEmpty(calibratedText)) GUILayout.Label(calibratedText);
            GUILayout.Label(feedback);
            GUILayout.Label(status);
            if (result?.recommendation != null)
            {
                var r = result.recommendation;
                GUILayout.Label($"Suggestion: {r.action} → level {r.next_level}" + (result.saved_to_history ? " (saved)" : " (demo/guest: not saved)"));
                foreach (var reason in r.reasons) GUILayout.Label("• " + reason);
                GUILayout.Label(r.safety_note);
            }
            GUILayout.EndArea();
        }

        void EnsureStyles()
        {
            if (bigStyle != null) return;
            white = Texture2D.whiteTexture;
            bigStyle = new GUIStyle(GUI.skin.label) { fontSize = 40, fontStyle = FontStyle.Bold };
            titleStyle = new GUIStyle(GUI.skin.label) { fontSize = 20, fontStyle = FontStyle.Bold };
            pillStyle = new GUIStyle(GUI.skin.label) { fontSize = 16, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
        }

        void OnDestroy() { client?.Dispose(); relay?.Dispose(); }
    }
}
