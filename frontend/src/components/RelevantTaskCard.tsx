import {
  Card,
  CardActionArea,
  CardContent,
  Typography,
} from "@mui/material";
import type { RelevantNowItem } from "../api";

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

export function RelevantTaskCard({
  item,
  onNavigateToPlant,
}: {
  item: RelevantNowItem;
  onNavigateToPlant?: (plantId: string) => void;
}) {
  const emoji = TASK_TYPE_EMOJI[item.task_type] ?? "📋";
  const isClickable = !!onNavigateToPlant && !!item.task.plant_id;

  const content = (
    <CardContent>
      <Typography variant="h6">
        {emoji} {item.plant_name}
      </Typography>
      <Typography variant="subtitle2" color="primary" gutterBottom>
        {item.explanation_summary}
      </Typography>
      <Typography variant="body2" sx={{ mt: 1 }}>
        <strong>Warum:</strong> {item.explanation_why}
      </Typography>
      <Typography variant="body2">
        <strong>Wie:</strong> {item.explanation_how}
      </Typography>
    </CardContent>
  );

  return (
    <Card sx={{ mb: 2, borderLeft: "4px solid", borderLeftColor: "primary.main" }}>
      {isClickable ? (
        <CardActionArea onClick={() => onNavigateToPlant(item.task.plant_id)}>
          {content}
        </CardActionArea>
      ) : (
        content
      )}
    </Card>
  );
}
