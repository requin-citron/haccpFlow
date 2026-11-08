import {
  MODULE_KEYS,
  type EnabledModules,
  type ModuleKey,
} from "@/lib/modules";

const MODULE_ENV_VARS: Record<ModuleKey, string> = {
  equipment: "MODULE_EQUIPMENT",
  readings: "MODULE_READINGS",
  cleaning: "MODULE_CLEANING",
  pasteurisation: "MODULE_PASTEURISATION",
  transport: "MODULE_TRANSPORT",
  cashSessions: "MODULE_CASH_SESSIONS",
  export: "MODULE_EXPORT",
  documents: "MODULE_DOCUMENTS",
  history: "MODULE_HISTORY",
  users: "MODULE_USERS",
};

function readModuleFlag(key: ModuleKey): boolean {
  const envName = MODULE_ENV_VARS[key];
  const value = process.env[envName];
  if (value === undefined || value === "") {
    return true;
  }
  if (value === "0") {
    return false;
  }
  if (value === "1") {
    return true;
  }
  throw new Error(`${envName} doit valoir 0 ou 1 (valeur reçue : « ${value} »).`);
}

export function getEnabledModules(): EnabledModules {
  const enabled = {} as EnabledModules;
  for (const key of MODULE_KEYS) {
    enabled[key] = readModuleFlag(key);
  }

  // Equipment owns the configurations used by readings, transport
  // (vehicles) and cash sessions (registers). Keep it visible while any of
  // those dependants is active.
  enabled.equipment =
    enabled.equipment ||
    enabled.readings ||
    enabled.transport ||
    enabled.cashSessions;
  return enabled;
}
