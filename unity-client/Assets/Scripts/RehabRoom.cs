using System.Collections;
using UnityEngine;

namespace Arvr
{
    /// <summary>
    /// Desktop 3D rehabilitation room. Attach this single component to an empty GameObject in an empty scene and press Play:
    /// it builds the room, a virtual trainer (elbow flexion), streams the angle to the ARVR backend, and shows the live results.
    ///
    /// Angle source: "Trainer demo" (synthetic sweep, flagged as a demo session) or a manual slider. This client does NOT do pose
    /// estimation: connecting a real pose source (for example a MediaPipe Unity plugin, or a relay from the web app) is future work.
    /// Research prototype; not a medical device.
    /// </summary>
    public class RehabRoom : MonoBehaviour
    {
        public string backendUrl = "http://127.0.0.1:8000";
        public string exerciseId = "elbow_flexion";
        public int level = 1;
        public float sendHz = 15f;

        enum Source { TrainerDemo, ManualSlider }
        Source source = Source.TrainerDemo;
        bool running;
        float t0, lastSend, manualAngle = 160f, angle = 160f;
        AnalysisClient client;
        SessionApi.Created session;
        SessionApi.Completed result;
        string phase = "waiting", feedback = "", status = "Press Start.";
        int reps, target;
        Transform forearmPivot;

        void Start()
        {
            BuildRoom();
            BuildTrainer();
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
            Camera.main.transform.position = new Vector3(0, 1.4f, -2.2f);
            Camera.main.transform.LookAt(new Vector3(0, 1.2f, 0));
        }

        /// <summary>Torso, a fixed upper arm hanging from the shoulder, and a forearm that pivots at the elbow.</summary>
        void BuildTrainer()
        {
            var torso = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            torso.transform.position = new Vector3(0, 1.2f, 0);
            torso.transform.localScale = new Vector3(0.35f, 0.45f, 0.2f);
            torso.GetComponent<Renderer>().material.color = new Color(0.98f, 0.75f, 0.14f);
            var upper = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            upper.transform.position = new Vector3(0.3f, 1.2f, 0);
            upper.transform.localScale = new Vector3(0.09f, 0.25f, 0.09f);
            upper.GetComponent<Renderer>().material.color = new Color(0.98f, 0.75f, 0.14f);
            var elbow = new GameObject("ElbowPivot").transform;
            elbow.position = new Vector3(0.3f, 0.95f, 0);
            forearmPivot = elbow;
            var fore = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            fore.transform.SetParent(elbow, false);
            fore.transform.localPosition = new Vector3(0, 0.22f, 0); // the forearm points up from the pivot at angle 0
            fore.transform.localScale = new Vector3(0.08f, 0.22f, 0.08f);
            fore.GetComponent<Renderer>().material.color = new Color(0.18f, 0.83f, 0.75f);
            ApplyAngle(angle);
        }

        /// <summary>Elbow angle = angle between the upper arm (up from the elbow) and the forearm. 180 is straight.</summary>
        void ApplyAngle(float deg) => forearmPivot.localRotation = Quaternion.Euler(0, 0, 180f - deg);

        IEnumerator StartSession()
        {
            status = "Creating session...";
            yield return SessionApi.Create(backendUrl, exerciseId, level, source == Source.TrainerDemo, s => session = s);
            client = new AnalysisClient();
            var task = client.ConnectAsync(backendUrl, exerciseId, level, session?.id, session?.ws_key);
            while (!task.IsCompleted) yield return null;
            status = client.Connected ? "Streaming to the backend." : $"Backend not reachable ({client.LastError}); the room still runs.";
            result = null; reps = 0; t0 = Time.time; running = true;
        }

        IEnumerator StopSession()
        {
            running = false;
            client?.Dispose(); client = null;
            if (session != null && reps > 0) yield return SessionApi.Complete(backendUrl, session.id, c => result = c);
            session = null;
            status = "Stopped.";
        }

        void Update()
        {
            if (!running) return;
            var t = Time.time - t0;
            angle = source == Source.TrainerDemo ? 105f + 55f * Mathf.Cos(2f * Mathf.PI * t / 4f) : manualAngle; // 50..160 degrees
            ApplyAngle(angle);
            if (client != null && Time.time - lastSend >= 1f / sendHz) { lastSend = Time.time; client.Send(t, angle); }
            while (client != null && client.TryDequeue(out var m))
            {
                if (m.type == "hello") target = m.target_reps;
                else if (m.type == "state") { phase = m.phase; reps = m.counted_reps; }
                else if (m.type == "rep") feedback = $"{m.label} ({m.score:F2}): {m.feedback}";
                else if (m.type == "error") status = m.detail;
            }
        }

        void OnGUI()
        {
            GUILayout.BeginArea(new Rect(12, 12, 420, 520), GUI.skin.box);
            GUILayout.Label("ARVR 3D room (research prototype, not a medical device)");
            GUILayout.Label($"{exerciseId}  ·  level {level}  ·  backend {backendUrl}");
            if (!running)
            {
                source = (Source)GUILayout.Toolbar((int)source, new[] { "Trainer demo (synthetic)", "Manual slider" });
                if (GUILayout.Button("Start")) StartCoroutine(StartSession());
            }
            else
            {
                if (source == Source.ManualSlider) manualAngle = GUILayout.HorizontalSlider(manualAngle, 40f, 180f);
                if (GUILayout.Button("Stop and save")) StartCoroutine(StopSession());
            }
            GUILayout.Label($"Repetitions: {reps} / {(target > 0 ? target.ToString() : "-")}   Phase: {phase}   Angle: {angle:F0}°");
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

        void OnDestroy() => client?.Dispose();
    }
}
