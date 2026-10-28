#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace Arvr.EditorTools
{
    /// <summary>Menu "ARVR > Build Windows player" (also runnable in batch mode) writes unity-client/Builds/Windows/ARVR-Unity.exe.</summary>
    public static class BuildScript
    {
        [MenuItem("ARVR/Build Windows player")]
        public static void BuildWindows()
        {
            var options = new BuildPlayerOptions
            {
                scenes = new[] { "Assets/Scenes/RehabRoom.unity" },
                locationPathName = "Builds/Windows/ARVR-Unity.exe",
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            };
            var report = BuildPipeline.BuildPlayer(options);
            Debug.Log($"ARVR build: {report.summary.result}, {report.summary.totalSize / (1024 * 1024)} MB, errors {report.summary.totalErrors}");
            if (Application.isBatchMode) EditorApplication.Exit(report.summary.result == BuildResult.Succeeded ? 0 : 1);
        }
    }
}
#endif
