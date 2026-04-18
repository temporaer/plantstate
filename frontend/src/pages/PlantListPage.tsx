import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import { api } from "../api";
import type { Plant } from "../api";

const TASK_TYPE_EMOJI: Record<string, string> = {
  sow: "🌱",
  transplant: "🌿",
  harvest: "🍎",
  prune_maintenance: "✂️",
  prune_structural: "🪚",
  cut_back: "✂️",
  deadhead: "🌸",
  thin_fruit: "🍏",
  remove_deadwood: "🪵",
};

export function PlantListPage({
  onSelect,
}: {
  onSelect: (id: string) => void;
}) {
  const { data: plants, isLoading, error } = useQuery({
    queryKey: ["plants"],
    queryFn: api.listPlants,
  });

  if (isLoading) return <Typography>Laden…</Typography>;
  if (error) return <Typography color="error">Fehler beim Laden</Typography>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        🌿 Meine Pflanzen
      </Typography>
      <Grid container spacing={2}>
        {plants?.map((plant: Plant) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={plant.id}>
            <Card>
              <CardActionArea onClick={() => onSelect(plant.id)}>
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
                        label={`${TASK_TYPE_EMOJI[r.task_type] ?? ""} ${r.task_type}`}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                  </Stack>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
