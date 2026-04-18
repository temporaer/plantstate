import {
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import type { RelevantNowItem } from "../api";
import { TASK_TYPE_LABELS } from "../labels";

const PRIORITY_CONFIG: Record<string, { label: string; color: "error" | "default" | "info" }> = {
  high: { label: "Wichtig", color: "error" },
  normal: { label: "Normal", color: "default" },
  low: { label: "Nebensache", color: "info" },
};

const BORDER_COLOR: Record<string, string> = {
  high: "error.main",
  normal: "primary.main",
  low: "grey.400",
};

export function RelevantTaskCard({
  item,
  onNavigateToPlant,
}: {
  item: RelevantNowItem;
  onNavigateToPlant?: (plantId: string) => void;
}) {
  const taskLabel = TASK_TYPE_LABELS[item.task_type] ?? item.task_type;
  const emoji = taskLabel.split(" ")[0] ?? "📋";
  const isClickable = !!onNavigateToPlant && !!item.task.plant_id;
  const prio = PRIORITY_CONFIG[item.priority] ?? PRIORITY_CONFIG.normal;

  const content = (
    <CardContent>
      <Stack direction="row" spacing={1} sx={{ mb: 0.5, alignItems: "center" }}>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          {emoji} {item.plant_name}
        </Typography>
        <Chip label={taskLabel} size="small" variant="outlined" />
        {item.priority !== "normal" && (
          <Chip label={prio.label} color={prio.color} size="small" />
        )}
      </Stack>
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
    <Card sx={{ mb: 2, borderLeft: "4px solid", borderLeftColor: BORDER_COLOR[item.priority] ?? "primary.main" }}>
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
