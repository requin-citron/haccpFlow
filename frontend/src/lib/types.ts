export type EquipmentType = "fridge" | "freezer";

export type Equipment = {
  id: string;
  name: string;
  type: EquipmentType;
  min_temperature_celsius: number;
  max_temperature_celsius: number;
  location: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type UserRole = "admin" | "operator";

export type CurrentUser = {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
};
