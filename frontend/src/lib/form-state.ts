export type LoginState = {
  error?: string;
};

export const INITIAL_LOGIN_STATE: LoginState = {};

export type EquipmentFormState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_EQUIPMENT_FORM_STATE: EquipmentFormState = { status: "idle" };
