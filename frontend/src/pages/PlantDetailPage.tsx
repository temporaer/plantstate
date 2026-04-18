import { useQuery } from "@tanstack/react-query";
import { Box, Button, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
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
  const { data: plant, isLoading } = useQuery({
    queryKey: ["plant", plantId],
    queryFn: () => api.getPlant(plantId),
  });

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

      <Typography variant="h5" gutterBottom>
        Pflege-Regeln
      </Typography>
      {plant.rules.map((rule) => (
        <RuleCard key={rule.id} rule={rule} />
      ))}
    </Box>
  );
}
