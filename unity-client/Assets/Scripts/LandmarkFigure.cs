using UnityEngine;

namespace Arvr
{
    /// <summary>A figure made of spheres and cylinders, posed from landmarks. Y is up; the figure stands on the floor (y = 0).</summary>
    public class LandmarkFigure
    {
        readonly Transform root;
        readonly Transform[] joints = new Transform[PoseMath.JointIndices.Length];
        readonly Transform[] bones = new Transform[PoseMath.Bones.Length];
        readonly Transform head;

        public LandmarkFigure(string name, Color color)
        {
            root = new GameObject(name).transform;
            for (int i = 0; i < joints.Length; i++) joints[i] = Make(PrimitiveType.Sphere, color, 0.09f);
            for (int i = 0; i < bones.Length; i++) bones[i] = Make(PrimitiveType.Cylinder, color, 0.05f);
            head = Make(PrimitiveType.Sphere, color, 0.22f);
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
        }
    }
}
