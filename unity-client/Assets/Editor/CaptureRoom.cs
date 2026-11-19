using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Arvr.Editor
{
    /// <summary>Opens the room, enters Play mode, saves a Game-view screenshot after a few seconds and exits.
    /// Run (not batch mode, it needs graphics): Unity -projectPath ... -executeMethod Arvr.Editor.CaptureRoom.Run
    /// The state is kept in SessionState because entering Play mode reloads scripts.</summary>
    [InitializeOnLoad]
    public static class CaptureRoom
    {
        const string Flag = "arvr.capture", Out = "capture_room.png";
        static double start = -1;
        static bool shot, started;

        static CaptureRoom()
        {
            if (SessionState.GetBool(Flag, false)) EditorApplication.update += Tick;
        }

        public static void Run()
        {
            SessionState.SetBool(Flag, true);
            EditorSceneManager.OpenScene("Assets/Scenes/RehabRoom.unity");
            EditorApplication.EnterPlaymode();
        }

        static void Tick()
        {
            if (!EditorApplication.isPlaying) return;
            if (start < 0) start = EditorApplication.timeSinceStartup;
            double t = EditorApplication.timeSinceStartup - start;
            if (!started && t > 6)
            {
                started = true; // press Start on the trainer demo (private coroutine, via reflection)
                var room = Object.FindFirstObjectByType<Arvr.RehabRoom>();
                var m = typeof(Arvr.RehabRoom).GetMethod("StartSession", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                if (room != null && m != null) room.StartCoroutine((System.Collections.IEnumerator)m.Invoke(room, null));
            }
            if (!shot && t > 20) { ScreenCapture.CaptureScreenshot(Out); shot = true; }
            if (shot && t > 24) { SessionState.SetBool(Flag, false); EditorApplication.Exit(0); }
        }
    }
}
