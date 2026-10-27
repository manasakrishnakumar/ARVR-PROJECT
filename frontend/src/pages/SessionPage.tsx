import { useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useExercises } from "../hooks/useExercises";
import PoseLab from "./PoseLab";

export default function SessionPage() {
  const { exercises, loading, error } = useExercises();
  const { user } = useAuth();
  const [params] = useSearchParams();
  if (loading) return <p className="muted">Loading exercises...</p>;
  if (error) return <p className="error" role="alert">Could not load exercises: {error}</p>;
  return <PoseLab exercises={exercises} user={user} initialExerciseId={params.get("exercise") ?? undefined} />;
}
