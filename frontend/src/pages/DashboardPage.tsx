import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import { api } from "../api";
import type { WeatherStatus } from "../api";
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
              color={active ? "success" : "default"}
              variant={active ? "filled" : "outlined"}
              size="small"
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

export function DashboardPage() {
  const weatherQuery = useQuery({
    queryKey: ["weather"],
    queryFn: api.getWeatherStatus,
    refetchInterval: 5 * 60 * 1000, // refresh every 5 min
  });

  const relevantQuery = useQuery({
    queryKey: ["relevant-now"],
    queryFn: api.getRelevantNowLive,
    refetchInterval: 5 * 60 * 1000,
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

      <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>
        Jetzt relevant
      </Typography>

      {relevantQuery.data && relevantQuery.data.length === 0 && (
        <Typography color="text.secondary">
          Aktuell sind keine Aufgaben fällig. Das Wetter oder die Jahreszeit
          passen noch nicht.
        </Typography>
      )}

      {relevantQuery.data?.map((item) => (
        <RelevantTaskCard key={item.task.id} item={item} />
      ))}
    </Box>
  );
}
