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

export type HistoryEntity =
  | "temperature_reading"
  | "cleaning_record"
  | "pasteurisation_phase"
  | "transport";

export type HistoryAction = "created" | "updated" | "deleted";

export type HistoryChange = {
  field: string;
  label: string;
  previous: string | null;
  new: string | null;
};

export type HistoryEntry = {
  id: string;
  occurred_at: string;
  entity: HistoryEntity;
  action: HistoryAction;
  actor_email: string | null;
  target_id: string;
  subject: string;
  detail: string;
  changes: HistoryChange[];
};

export type Vehicle = {
  id: string;
  name: string | null;
  plate: string | null;
  created_at: string;
  updated_at: string;
};

export type TransportVehicle = {
  /** Null when the transport used a free label for a one-off carrier. */
  id: string | null;
  name: string;
  plate: string | null;
};

export type Transport = {
  id: string;
  transport_date: string;
  place: string;
  product_name: string;
  lot_number: string | null;
  vehicle: TransportVehicle;
  departure_time: string | null;
  departure_temperature_celsius: number | null;
  arrival_time: string | null;
  arrival_temperature_celsius: number | null;
  observation: string | null;
  is_complete: boolean;
  created_at: string;
  updated_at: string;
};

export type CashRegisterCounts = {
  coins_1_cent: number;
  coins_2_cent: number;
  coins_5_cent: number;
  coins_10_cent: number;
  coins_20_cent: number;
  coins_50_cent: number;
  coins_1_euro: number;
  coins_2_euro: number;
  notes_5_euro: number;
  notes_10_euro: number;
  notes_20_euro: number;
  notes_50_euro: number;
};

export type CashRegister = CashRegisterCounts & {
  id: string;
  name: string;
  total_cents: number;
  created_at: string;
  updated_at: string;
};

export type CashExpenseKind = "professional" | "personal";

export type CashExpense = {
  id: string;
  kind: CashExpenseKind;
  name: string;
  quantity: number;
  unit_price_cents: number;
  /** Percentage, serialised as a decimal string by the API ("20.00"). */
  vat_rate: string;
  total_cents: number;
  created_at: string;
  updated_at: string;
};

export type CashSession = {
  id: string;
  cash_register_id: string;
  cash_register_name: string;
  session_date: string;
  opening_counts: CashRegisterCounts;
  closing_counts: CashRegisterCounts | null;
  opening_total_cents: number;
  closing_total_cents: number | null;
  expenses_total_cents: number;
  expenses_professional_total_cents: number;
  expenses_personal_total_cents: number;
  expenses: CashExpense[];
  is_open: boolean;
  opened_by_email: string | null;
  closed_by_email: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
};
