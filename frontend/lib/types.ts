export type UserRole = "super_admin" | "admin" | "operator" | "client";
export type SiteStatus = "normal" | "warning" | "critical" | "disconnected";
export type AlertSeverity = "info" | "warning" | "critical";
export type AlertCategory = "threshold" | "communication" | "data_missing" | "device_offline";
export type AlertStatus = "open" | "acknowledged" | "resolved";
export type QualityFlag = "good" | "suspect" | "bad" | "missing";
export type SensorType =
  | "inclinometer" | "settlement" | "crack" | "lvdt" | "piezometer"
  | "water_level" | "load_cell" | "strain_gauge" | "vibration"
  | "sound_level" | "total_station" | "gnss" | "temperature" | "other";
export type IngestionMode = "modbus" | "mqtt" | "manual";

export interface User {
  id: string;
  email: string;
  name: string;
  phone?: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface SiteSummary {
  id: string;
  code: string;
  name: string;
  status: SiteStatus;
  latitude?: number | null;
  longitude?: number | null;
  sensor_count: number;
  online_device_count: number;
  open_alerts: number;
  last_data_at?: string | null;
}

export interface Site extends Omit<SiteSummary, "sensor_count" | "online_device_count" | "open_alerts"> {
  address?: string | null;
  manager_user_id?: string | null;
  customer_user_id?: string | null;
  metadata: Record<string, unknown>;
  last_data_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Threshold {
  id: string;
  level: "warning" | "critical";
  min_value?: number | null;
  max_value?: number | null;
  is_active: boolean;
}

export interface Sensor {
  id: string;
  device_id: string;
  code: string;
  name: string;
  serial_number?: string | null;
  sensor_type: SensorType;
  unit: string;
  ingestion_mode: IngestionMode;
  modbus_register_address?: number | null;
  modbus_register_count?: number | null;
  modbus_data_type?: string | null;
  calibration_offset: number;
  calibration_scale: number;
  initial_baseline?: number | null;
  expected_interval_seconds: number;
  is_active: boolean;
  last_reading_at?: string | null;
  metadata: Record<string, unknown>;
  thresholds: Threshold[];
  created_at: string;
}

export interface SystemSetting {
  key: string;
  value: string;
  updated_at: string;
}

export interface IngestResult {
  accepted: number;
  rejected: number;
  errors?: string[];
}

export interface Device {
  id: string;
  site_id: string;
  code: string;
  name: string;
  serial_number?: string | null;
  device_type: string;
  primary_protocol: string;
  ip_address?: string | null;
  port?: number | null;
  is_online: boolean;
  last_heartbeat_at?: string | null;
  config: Record<string, unknown>;
  created_at: string;
}

export interface Alert {
  id: string;
  ts: string;
  site_id: string;
  sensor_id?: string | null;
  device_id?: string | null;
  severity: AlertSeverity;
  category: AlertCategory;
  status: AlertStatus;
  title: string;
  message: string;
  triggered_value?: number | null;
  threshold_value?: number | null;
  notified: boolean;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
}

export interface TimeSeriesPoint {
  ts: string;
  value: number;
  quality?: QualityFlag;
}

export interface TimeSeriesResponse {
  sensor_id: string;
  points: TimeSeriesPoint[];
  count: number;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
