import { Box, Typography } from "@mui/material";
import type { RelevantNowItem } from "../api";
import { RelevantTaskCard } from "../components/RelevantTaskCard";

export function DashboardPage({ items }: { items: RelevantNowItem[] }) {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        📋 Jetzt relevant
      </Typography>
      {items.length === 0 ? (
        <Typography color="text.secondary">
          Aktuell sind keine Aufgaben fällig. Das Wetter oder die Jahreszeit
          passen noch nicht.
        </Typography>
      ) : (
        items.map((item) => (
          <RelevantTaskCard key={item.task.id} item={item} />
        ))
      )}
    </Box>
  );
}
