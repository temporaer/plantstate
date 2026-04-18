import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import CloseIcon from "@mui/icons-material/Close";
import { api } from "../api";
import type { Plant } from "../api";
import { PlantImage } from "../components/PlantImage";
import { RuleCard } from "../components/RuleCard";
import { taskTypeLabel } from "../labels";

export function PlantListPage({
  onSelect,
}: {
  onSelect: (id: string) => void;
}) {
  const { data: plants, isLoading, error } = useQuery({
    queryKey: ["plants"],
    queryFn: api.listPlants,
  });
  const [filter, setFilter] = useState("");
  const [rulesPlant, setRulesPlant] = useState<Plant | null>(null);

  const filtered = useMemo(() => {
    if (!plants) return [];
    if (!filter.trim()) return plants;
    const q = filter.toLowerCase();
    return plants.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.botanical_name?.toLowerCase().includes(q) ?? false) ||
        p.description.toLowerCase().includes(q),
    );
  }, [plants, filter]);

  if (isLoading) return <Typography>Laden…</Typography>;
  if (error) return <Typography color="error">Fehler beim Laden</Typography>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        🌿 Meine Pflanzen
      </Typography>
      <TextField
        fullWidth
        size="small"
        placeholder="Pflanze suchen…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        sx={{ mb: 2 }}
      />
      <Grid container spacing={2}>
        {filtered.map((plant: Plant) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={plant.id}>
            <Card>
              <CardActionArea onClick={() => onSelect(plant.id)}>
                <PlantImage url={plant.image_url} alt={plant.name} height={160} />
                <CardContent>
                  <Typography variant="h6">{plant.name}</Typography>
                  {plant.botanical_name && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ fontStyle: "italic" }}
                    >
                      {plant.botanical_name}
                    </Typography>
                  )}
                  <Typography variant="body2" sx={{ mt: 1, mb: 1.5 }}>
                    {plant.description}
                  </Typography>
                  <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5 }}>
                    {plant.rules.map((r) => (
                      <Chip
                        key={r.id}
                        label={taskTypeLabel(r.task_type)}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                  </Stack>
                </CardContent>
              </CardActionArea>
              <Box sx={{ display: "flex", justifyContent: "flex-end", px: 1, pb: 0.5 }}>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    setRulesPlant(plant);
                  }}
                  aria-label="Regeln anzeigen"
                >
                  <InfoOutlinedIcon fontSize="small" />
                </IconButton>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog
        open={!!rulesPlant}
        onClose={() => setRulesPlant(null)}
        maxWidth="sm"
        fullWidth
        scroll="paper"
      >
        {rulesPlant && (
          <>
            <DialogTitle sx={{ pr: 6 }}>
              {rulesPlant.name} — Pflege-Regeln
              <IconButton
                onClick={() => setRulesPlant(null)}
                sx={{ position: "absolute", right: 8, top: 8 }}
                aria-label="Schließen"
              >
                <CloseIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent dividers>
              {rulesPlant.rules.map((rule) => (
                <RuleCard key={rule.id} rule={rule} />
              ))}
            </DialogContent>
          </>
        )}
      </Dialog>
    </Box>
  );
}
