import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, CssBaseline } from "@mui/material";
import {
  AppBar,
  Box,
  Container,
  Tab,
  Tabs,
  Toolbar,
  Typography,
} from "@mui/material";
import { theme } from "./theme";
import { PlantListPage } from "./pages/PlantListPage";
import { PlantDetailPage } from "./pages/PlantDetailPage";
import { DashboardPage } from "./pages/DashboardPage";

const queryClient = new QueryClient();

type View = { page: "list" } | { page: "detail"; id: string } | { page: "dashboard" };

function AppContent() {
  const [view, setView] = useState<View>({ page: "dashboard" });
  const tabIndex = view.page === "dashboard" ? 0 : 1;

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="static" color="primary" elevation={0}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            🌱 Plant-State
          </Typography>
        </Toolbar>
        <Tabs
          value={tabIndex}
          onChange={(_, v) =>
            setView(v === 0 ? { page: "dashboard" } : { page: "list" })
          }
          textColor="inherit"
          indicatorColor="secondary"
          sx={{ px: 2 }}
        >
          <Tab label="Dashboard" />
          <Tab label="Pflanzen" />
        </Tabs>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 3 }}>
        {view.page === "dashboard" && (
          <DashboardPage
            onNavigateToPlant={(id) => setView({ page: "detail", id })}
          />
        )}
        {view.page === "list" && (
          <PlantListPage
            onSelect={(id) => setView({ page: "detail", id })}
          />
        )}
        {view.page === "detail" && (
          <PlantDetailPage
            plantId={view.id}
            onBack={() => setView({ page: "list" })}
          />
        )}
      </Container>
    </Box>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AppContent />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
