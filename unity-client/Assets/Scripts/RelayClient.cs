using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace Arvr
{
    /// <summary>
    /// Subscribes to a room on the local backend relay (WS /api/ws/relay/{room}) to show the live pose the browser publishes.
    /// The browser does the pose estimation; Unity only receives landmark numbers. Only the newest frame is kept.
    /// </summary>
    public class RelayClient : IDisposable
    {
        [Serializable]
        public class Frame
        {
            public float[] lm; // 33 x [x, y, z, visibility]
            public float angle;
            public bool has_angle;
            public string phase, feedback, label;
            public int counted_reps, target_reps;
        }

        readonly object gate = new object();
        Frame latest;
        long latestSeq, readSeq;
        ClientWebSocket ws;
        CancellationTokenSource cts;

        public bool Connected => ws != null && ws.State == WebSocketState.Open;
        public string LastError { get; private set; }

        public static string BuildUrl(string httpBase, string room)
        {
            var wsBase = httpBase.Replace("https://", "wss://").Replace("http://", "ws://").TrimEnd('/');
            return $"{wsBase}/api/ws/relay/{Uri.EscapeDataString(room)}?role=subscriber";
        }

        public static Frame ParseFrame(string json)
        {
            try
            {
                var f = JsonUtility.FromJson<Frame>(json);
                return f != null && f.lm != null && f.lm.Length == PoseMath.LandmarkCount * 4 ? f : null; // ignore control messages such as "joined"
            }
            catch (Exception) { return null; }
        }

        public async Task ConnectAsync(string httpBase, string room)
        {
            cts = new CancellationTokenSource();
            ws = new ClientWebSocket();
            try
            {
                await ws.ConnectAsync(new Uri(BuildUrl(httpBase, room)), cts.Token);
                _ = ReceiveLoop(cts.Token);
            }
            catch (Exception e) { LastError = e.Message; }
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
                        if (r.MessageType == WebSocketMessageType.Close) { LastError = $"closed by server: {ws.CloseStatusDescription}"; return; }
                        sb.Append(Encoding.UTF8.GetString(buf, 0, r.Count));
                    } while (!r.EndOfMessage);
                    var f = ParseFrame(sb.ToString());
                    if (f != null) lock (gate) { latest = f; latestSeq++; }
                }
            }
            catch (Exception e) { if (!ct.IsCancellationRequested) LastError = e.Message; }
        }

        /// <summary>The newest frame if a new one arrived since the last call.</summary>
        public bool TryGetLatest(out Frame f)
        {
            lock (gate)
            {
                f = latest;
                if (latestSeq == readSeq) return false;
                readSeq = latestSeq;
                return true;
            }
        }

        public void Dispose()
        {
            try { cts?.Cancel(); ws?.Dispose(); } catch (Exception) { }
        }
    }
}
