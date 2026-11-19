using UnityEngine;

namespace Arvr
{
    /// <summary>A figure made of spheres, cylinders and a torso block, posed from landmarks. Y is up; the figure stands on the floor (y = 0).</summary>
    public class LandmarkFigure
    {
        const float JointSize = 0.09f, HighlightSize = 0.17f;
        readonly Transform root;
        readonly Transform[] joints = new Transform[PoseMath.JointIndices.Length];
        readonly Renderer[] jointRenderers = new Renderer[PoseMath.JointIndices.Length];
        readonly Transform[] bones = new Transform[PoseMath.Bones.Length];
        readonly Transform head, torso;
        readonly Color baseColor;

        public LandmarkFigure(string name, Color color)
        {
            baseColor = color;
            root = new GameObject(name).transform;
            for (int i = 0; i < joints.Length; i++) { joints[i] = Make(PrimitiveType.Sphere, color, JointSize); jointRenderers[i] = joints[i].GetComponent<Renderer>(); }
            for (int i = 0; i < bones.Length; i++) bones[i] = Make(PrimitiveType.Cylinder, color, 0.05f);
            head = Make(PrimitiveType.Sphere, color, 0.22f);
            torso = Make(PrimitiveType.Cube, Color.Lerp(color, Color.black, 0.45f), 1f);
            SetVisible(false);
        }

        Transform Make(PrimitiveType type, Color color, float size)
        {
            var go = GameObject.CreatePrimitive(type);
            Object.Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(root, false);
            go.transform.localScale = Vector3.one * size;
            go.GetComponent<Renderer>().material.color = color;
            return go.transform;
        }

        public void SetVisible(bool on) => root.gameObject.SetActive(on);

        /// <summary>Makes the joint at a landmark index larger and gives it a colour (for the exercising joint); a negative index clears it.</summary>
        public void Highlight(int landmarkIndex, Color color)
        {
            for (int i = 0; i < joints.Length; i++)
            {
                bool on = PoseMath.JointIndices[i] == landmarkIndex;
                jointRenderers[i].material.color = on ? color : baseColor;
                joints[i].localScale = Vector3.one * (on ? HighlightSize : JointSize);
            }
        }

        /// <summary>Normalised image coordinates to room units: about 2 tall; x is mirrored so the figure moves like a reflection.</summary>
        public static Vector3 ToRoom(Lm l, float xOffset) => new Vector3((0.5f - l.x) * 2f + xOffset, (1f - l.y) * 2f, -l.z * 1.2f);

        public void Apply(Lm[] lm, float xOffset)
        {
            if (lm == null) { SetVisible(false); return; }
            SetVisible(true);
            for (int i = 0; i < joints.Length; i++) joints[i].position = ToRoom(lm[PoseMath.JointIndices[i]], xOffset);
            for (int i = 0; i < bones.Length; i++)
            {
                var p = ToRoom(lm[PoseMath.Bones[i][0]], xOffset);
                var q = ToRoom(lm[PoseMath.Bones[i][1]], xOffset);
                var d = q - p;
                var t = bones[i];
                t.position = (p + q) * 0.5f;
                t.rotation = d.sqrMagnitude > 1e-8f ? Quaternion.FromToRotation(Vector3.up, d.normalized) : Quaternion.identity;
                t.localScale = new Vector3(0.05f, Mathf.Max(d.magnitude / 2f, 1e-3f), 0.05f); // a Unity cylinder is 2 units tall
            }
            head.position = ToRoom(lm[0], xOffset);

            // torso block between the shoulder line and the hip line
            var ls = ToRoom(lm[11], xOffset); var rs = ToRoom(lm[12], xOffset);
            var lh = ToRoom(lm[23], xOffset); var rh = ToRoom(lm[24], xOffset);
            var s = (ls + rs) * 0.5f; var h = (lh + rh) * 0.5f; var spine = s - h;
            torso.position = (s + h) * 0.5f;
            torso.rotation = spine.sqrMagnitude > 1e-8f ? Quaternion.FromToRotation(Vector3.up, spine.normalized) : Quaternion.identity;
            torso.localScale = new Vector3(Mathf.Max((ls - rs).magnitude * 0.85f, 0.1f), Mathf.Max(spine.magnitude, 0.1f), 0.12f);
        }
    }
}
