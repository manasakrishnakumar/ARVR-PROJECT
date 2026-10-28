/** Short spoken cues for sessions where the user is away from the screen (AR and 3D room pages). */
const CUE: Record<string, string> = {
  insufficient_range: "Go a little further.",
  incomplete_repetition: "Complete the whole movement.",
  too_fast: "Slow down.",
  uncontrolled: "Move more steadily.",
  insufficient_data: "I could not see that one clearly.",
};

export function repCue(rep: { counted: boolean; label: string }, countedSoFar: number, target: number): string {
  if (!rep.counted) return CUE[rep.label] ?? "";
  const done = target > 0 && countedSoFar >= target;
  const base = rep.label === "acceptable" ? `${countedSoFar}.` : `${countedSoFar}. ${CUE[rep.label] ?? ""}`.trim();
  return done ? `${base} That is all your repetitions. Well done.` : base;
}

export function speak(text: string): void {
  if (!text || typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}
