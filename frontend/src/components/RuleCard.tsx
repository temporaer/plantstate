import {
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import type { Rule } from "../api";
import { TASK_TYPE_LABELS } from "../labels";

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

const EVENT_CRITERIA: Record<string, string> = {
  frost_risk_active: "min(nächste 5 Tage T_min) ≤ 1 °C",
  frost_risk_passed: "min(letzte 7 Tage T_min) > 1 °C UND min(nächste 5 Tage T_min) > 1 °C",
  sustained_mild_nights: "≥ 4 von 5 Nächten T_min ≥ 8 °C",
  warm_spell: "≥ 3 von 5 Tagen T_max ≥ 20 °C",
  heatwave: "3 aufeinanderfolgende Tage T_max ≥ 30 °C",
  dry_spell: "3 aufeinanderfolgende Tage Niederschlag < 1 mm",
  persistent_rain: "3 aufeinanderfolgende Tage Niederschlag ≥ 5 mm",
};

export function RuleCard({ rule, debug = false }: { rule: Rule; debug?: boolean }) {
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {TASK_TYPE_LABELS[rule.task_type] ?? rule.task_type}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {rule.explanation.summary}
        </Typography>

        {debug && (
          <Card variant="outlined" sx={{ mb: 1.5, bgcolor: "action.hover" }}>
            <CardContent sx={{ py: 0.75, "&:last-child": { pb: 0.75 } }}>
              <Typography variant="caption" sx={{ fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
                Saisons: [{rule.planning_seasons.join(", ")}]
                {"\n"}Benötigt: [{rule.activation.required_events.join(", ") || "—"}]
                {"\n"}Verboten: [{rule.activation.forbidden_events.join(", ") || "—"}]
                {"\n"}Wiederholung: alle {rule.recurrence_years} Jahr(e)
                {rule.priority ? `\nPriorität: ${rule.priority}` : ""}
              </Typography>
            </CardContent>
          </Card>
        )}

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
              {debug && EVENT_CRITERIA[event] && (
                <Typography
                  variant="caption"
                  sx={{
                    display: "block",
                    mt: 0.5,
                    fontFamily: "monospace",
                    color: "text.disabled",
                  }}
                >
                  ⚙️ {EVENT_CRITERIA[event]}
                </Typography>
              )}
            </CardContent>
          </Card>
        ))}
      </CardContent>
    </Card>
  );
}
