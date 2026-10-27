import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { Exercise } from "../types/api";

let cache: Exercise[] | null = null;

/** The exercise library is fixed data from the backend, so it is fetched once per page load. */
export function useExercises(): { exercises: Exercise[]; error: string | null; loading: boolean } {
  const [exercises, setExercises] = useState<Exercise[]>(cache ?? []);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(cache === null);

  useEffect(() => {
    if (cache) return;
    api.exercises()
      .then((e) => { cache = e; setExercises(e); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { exercises, error, loading };
}
