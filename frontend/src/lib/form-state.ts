export type LoginState = {
  error?: string;
};

export const INITIAL_LOGIN_STATE: LoginState = {};

export type EquipmentFormState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_EQUIPMENT_FORM_STATE: EquipmentFormState = { status: "idle" };

export type ReadingFormState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_READING_FORM_STATE: ReadingFormState = { status: "idle" };

export type CleaningPlanFormState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_CLEANING_PLAN_FORM_STATE: CleaningPlanFormState = { status: "idle" };

export type CleaningRecordFormState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_CLEANING_RECORD_FORM_STATE: CleaningRecordFormState = { status: "idle" };

export type PasteurisationFormState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_PASTEURISATION_FORM_STATE: PasteurisationFormState = { status: "idle" };

export type VehicleFormState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_VEHICLE_FORM_STATE: VehicleFormState = { status: "idle" };

export type TransportFormState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_TRANSPORT_FORM_STATE: TransportFormState = { status: "idle" };
