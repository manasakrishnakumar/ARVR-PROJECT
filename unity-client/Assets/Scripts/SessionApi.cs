using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace Arvr
{
    /// <summary>REST calls to the ARVR backend: create a session, complete it, read the recommendation.</summary>
    public static class SessionApi
    {
        [Serializable] public class Created { public string id, ws_key; }
        [Serializable] public class Metrics { public int counted_reps, target_reps, n_reps, n_reliable; public float quality, error_rate; }
        [Serializable] public class Recommendation { public string action; public int current_level, next_level; public string[] reasons; public string safety_note; public Metrics metrics; }
        [Serializable] public class Completed { public Recommendation recommendation; public bool saved_to_history; }

        /// <summary>Guest sessions need no account. isDemo marks synthetic input so it never feeds a user's history.</summary>
        public static IEnumerator Create(string baseUrl, string exerciseId, int level, bool isDemo, Action<Created> done)
        {
            var body = $"{{\"exercise_id\":\"{exerciseId}\",\"difficulty\":{level},\"is_demo\":{(isDemo ? "true" : "false")}}}";
            using (var req = Post(baseUrl + "/api/sessions", body))
            {
                yield return req.SendWebRequest();
                done(req.result == UnityWebRequest.Result.Success ? JsonUtility.FromJson<Created>(req.downloadHandler.text) : null);
            }
        }

        public static IEnumerator Complete(string baseUrl, string sessionId, Action<Completed> done)
        {
            using (var req = Post($"{baseUrl}/api/sessions/{sessionId}/complete", "{}"))
            {
                yield return req.SendWebRequest();
                done(req.result == UnityWebRequest.Result.Success ? JsonUtility.FromJson<Completed>(req.downloadHandler.text) : null);
            }
        }

        static UnityWebRequest Post(string url, string json)
        {
            var req = new UnityWebRequest(url, "POST") { uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json)), downloadHandler = new DownloadHandlerBuffer() };
            req.SetRequestHeader("Content-Type", "application/json");
            return req;
        }
    }
}
