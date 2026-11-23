import type { TemperatureReadingDay } from "@/lib/types";

export type TemperatureField = "morning" | "evening";

export type ParsedTemperature =
  | { kind: "empty" }
  | { kind: "valid"; value: number }
  | { kind: "invalid" };

const TEMPERATURE_PATTERN = /^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)$/;

export function parseTemperatureInput(value: string): ParsedTemperature {
  const normalized = value.trim().replace(",", ".");
  if (normalized === "") {
    return { kind: "empty" };
  }
  if (!TEMPERATURE_PATTERN.test(normalized)) {
    return { kind: "invalid" };
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? { kind: "valid", value: parsed } : { kind: "invalid" };
}

export function readingAction(
  day: TemperatureReadingDay,
): "enter" | "complete" | "correct" {
  if (day.morning === null && day.evening === null) {
    return "enter";
  }
  if (day.morning === null || day.evening === null) {
    return "complete";
  }
  return "correct";
}
