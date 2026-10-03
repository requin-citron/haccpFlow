export type LoginState = {
  error?: string;
};

export const INITIAL_LOGIN_STATE: LoginState = {};

export type CreateEquipmentState = {
  status: "idle" | "error" | "success";
  message?: string;
};

export const INITIAL_CREATE_EQUIPMENT_STATE: CreateEquipmentState = { status: "idle" };
