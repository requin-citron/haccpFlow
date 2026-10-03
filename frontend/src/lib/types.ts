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

export type ReadingSlot = "morning" | "evening";

export type ReadingSource = "manual" | "sensor";

export type ReadingEditAction = "created" | "updated";

export type TemperatureReadingSlot = {
  temperature_celsius: number;
  is_compliant: boolean;
  source: ReadingSource;
  recorded_at: string;
  updated_at: string;
};

export type TemperatureReadingDay = {
  reading_date: string;
  morning: TemperatureReadingSlot | null;
  evening: TemperatureReadingSlot | null;
};

export type TemperatureReadingEdit = {
  slot: ReadingSlot;
  action: ReadingEditAction;
  previous_celsius: number | null;
  new_celsius: number;
  changed_by_email: string | null;
  changed_at: string;
};
