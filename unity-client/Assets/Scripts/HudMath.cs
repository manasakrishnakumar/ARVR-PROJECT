using UnityEngine;

namespace Arvr
{
    /// <summary>Small pure helpers for the HUD and the figure highlight, kept apart from the MonoBehaviour so they can be unit tested.</summary>
    public static class HudMath
    {
        public static readonly Color Rest = new Color(0.64f, 0.70f, 0.75f);
        public static readonly Color Moving = new Color(0.98f, 0.75f, 0.14f);
        public static readonly Color Target = new Color(0.29f, 0.87f, 0.50f);

        /// <summary>Share of the target repetitions done, 0 to 1 (0 when there is no target yet).</summary>
        public static float ProgressFraction(int reps, int target) => target <= 0 ? 0f : Mathf.Clamp01((float)reps / target);

        /// <summary>Colour of the exercising joint for a counter phase: grey at rest, amber while moving, green at the target.</summary>
        public static Color PhaseColor(string phase)
        {
            switch (phase)
            {
                case "target": return Target;
                case "moving_out":
                case "returning": return Moving;
                default: return Rest;
            }
        }

        /// <summary>Readable phase text for the HUD.</summary>
        public static string PhaseLabel(string phase)
        {
            switch (phase)
            {
                case "moving_out": return "Moving out";
                case "target": return "At target";
                case "returning": return "Returning";
                case "rest": return "Rest";
                default: return string.IsNullOrEmpty(phase) ? "Waiting" : phase;
            }
        }
    }
}
