using UnityEngine.XR;

namespace Arvr
{
    /// <summary>
    /// Reports whether an XR (VR) device is active. The project includes the OpenXR packages, but XR is OFF by default
    /// (Edit > Project Settings > XR Plug-in Management) and no headset has been tested: with none attached the room runs as a normal
    /// desktop scene. See unity-client/README.md, "Enabling VR".
    /// </summary>
    public static class XrStatus
    {
        public static bool Active => XRSettings.isDeviceActive;

        public static string Describe() =>
            XRSettings.isDeviceActive ? $"XR device active: {XRSettings.loadedDeviceName} (untested)" : "XR: no headset active (desktop mode)";
    }
}
