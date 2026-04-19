import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  FormControlLabel,
  IconButton,
  Popover,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import HelpOutlinedIcon from "@mui/icons-material/HelpOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { api } from "../api";
import type { CompletedTaskItem, OutlookItem, Tip, WeatherStatus } from "../api";
import { RelevantTaskCard } from "../components/RelevantTaskCard";
import { TASK_TYPE_EMOJI, TASK_TYPE_TEXT } from "../labels";

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
  const [expanded, setExpanded] = useState(false);
  // Count active events for the summary line
  const activeEvents = Object.entries(weather.events).filter(([, v]) => v);

  return (
    <Card
      sx={{ mb: 3, cursor: "pointer" }}
      onClick={() => setExpanded((prev) => !prev)}
    >
      <CardContent sx={{ pb: expanded ? undefined : "12px !important" }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
            <Typography variant="h6" sx={{ mr: 1 }}>
              {SEASON_LABELS[weather.season] ?? weather.season}
            </Typography>
            {activeEvents.map(([event]) => (
              <Chip
                key={event}
                label={EVENT_LABELS[event] ?? event}
                size="small"
                color="success"
                variant="outlined"
              />
            ))}
            {activeEvents.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                Keine aktiven Wetterereignisse
              </Typography>
            )}
          </Stack>
          {expanded ? <ExpandLessIcon color="action" /> : <ExpandMoreIcon color="action" />}
        </Stack>

        <Collapse in={expanded}>
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1, mt: 2 }}>
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

          {weather.history.length > 0 && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" gutterBottom>
                Letzte Tage
              </Typography>
              <Stack direction="row" spacing={2} sx={{ overflowX: "auto", pb: 1 }}>
                {weather.history.slice(-5).map((d) => (
                  <Box key={d.date} sx={{ textAlign: "center", minWidth: 70, opacity: 0.75 }}>
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
        </Collapse>
      </CardContent>
    </Card>
  );
}

function TipsSection({ tips }: { tips: Tip[] }) {
  const [expanded, setExpanded] = useState(false);
  if (tips.length === 0) return null;
  return (
    <Box sx={{ mb: 3 }}>
      <Stack spacing={1}>
        {tips.map((tip, i) => (
          <Card
            key={i}
            variant="outlined"
            sx={{ bgcolor: "action.hover", cursor: "pointer" }}
            onClick={() => setExpanded((prev) => !prev)}
          >
            <CardContent sx={{ py: 1, "&:last-child": { pb: 1 } }}>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {tip.icon} {tip.title}
              </Typography>
              <Collapse in={expanded}>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {tip.detail}
                </Typography>
              </Collapse>
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
  const [openSeasons, setOpenSeasons] = useState<Record<string, boolean>>({});

  const toggle = (season: string) =>
    setOpenSeasons((prev) => ({ ...prev, [season]: !prev[season] }));

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
      {sortedSeasons.map((season) => {
        const expanded = !!openSeasons[season];
        const count = bySeason[season].length;
        const readyCount = bySeason[season].filter((i) => i.ready).length;
        return (
          <Box key={season} sx={{ mb: 1 }}>
            <Stack
              direction="row"
              sx={{ alignItems: "center", cursor: "pointer", py: 0.5 }}
              onClick={() => toggle(season)}
            >
              {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              <Typography variant="subtitle1" sx={{ fontWeight: 600, ml: 0.5, flexGrow: 1 }}>
                {SEASON_LABELS[season] ?? season}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {readyCount > 0 ? `${readyCount}/${count} bereit` : `${count} Aufgaben`}
              </Typography>
            </Stack>
            <Collapse in={expanded}>
              <Stack spacing={1} sx={{ mt: 0.5, mb: 1 }}>
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
            </Collapse>
          </Box>
        );
      })}
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

function CompletedCard({ item }: { item: CompletedTaskItem }) {
  const emoji = TASK_TYPE_EMOJI[item.task_type] ?? "📋";
  const text = TASK_TYPE_TEXT[item.task_type] ?? item.task_type;
  const status = item.task.status === "skipped" ? "⏭️ Übersprungen" : "✅ Erledigt";
  const when = item.completed_at
    ? new Date(item.completed_at).toLocaleDateString("de-DE", {
        day: "numeric", month: "short",
      })
    : null;

  return (
    <Card sx={{ mb: 1, borderLeft: "4px solid", borderLeftColor: "grey.400" }}>
      <CardContent sx={{ py: 1, "&:last-child": { pb: 1 } }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
          <Typography variant="body2">
            {emoji} {text} — {item.plant_name}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            {when && (
              <Typography variant="caption" color="text.disabled">{when}</Typography>
            )}
            <Chip label={status} size="small" variant="outlined" sx={{ borderColor: "grey.400" }} />
          </Stack>
        </Stack>
      </CardContent>
    </Card>
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
      queryClient.invalidateQueries({ queryKey: ["completed-tasks"] });
    },
  });

  const snoozeMutation = useMutation({
    mutationFn: (id: string) => api.snoozeTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["relevant-now"] });
    },
  });

  const [showCompleted, setShowCompleted] = useState(false);
  const completedQuery = useQuery({
    queryKey: ["completed-tasks"],
    queryFn: api.getCompletedTasks,
    enabled: showCompleted,
  });

  const isLoading = weatherQuery.isLoading || relevantQuery.isLoading;
  const hasHAError =
    weatherQuery.error?.message?.includes("503") ||
    relevantQuery.error?.message?.includes("503");

  // Scroll to task if deep-linked from Lovelace card
  const [deepLinkedTaskId, setDeepLinkedTaskId] = useState<string | null>(null);
  useEffect(() => {
    if (!relevantQuery.data) return;
    const taskId = localStorage.getItem("plant-state-task");
    if (taskId) {
      localStorage.removeItem("plant-state-task");
      setDeepLinkedTaskId(taskId);
      requestAnimationFrame(() => {
        const el = document.getElementById(`task-${taskId}`);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.style.outline = "2px solid #4caf50";
          setTimeout(() => { el.style.outline = ""; }, 2000);
        }
      });
    }
  }, [relevantQuery.data]);

  return (
    <Box>
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
          initialExpanded={item.task.id === deepLinkedTaskId}
          onNavigateToPlant={onNavigateToPlant}
          onComplete={(id) => completeMutation.mutate(id)}
          onSnooze={(id) => snoozeMutation.mutate(id)}
        />
      ))}

      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={showCompleted}
            onChange={(_, v) => setShowCompleted(v)}
          />
        }
        label="Erledigte anzeigen"
        sx={{ mt: 1, mb: 1, color: "text.secondary" }}
      />

      {showCompleted && completedQuery.data && completedQuery.data.length > 0 && (
        <Box sx={{ opacity: 0.5 }}>
          {completedQuery.data.map((item) => (
            <CompletedCard key={item.task.id} item={item} />
          ))}
        </Box>
      )}

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
