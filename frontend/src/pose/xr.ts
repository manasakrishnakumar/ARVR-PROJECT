export type VrSupport = "checking" | "supported" | "unsupported";

interface XrNavigator { xr?: { isSessionSupported?: (mode: string) => Promise<boolean> } }

/** Whether this browser and device report support for an immersive VR session. Reports support only; it does not start one. */
export async function detectVr(nav: XrNavigator = navigator as unknown as XrNavigator): Promise<Exclude<VrSupport, "checking">> {
  const xr = nav.xr;
  if (!xr?.isSessionSupported) return "unsupported";
  try { return (await xr.isSessionSupported("immersive-vr")) ? "supported" : "unsupported"; } catch { return "unsupported"; }
}

/** Where the room is placed so a standing user (local-floor reference space, origin at the floor) faces the trainer and avatar 2.5 m ahead.
 *  The desktop scene's floor is at y = -0.9, so the group is lifted by 0.9. */
export const VR_ROOM_OFFSET: [number, number, number] = [0, 0.9, -2.5];

/** The text shown on the floating in-VR panel. */
export function hudText(counted: number, target: number, phase: string, feedback: string): string[] {
  return [`${counted}/${target || "-"} reps`, phase.replace("_", " "), feedback].filter(Boolean);
}
