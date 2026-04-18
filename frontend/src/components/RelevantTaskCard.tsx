import {
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import SkipNextOutlinedIcon from "@mui/icons-material/SkipNextOutlined";
import type { RelevantNowItem } from "../api";
import { TASK_TYPE_LABELS } from "../labels";

const PRIORITY_CONFIG: Record<string, { label: string; color: "error" | "default" | "info" }> = {
  high: { label: "Wichtig", color: "error" },
  normal: { label: "Normal", color: "default" },
  low: { label: "Nebensache", color: "info" },
};

const URGENCY_CONFIG: Record<string, { label: string; color: string }> = {
  acute: { label: "🔴 Akut", color: "#d32f2f" },
  soon: { label: "🟡 Bald", color: "#ed6c02" },
  relaxed: { label: "⚪ Entspannt", color: "#9e9e9e" },
};

export function RelevantTaskCard({
  item,
  onNavigateToPlant,
  onComplete,
  onSkip,
}: {
  item: RelevantNowItem;
  onNavigateToPlant?: (plantId: string) => void;
  onComplete?: (taskId: string) => void;
  onSkip?: (taskId: string) => void;
}) {
  const taskLabel = TASK_TYPE_LABELS[item.task_type] ?? item.task_type;
  const emoji = taskLabel.split(" ")[0] ?? "📋";
  const isClickable = !!onNavigateToPlant && !!item.task.plant_id;
  const prio = PRIORITY_CONFIG[item.priority] ?? PRIORITY_CONFIG.normal;
  const urg = URGENCY_CONFIG[item.urgency] ?? URGENCY_CONFIG.soon;

  const borderColor =
    item.urgency === "acute" ? "error.main" :
    item.priority === "high" ? "warning.main" :
    item.priority === "low" ? "grey.400" : "primary.main";

  const cardBody = (
    <CardContent sx={{ pb: 1 }}>
      <Stack direction="row" spacing={1} sx={{ mb: 0.5, alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          {emoji} {item.plant_name}
        </Typography>
        <Chip label={taskLabel} size="small" variant="outlined" sx={{ borderColor: "grey.300", color: "text.secondary" }} />
        <Chip
          label={urg.label}
          size="small"
          variant="outlined"
          sx={{ borderColor: urg.color, color: urg.color }}
        />
        {item.priority !== "normal" && (
          <Chip
            label={prio.label}
            size="small"
            variant="outlined"
            sx={{ borderColor: prio.color === "error" ? "error.main" : "info.main", color: prio.color === "error" ? "error.main" : "info.main" }}
          />
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
    <Card sx={{ mb: 2, borderLeft: "4px solid", borderLeftColor: borderColor }}>
      {isClickable ? (
        <CardActionArea onClick={() => onNavigateToPlant(item.task.plant_id)}>
          {cardBody}
        </CardActionArea>
      ) : (
        cardBody
      )}
      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, px: 2, pb: 1.5 }}>
        <Button
          size="small"
          variant="outlined"
          color="inherit"
          startIcon={<SkipNextOutlinedIcon />}
          onClick={(e) => { e.stopPropagation(); onSkip?.(item.task.id); }}
        >
          Überspringen
        </Button>
        <Button
          size="small"
          variant="contained"
          color="success"
          startIcon={<CheckCircleOutlinedIcon />}
          onClick={(e) => { e.stopPropagation(); onComplete?.(item.task.id); }}
        >
          Erledigt
        </Button>
      </Box>
    </Card>
  );
}
