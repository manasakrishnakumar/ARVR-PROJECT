#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Arvr.EditorTools
{
    /// <summary>Menu "ARVR > Create room scene" (also runnable in batch mode) builds Assets/Scenes/RehabRoom.unity with the RehabRoom component attached.</summary>
    public static class CreateRoomScene
    {
        [MenuItem("ARVR/Create room scene")]
        public static void Create()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            new GameObject("ARVR Rehab Room").AddComponent<RehabRoom>();
            System.IO.Directory.CreateDirectory("Assets/Scenes");
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/RehabRoom.unity");
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene("Assets/Scenes/RehabRoom.unity", true) };
            Debug.Log("ARVR: created Assets/Scenes/RehabRoom.unity");
        }
    }
}
#endif
