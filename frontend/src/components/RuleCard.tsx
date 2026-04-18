import {
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import type { Rule } from "../api";

const TASK_TYPE_LABELS: Record<string, string> = {
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

const SEASON_LABELS: Record<string, string> = {
  early_spring: "Vorfrühling",
  spring: "Frühling",
  early_summer: "Frühsommer",
  summer: "Sommer",
  late_summer: "Spätsommer",
  autumn: "Herbst",
  winter: "Winter",
};

const EVENT_LABELS: Record<string, string> = {
  frost_risk_active: "🥶 Frostgefahr",
  frost_risk_passed: "☀️ Frostfrei",
  sustained_mild_nights: "🌙 Milde Nächte",
  warm_spell: "🌡️ Wärmephase",
  heatwave: "🔥 Hitzewelle",
  dry_spell: "☀️ Trockenheit",
  persistent_rain: "🌧️ Dauerregen",
};

export function RuleCard({ rule }: { rule: Rule }) {
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {TASK_TYPE_LABELS[rule.task_type] ?? rule.task_type}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {rule.explanation.summary}
        </Typography>

        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1, my: 1.5 }}>
          {rule.planning_seasons.map((s) => (
            <Chip
              key={s}
              label={SEASON_LABELS[s] ?? s}
              size="small"
              color="primary"
              variant="outlined"
            />
          ))}
        </Stack>

        {rule.activation.required_events.length > 0 && (
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1, mb: 1 }}>
            {rule.activation.required_events.map((e) => (
              <Chip
                key={e}
                label={`✅ ${EVENT_LABELS[e] ?? e}`}
                size="small"
                color="success"
                variant="outlined"
              />
            ))}
          </Stack>
        )}

        {rule.activation.forbidden_events.length > 0 && (
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1, mb: 1 }}>
            {rule.activation.forbidden_events.map((e) => (
              <Chip
                key={e}
                label={`🚫 ${EVENT_LABELS[e] ?? e}`}
                size="small"
                color="error"
                variant="outlined"
              />
            ))}
          </Stack>
        )}

        <Typography variant="body2" sx={{ mt: 1.5 }}>
          <strong>Warum:</strong> {rule.explanation.why}
        </Typography>
        <Typography variant="body2">
          <strong>Wie:</strong> {rule.explanation.how}
        </Typography>

        {Object.entries(rule.activation.event_explanations).map(([event, expl]) => (
          <Card key={event} variant="outlined" sx={{ mt: 1.5, bgcolor: "grey.50" }}>
            <CardContent sx={{ py: 1, "&:last-child": { pb: 1 } }}>
              <Typography variant="caption" color="text.secondary">
                {EVENT_LABELS[event] ?? event}
              </Typography>
              <Typography variant="body2">{expl.why}</Typography>
              <Typography variant="body2" color="text.secondary">
                {expl.how}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </CardContent>
    </Card>
  );
}
