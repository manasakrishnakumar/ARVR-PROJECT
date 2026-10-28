using System;
using System.Collections.Concurrent;
using System.Globalization;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace Arvr
{
    /// <summary>
    /// Streams joint-angle samples to the ARVR backend (WS /api/ws/analysis) and queues the replies for the main thread.
    /// The backend, not Unity, counts repetitions and assesses quality: the same pipeline the web app uses.
    /// </summary>
    public class AnalysisClient : IDisposable
    {
        /// <summary>One flat class for every message type (hello, state, rep, error); unused fields stay at their defaults.</summary>
        [Serializable]
        public class Msg
        {
            public string type, phase, label, feedback, explanation, detail;
            public int counted_reps, target_reps;
            public float angle, progress, score;
            public bool counted, saving;
        }

        readonly ConcurrentQueue<Msg> inbox = new ConcurrentQueue<Msg>();
        readonly SemaphoreSlim sendLock = new SemaphoreSlim(1, 1);
        ClientWebSocket ws;
        CancellationTokenSource cts;

        public bool Connected => ws != null && ws.State == WebSocketState.Open;
        public string LastError { get; private set; }
        public bool TryDequeue(out Msg m) => inbox.TryDequeue(out m);

        public async Task ConnectAsync(string httpBase, string exerciseId, int level, string sessionId = null, string key = null)
        {
            var wsBase = httpBase.Replace("https://", "wss://").Replace("http://", "ws://").TrimEnd('/');
            var url = $"{wsBase}/api/ws/analysis?exercise_id={Uri.EscapeDataString(exerciseId)}&difficulty={level}";
            if (!string.IsNullOrEmpty(sessionId)) url += $"&session_id={Uri.EscapeDataString(sessionId)}&key={Uri.EscapeDataString(key ?? "")}";
            cts = new CancellationTokenSource();
            ws = new ClientWebSocket();
            try
            {
                await ws.ConnectAsync(new Uri(url), cts.Token);
                _ = ReceiveLoop(cts.Token);
            }
            catch (Exception e)
            {
                LastError = e.Message; // surfaced in the HUD; the scene keeps running without the backend
            }
        }

        async Task ReceiveLoop(CancellationToken ct)
        {
            var buf = new byte[16 * 1024];
            var sb = new StringBuilder();
            try
            {
                while (ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
                {
                    sb.Clear();
                    WebSocketReceiveResult r;
                    do
                    {
                        r = await ws.ReceiveAsync(new ArraySegment<byte>(buf), ct);
                        if (r.MessageType == WebSocketMessageType.Close) { LastError = $"closed by server ({(int?)ws.CloseStatus})"; return; }
                        sb.Append(Encoding.UTF8.GetString(buf, 0, r.Count));
                    } while (!r.EndOfMessage);
                    try { inbox.Enqueue(JsonUtility.FromJson<Msg>(sb.ToString())); }
                    catch (Exception) { /* ignore a malformed message */ }
                }
            }
            catch (Exception e) { if (!ct.IsCancellationRequested) LastError = e.Message; }
        }

        /// <summary>Send one sample. angle = null means the landmarks were not reliable (the backend never guesses).</summary>
        public async void Send(float tSeconds, float? angle)
        {
            if (!Connected) return;
            var a = angle.HasValue ? angle.Value.ToString("F2", CultureInfo.InvariantCulture) : "null";
            var json = $"{{\"t\":{tSeconds.ToString("F3", CultureInfo.InvariantCulture)},\"angle\":{a}}}";
            var bytes = Encoding.UTF8.GetBytes(json);
            await sendLock.WaitAsync();
            try { await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, cts.Token); }
            catch (Exception e) { LastError = e.Message; }
            finally { sendLock.Release(); }
        }

        public void Dispose()
        {
            try { cts?.Cancel(); ws?.Dispose(); } catch (Exception) { }
        }
    }
}
