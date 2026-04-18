import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Popover,
  Stack,
  Typography,
} from "@mui/material";
import HelpOutlinedIcon from "@mui/icons-material/HelpOutlined";
import { api } from "../api";
import type { OutlookItem, Tip, WeatherStatus } from "../api";
import { RelevantTaskCard } from "../components/RelevantTaskCard";

const SEASON_LABELS: Record<string, string> = {
  early_spring: "🌱 Vorfrühling",
  spring: "🌷 Frühling",
  early_summer: "☀️ Frühsommer",
  summer: "🌻 Sommer",
  late_summer: "🍂 Spätsommer",
  autumn: "🍁 Herbst",
  winter: "❄️ Winter",
};

const EVENT_LABELS: Record<string, string> = {
  frost_risk_active: "🥶 Frostgefahr",
  frost_risk_passed: "☀️ Frostfrei",
  sustained_mild_nights: "🌙 Milde Nächte",
  warm_spell: "🌡️ Wärmephase",
  heatwave: "🔥 Hitzewelle",
  dry_spell: "💧 Trockenheit",
  persistent_rain: "🌧️ Dauerregen",
};

function WeatherCard({ weather }: { weather: WeatherStatus }) {
  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          🌤️ Wetter & Jahreszeit
        </Typography>
        <Typography variant="body1" sx={{ mb: 1.5 }}>
          Saison: <strong>{SEASON_LABELS[weather.season] ?? weather.season}</strong>
        </Typography>
        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
          {Object.entries(weather.events).map(([event, active]) => (
            <Chip
              key={event}
              label={EVENT_LABELS[event] ?? event}
              size="small"
              variant="outlined"
              sx={active
                ? { borderColor: "success.main", color: "success.main" }
                : { borderColor: "grey.300", color: "text.disabled" }
              }
            />
          ))}
        </Stack>

        {weather.forecast.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" gutterBottom>
              Vorhersage
            </Typography>
            <Stack direction="row" spacing={2} sx={{ overflowX: "auto", pb: 1 }}>
              {weather.forecast.slice(0, 5).map((d) => (
                <Box key={d.date} sx={{ textAlign: "center", minWidth: 70 }}>
                  <Typography variant="caption" sx={{ display: "block" }}>
                    {new Date(d.date).toLocaleDateString("de-DE", { weekday: "short" })}
                  </Typography>
                  <Typography variant="body2">
                    {d.temp_min.toFixed(0)}° / {d.temp_max.toFixed(0)}°
                  </Typography>
                  {d.precipitation_mm > 0 && (
                    <Typography variant="caption" color="primary">
                      {d.precipitation_mm.toFixed(1)} mm
                    </Typography>
                  )}
                </Box>
              ))}
            </Stack>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function TipsSection({ tips }: { tips: Tip[] }) {
  if (tips.length === 0) return null;
  return (
    <Box sx={{ mb: 3 }}>
      <Stack spacing={1}>
        {tips.map((tip, i) => (
          <Card key={i} variant="outlined" sx={{ bgcolor: "action.hover" }}>
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {tip.icon} {tip.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {tip.detail}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Box>
  );
}

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

const BLOCKING_LABELS: Record<string, string> = {
  season: "Andere Jahreszeit",
  "waiting:frost_risk_passed": "Warte auf frostfreie Nächte",
  "waiting:sustained_mild_nights": "Warte auf milde Nächte (≥8°C)",
  "waiting:warm_spell": "Warte auf Wärmephase",
  "waiting:frost_risk_active": "Warte auf Frost",
  "blocked:frost_risk_active": "Frostgefahr aktiv",
  "blocked:heatwave": "Hitzewelle aktiv",
  "blocked:persistent_rain": "Dauerregen aktiv",
};

function OutlookSection({ items }: { items: OutlookItem[] }) {
  // Group by season (use first planning season)
  const bySeason: Record<string, OutlookItem[]> = {};
  for (const item of items) {
    const season = item.planning_seasons[0] ?? "unknown";
    if (!bySeason[season]) bySeason[season] = [];
    bySeason[season].push(item);
  }

  const seasonOrder = [
    "early_spring", "spring", "early_summer", "summer",
    "late_summer", "autumn", "winter",
  ];
  const sortedSeasons = Object.keys(bySeason).sort(
    (a, b) => seasonOrder.indexOf(a) - seasonOrder.indexOf(b)
  );

  return (
    <Box>
      {sortedSeasons.map((season) => (
        <Box key={season} sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            {SEASON_LABELS[season] ?? season}
          </Typography>
          <Stack spacing={1}>
            {bySeason[season].map((item) => (
              <Card
                key={item.task.id}
                variant="outlined"
                sx={{
                  opacity: item.ready ? 1 : 0.75,
                  borderLeft: item.ready
                    ? "4px solid #4caf50"
                    : item.in_planning_window
                    ? "4px solid #ff9800"
                    : "4px solid #bdbdbd",
                }}
              >
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Stack
                    direction="row"
                    spacing={1}
                    sx={{ alignItems: "center", flexWrap: "wrap", gap: 0.5 }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {item.plant_name}
                    </Typography>
                    {item.priority === "high" && (
                      <Chip label="Wichtig" size="small" variant="outlined" sx={{ borderColor: "error.main", color: "error.main" }} />
                    )}
                    {item.priority === "low" && (
                      <Chip label="Nebensache" size="small" variant="outlined" sx={{ borderColor: "info.main", color: "info.main" }} />
                    )}
                    <Chip
                      label={TASK_TYPE_LABELS[item.task_type] ?? item.task_type}
                      size="small"
                      variant="outlined"
                      sx={item.ready ? { borderColor: "success.main", color: "success.main" } : { borderColor: "grey.400", color: "text.secondary" }}
                    />
                    {item.ready && (
                      <Chip label="✅ Bereit" size="small" variant="outlined" sx={{ borderColor: "success.main", color: "success.main" }} />
                    )}
                    {!item.ready && item.blocking.map((b) => (
                      <Chip
                        key={b}
                        label={BLOCKING_LABELS[b] ?? b}
                        size="small"
                        variant="outlined"
                        sx={{ borderColor: b === "season" ? "grey.400" : "warning.main", color: b === "season" ? "text.secondary" : "warning.main" }}
                      />
                    ))}
                  </Stack>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.5 }}
                  >
                    {item.explanation_summary}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </Box>
      ))}
    </Box>
  );
}

function LegendPopover() {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  return (
    <>
      <IconButton
        size="small"
        onClick={(e) => setAnchor(anchor ? null : e.currentTarget)}
        aria-label="Legende anzeigen"
        sx={{ ml: 0.5 }}
      >
        <HelpOutlinedIcon fontSize="small" />
      </IconButton>
      <Popover
        open={!!anchor}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        slotProps={{ paper: { sx: { p: 2, maxWidth: 320 } } }}
      >
        <Typography variant="subtitle2" gutterBottom>
          Dringlichkeit (berechnet)
        </Typography>
        <Stack spacing={0.5} sx={{ mb: 1.5 }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Chip label="🔴 Akut" size="small" variant="outlined" sx={{ borderColor: "#d32f2f", color: "#d32f2f" }} />
            <Typography variant="caption">Jetzt handeln — Zeitfenster schließt sich</Typography>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Chip label="🟡 Bald" size="small" variant="outlined" sx={{ borderColor: "#ed6c02", color: "#ed6c02" }} />
            <Typography variant="caption">Bereit, aber noch etwas Zeit</Typography>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Chip label="⚪ Entspannt" size="small" variant="outlined" sx={{ borderColor: "#9e9e9e", color: "#9e9e9e" }} />
            <Typography variant="caption">Breites Zeitfenster</Typography>
          </Stack>
        </Stack>
        <Typography variant="subtitle2" gutterBottom>
          Wichtigkeit (fest pro Regel)
        </Typography>
        <Stack spacing={0.5}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Chip label="Wichtig" size="small" variant="outlined" sx={{ borderColor: "error.main", color: "error.main" }} />
            <Typography variant="caption">Schadet der Pflanze wenn's ausfällt</Typography>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Chip label="Nebensache" size="small" variant="outlined" sx={{ borderColor: "info.main", color: "info.main" }} />
            <Typography variant="caption">Optisch / kosmetisch, kein Schaden</Typography>
          </Stack>
        </Stack>
      </Popover>
    </>
  );
}

export function DashboardPage({
  onNavigateToPlant,
}: {
  onNavigateToPlant?: (plantId: string) => void;
}) {
  const weatherQuery = useQuery({
    queryKey: ["weather"],
    queryFn: api.getWeatherStatus,
    refetchInterval: 5 * 60 * 1000,
  });

  const tipsQuery = useQuery({
    queryKey: ["tips"],
    queryFn: api.getTips,
    refetchInterval: 10 * 60 * 1000,
  });

  const relevantQuery = useQuery({
    queryKey: ["relevant-now"],
    queryFn: api.getRelevantNowLive,
    refetchInterval: 5 * 60 * 1000,
  });

  const outlookQuery = useQuery({
    queryKey: ["outlook"],
    queryFn: api.getOutlook,
    refetchInterval: 10 * 60 * 1000,
  });

  const queryClient = useQueryClient();

  const completeMutation = useMutation({
    mutationFn: api.completeTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["relevant-now"] });
      queryClient.invalidateQueries({ queryKey: ["outlook"] });
    },
  });

  const skipMutation = useMutation({
    mutationFn: api.skipTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["relevant-now"] });
      queryClient.invalidateQueries({ queryKey: ["outlook"] });
    },
  });

  const isLoading = weatherQuery.isLoading || relevantQuery.isLoading;
  const hasHAError =
    weatherQuery.error?.message?.includes("503") ||
    relevantQuery.error?.message?.includes("503");

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        📋 Dashboard
      </Typography>

      {isLoading && <CircularProgress />}

      {hasHAError && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Home Assistant ist nicht konfiguriert. Setze HA_BASE_URL und HA_TOKEN
          in der .env Datei.
        </Alert>
      )}

      {weatherQuery.data && <WeatherCard weather={weatherQuery.data} />}

      {tipsQuery.data && tipsQuery.data.length > 0 && (
        <>
          <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>
            💡 Tipps & Hinweise
          </Typography>
          <TipsSection tips={tipsQuery.data} />
        </>
      )}

      <Stack direction="row" sx={{ alignItems: "center", mt: 2, mb: 1 }}>
        <Typography variant="h5">
          Jetzt relevant
        </Typography>
        <LegendPopover />
      </Stack>

      {relevantQuery.data && relevantQuery.data.length === 0 && (
        <Typography color="text.secondary">
          Aktuell sind keine Aufgaben fällig. Das Wetter oder die Jahreszeit
          passen noch nicht.
        </Typography>
      )}

      {relevantQuery.data?.map((item) => (
        <RelevantTaskCard
          key={item.task.id}
          item={item}
          onNavigateToPlant={onNavigateToPlant}
          onComplete={(id) => completeMutation.mutate(id)}
          onSkip={(id) => skipMutation.mutate(id)}
        />
      ))}

      <Divider sx={{ my: 3 }} />

      <Typography variant="h5" gutterBottom>
        🗓️ Jahresausblick
      </Typography>

      {outlookQuery.isLoading && <CircularProgress size={24} />}

      {outlookQuery.data && outlookQuery.data.length === 0 && (
        <Typography color="text.secondary">
          Keine Aufgaben geplant. Füge Pflanzen hinzu, um den Ausblick zu
          sehen.
        </Typography>
      )}

      {outlookQuery.data && outlookQuery.data.length > 0 && (
        <OutlookSection items={outlookQuery.data} />
      )}
    </Box>
  );
}
