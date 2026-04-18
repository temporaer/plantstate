/** German labels for task types and other enums. */

export const TASK_TYPE_LABELS: Record<string, string> = {
  sow: "🌱 Aussaat",
  transplant: "🌿 Auspflanzen",
  harvest: "🍎 Ernte",
  prune_maintenance: "✂️ Pflegeschnitt",
  prune_structural: "🪚 Formschnitt",
  cut_back: "✂️ Rückschnitt",
  deadhead: "🌸 Verblühtes entfernen",
  thin_fruit: "🍏 Fruchtausdünnung",
  remove_deadwood: "🪵 Totholz entfernen",
};

/** Task type text without emoji (for composite titles). */
export const TASK_TYPE_TEXT: Record<string, string> = {
  sow: "Aussaat",
  transplant: "Auspflanzen",
  harvest: "Ernte",
  prune_maintenance: "Pflegeschnitt",
  prune_structural: "Formschnitt",
  cut_back: "Rückschnitt",
  deadhead: "Verblühtes entfernen",
  thin_fruit: "Fruchtausdünnung",
  remove_deadwood: "Totholz entfernen",
};

export function taskTypeLabel(type: string): string {
  return TASK_TYPE_LABELS[type] ?? type;
}

export function taskTypeText(type: string): string {
  return TASK_TYPE_TEXT[type] ?? type;
}
