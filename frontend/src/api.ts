const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface Plant {
  id: string;
  name: string;
  botanical_name: string | null;
  description: string;
  language: string;
  rules: Rule[];
}

export interface Rule {
  id: string;
  task_type: string;
  planning_seasons: string[];
  activation: {
    required_events: string[];
    forbidden_events: string[];
    event_explanations: Record<string, { why: string; how: string }>;
  };
  recurrence_years: number;
  explanation: {
    summary: string;
    why: string;
    how: string;
  };
}

export interface Task {
  id: string;
  plant_id: string;
  rule_id: string;
  task_type: string;
  status: string;
  year: number;
}

export interface RelevantNowItem {
  task: Task;
  plant_name: string;
  task_type: string;
  explanation_summary: string;
  explanation_why: string;
  explanation_how: string;
}

export interface OutlookItem {
  task: Task;
  plant_name: string;
  task_type: string;
  planning_seasons: string[];
  explanation_summary: string;
  in_planning_window: boolean;
  conditions_met: boolean;
  blocking: string[];
  ready: boolean;
}

export interface WeatherStatus {
  season: string;
  events: Record<string, boolean>;
  forecast: DailyWeather[];
  history: DailyWeather[];
}

export interface DailyWeather {
  date: string;
  temp_min: number;
  temp_max: number;
  precipitation_mm: number;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  listPlants: () => apiFetch<Plant[]>("/plants"),
  getPlant: (id: string) => apiFetch<Plant>(`/plants/${id}`),
  createPlant: (plant: object) =>
    apiFetch<Plant>("/plants", { method: "POST", body: JSON.stringify(plant) }),
  deletePlant: (id: string) =>
    apiFetch<void>(`/plants/${id}`, { method: "DELETE" }),
  completeTask: (id: string) =>
    apiFetch<Task>(`/tasks/${id}/complete`, { method: "POST" }),
  skipTask: (id: string) =>
    apiFetch<Task>(`/tasks/${id}/skip`, { method: "POST" }),
  getWeatherStatus: () => apiFetch<WeatherStatus>("/dashboard/weather"),
  getOutlook: () => apiFetch<OutlookItem[]>("/dashboard/outlook"),
  getRelevantNowLive: () =>
    apiFetch<RelevantNowItem[]>("/dashboard/relevant-now-live"),
  syncCalendar: () =>
    apiFetch<{ synced: number; calendar: string }>("/sync/calendar", {
      method: "POST",
    }),
};
