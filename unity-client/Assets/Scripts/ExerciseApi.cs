using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

namespace Arvr
{
    /// <summary>The exercise library comes from the backend (GET /api/exercises), so Unity and the web app always agree.</summary>
    public static class ExerciseApi
    {
        [Serializable]
        public class Exercise
        {
            public string id, name;
            public string[] landmarks; // [A, B, C]; the angle is measured at B
            public float start_angle_deg, target_angle_deg;
        }

        [Serializable] class Wrapper { public Exercise[] items; }

        /// <summary>JsonUtility cannot read a top-level array, so the array is wrapped first.</summary>
        public static Exercise[] Parse(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) return new Exercise[0];
            try { return JsonUtility.FromJson<Wrapper>("{\"items\":" + json + "}")?.items ?? new Exercise[0]; }
            catch (Exception) { return new Exercise[0]; }
        }

        public static IEnumerator Load(string baseUrl, Action<Exercise[]> done)
        {
            using (var req = UnityWebRequest.Get(baseUrl.TrimEnd('/') + "/api/exercises"))
            {
                yield return req.SendWebRequest();
                done(req.result == UnityWebRequest.Result.Success ? Parse(req.downloadHandler.text) : new Exercise[0]);
            }
        }
    }
}
