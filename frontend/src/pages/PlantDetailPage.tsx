import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RefreshIcon from "@mui/icons-material/Refresh";
import { api } from "../api";
import { RuleCard } from "../components/RuleCard";
import { PlantImage } from "../components/PlantImage";

export function PlantDetailPage({
  plantId,
  onBack,
}: {
  plantId: string;
  onBack: () => void;
}) {
  const queryClient = useQueryClient();
  const { data: plant, isLoading } = useQuery({
    queryKey: ["plant", plantId],
    queryFn: () => api.getPlant(plantId),
  });
  const { data: agents } = useQuery({
    queryKey: ["ha-agents"],
    queryFn: () => api.listHaAgents(),
  });

  const [regenerating, setRegenerating] = useState(false);
  const [regenError, setRegenError] = useState("");
  const [agentId, setAgentId] = useState("");

  const handleRegenerate = async () => {
    if (!plant || !agentId) return;
    setRegenerating(true);
    setRegenError("");
    try {
      await api.regeneratePlant(plant.id, plant.name, agentId);
      queryClient.invalidateQueries({ queryKey: ["plant", plantId] });
      queryClient.invalidateQueries({ queryKey: ["relevant-now"] });
    } catch (e: unknown) {
      setRegenError(e instanceof Error ? e.message : String(e));
    } finally {
      setRegenerating(false);
    }
  };

  if (isLoading) return <Typography>Laden…</Typography>;
  if (!plant) return <Typography>Pflanze nicht gefunden</Typography>;

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={onBack} sx={{ mb: 2 }}>
        Zurück
      </Button>

      <PlantImage url={plant.image_url} alt={plant.name} height={280} borderRadius={2} />

      <Typography variant="h4" gutterBottom>
        {plant.name}
      </Typography>
      {plant.botanical_name && (
        <Typography
          variant="subtitle1"
          color="text.secondary"
          sx={{ fontStyle: "italic" }}
          gutterBottom
        >
          {plant.botanical_name}
        </Typography>
      )}
      <Typography variant="body1" sx={{ mb: 3 }}>
        {plant.description}
      </Typography>

      {(plant.water_needs || plant.fertilizer_needs) && (
        <Box sx={{ mb: 3 }}>
          {plant.water_needs && (
            <Typography variant="body2" sx={{ mb: 1 }}>
              💧 <strong>Wasserbedarf:</strong> {plant.water_needs}
            </Typography>
          )}
          {plant.fertilizer_needs && (
            <Typography variant="body2" sx={{ mb: 1 }}>
              🧪 <strong>Düngung:</strong> {plant.fertilizer_needs}
            </Typography>
          )}
        </Box>
      )}

      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
        <Typography variant="h5">Pflege-Regeln</Typography>
        {agents && agents.length > 0 && (
          <>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>KI-Agent</InputLabel>
              <Select
                value={agentId}
                label="KI-Agent"
                onChange={(e) => setAgentId(e.target.value)}
              >
                {agents.map((a) => (
                  <MenuItem key={a.agent_id} value={a.agent_id}>
                    {a.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="outlined"
              size="small"
              startIcon={regenerating ? <CircularProgress size={16} /> : <RefreshIcon />}
              disabled={!agentId || regenerating}
              onClick={handleRegenerate}
            >
              {regenerating ? "Generiere…" : "Neu generieren"}
            </Button>
          </>
        )}
      </Stack>

      {regenError && (
        <Alert severity="error" sx={{ mb: 2 }}>{regenError}</Alert>
      )}

      {plant.rules.map((rule) => (
        <RuleCard key={rule.id} rule={rule} />
      ))}
    </Box>
  );
}
