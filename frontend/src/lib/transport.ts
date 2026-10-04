import type { CheckpointStatus } from "@/lib/status";

/** A checkpoint is complete once it carries both a time and a temperature. */
export function checkpointState(
  time: string | null,
  temperature: number | null,
): CheckpointStatus {
  if (time !== null && temperature !== null) {
    return "complete";
  }
  return time !== null || temperature !== null ? "partial" : "empty";
}
