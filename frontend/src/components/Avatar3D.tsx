import { Canvas, useFrame } from "@react-three/fiber";
import { Component, useMemo, useRef, type MutableRefObject, type ReactNode } from "react";
import * as THREE from "three";
import { MIN_CONFIDENCE } from "../pose/angles";
import { SKELETON, type Landmark } from "../pose/types";

const JOINTS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28];

/** Normalised image coordinates -> room units: about 2 tall, mirrored so the avatar moves like the user's reflection. */
function toRoom(l: Landmark, xOffset: number): THREE.Vector3 {
  return new THREE.Vector3((0.5 - l.x) * 2 + xOffset, (1 - l.y) * 2 - 0.9, -l.z * 1.2);
}

/** A figure made of spheres and cylinders, updated every frame from a ref (no React re-render per frame). */
function Figure({ source, color, xOffset }: { source: MutableRefObject<Landmark[] | null>; color: string; xOffset: number }) {
  const joints = useRef<(THREE.Mesh | null)[]>([]);
  const bones = useRef<(THREE.Mesh | null)[]>([]);
  const head = useRef<THREE.Mesh>(null);
  const up = useMemo(() => new THREE.Vector3(0, 1, 0), []);
  useFrame(() => {
    const lm = source.current;
    const show = !!lm;
    joints.current.forEach((m) => m && (m.visible = show));
    bones.current.forEach((m) => m && (m.visible = show));
    if (head.current) head.current.visible = show;
    if (!lm) return;
    JOINTS.forEach((i, k) => {
      const m = joints.current[k];
      if (m) { m.position.copy(toRoom(lm[i], xOffset)); (m.material as THREE.MeshStandardMaterial).opacity = lm[i].visibility >= MIN_CONFIDENCE ? 1 : 0.3; }
    });
    SKELETON.forEach(([a, b], k) => {
      const m = bones.current[k];
      if (!m) return;
      const p = toRoom(lm[a], xOffset), q = toRoom(lm[b], xOffset), d = q.clone().sub(p), len = d.length();
      m.position.copy(p.clone().add(q).multiplyScalar(0.5));
      m.scale.set(1, Math.max(len, 1e-3), 1);
      m.quaternion.setFromUnitVectors(up, d.normalize());
    });
    if (head.current) {
      const n = toRoom(lm[0], xOffset);
      head.current.position.copy(n);
    }
  });
  return (
    <group>
      {JOINTS.map((_, k) => (
        <mesh key={k} ref={(el) => { joints.current[k] = el; }} visible={false}>
          <sphereGeometry args={[0.045, 16, 16]} /><meshStandardMaterial color={color} transparent />
        </mesh>
      ))}
      {SKELETON.map((_, k) => (
        <mesh key={k} ref={(el) => { bones.current[k] = el; }} visible={false}>
          <cylinderGeometry args={[0.025, 0.025, 1, 10]} /><meshStandardMaterial color={color} />
        </mesh>
      ))}
      <mesh ref={head} visible={false}><sphereGeometry args={[0.11, 20, 20]} /><meshStandardMaterial color={color} /></mesh>
    </group>
  );
}

function Room() {
  return (
    <>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.9, 0]}><planeGeometry args={[8, 6]} /><meshStandardMaterial color="#2b3a42" /></mesh>
      <gridHelper args={[8, 16, "#46606b", "#33454d"]} position={[0, -0.899, 0]} />
      <mesh position={[0, 1, -2.2]}><planeGeometry args={[8, 4]} /><meshStandardMaterial color="#1c2a31" /></mesh>
      <mesh position={[-4, 1, 0]} rotation={[0, Math.PI / 2, 0]}><planeGeometry args={[6, 4]} /><meshStandardMaterial color="#223138" /></mesh>
    </>
  );
}

/** If WebGL or the 3D scene fails, the rest of the page (pose pipeline, counters, feedback) keeps working. */
export class SceneBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

export default function Scene3D({ user, trainer }: { user: MutableRefObject<Landmark[] | null>; trainer: MutableRefObject<Landmark[] | null> }) {
  return (
    <Canvas camera={{ position: [0, 0.6, 3.4], fov: 50 }} style={{ height: 420, borderRadius: 10, background: "#0b1218" }}>
      <ambientLight intensity={0.7} />
      <directionalLight position={[2, 4, 3]} intensity={1.1} />
      <Room />
      <Figure source={trainer} color="#fbbf24" xOffset={-1.1} />
      <Figure source={user} color="#2dd4bf" xOffset={1.1} />
    </Canvas>
  );
}
