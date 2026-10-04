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

export type CleaningFrequency = "after_each_use" | "daily" | "weekly";

export type CleaningStatus = "overdue" | "due_today" | "upcoming";

export type CleaningRecordEditAction = "created" | "updated" | "deleted";

export type CleaningPlan = {
  id: string;
  name: string;
  frequency: CleaningFrequency;
  products: string | null;
  last_cleaning_date: string | null;
  next_due_date: string | null;
  created_at: string;
  updated_at: string;
};

export type CleaningRecord = {
  id: string;
  plan_id: string;
  cleaning_date: string;
  comment: string | null;
  performed_by_email: string | null;
  recorded_at: string;
  updated_at: string;
};

export type CleaningRecordEdit = {
  action: CleaningRecordEditAction;
  previous_cleaning_date: string | null;
  new_cleaning_date: string | null;
  previous_comment: string | null;
  new_comment: string | null;
  changed_by_email: string | null;
  changed_at: string;
};

export type CleaningScheduleEntry = {
  plan_id: string;
  name: string;
  frequency: CleaningFrequency;
  products: string | null;
  last_cleaning_date: string | null;
  next_due_date: string;
  status: CleaningStatus;
  days_late: number;
};

export type PasteurisationPhase = "preheating" | "holding" | "cooling";

export type PasteurisationPhaseEditAction = "created" | "updated";

export type PasteurisationPhaseSlot = {
  phase: PasteurisationPhase;
  started_at: string | null;
  ended_at: string | null;
  duration_minutes: number | null;
  target_temperature_celsius: number | null;
  observation: string | null;
};

export type PasteurisationBatch = {
  id: string;
  batch_date: string;
  product_name: string;
  lot_number: string;
  quantity: number;
  phases: PasteurisationPhaseSlot[];
  filled_phases: number;
  is_complete: boolean;
  created_at: string;
  updated_at: string;
};

export type PasteurisationPhaseEdit = {
  action: PasteurisationPhaseEditAction;
  previous_started_at: string | null;
  new_started_at: string | null;
  previous_ended_at: string | null;
  new_ended_at: string | null;
  previous_target_temperature_celsius: number | null;
  new_target_temperature_celsius: number | null;
  previous_observation: string | null;
  new_observation: string | null;
  changed_by_email: string | null;
  changed_at: string;
};
