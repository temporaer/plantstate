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
import {
  HashRouter,
  Routes,
  Route,
  useNavigate,
  useLocation,
  useParams,
} from "react-router-dom";
import { useEffect } from "react";
import { theme } from "./theme";
import { PlantListPage } from "./pages/PlantListPage";
import { PlantDetailPage } from "./pages/PlantDetailPage";
import { DashboardPage } from "./pages/DashboardPage";

const queryClient = new QueryClient();

function PlantDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  if (!id) return null;
  return <PlantDetailPage plantId={id} onBack={() => navigate(-1)} />;
}

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();

  // Deep link from Lovelace card: read route from localStorage
  useEffect(() => {
    const route = localStorage.getItem("plant-state-route");
    if (route) {
      localStorage.removeItem("plant-state-route");
      navigate(route);
    }
  }, [navigate]);

  const tabIndex = location.pathname.startsWith("/plants") ? 1 : 0;

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
          onChange={(_, v) => navigate(v === 0 ? "/" : "/plants")}
          textColor="inherit"
          indicatorColor="secondary"
          sx={{ px: 2 }}
        >
          <Tab label="Dashboard" />
          <Tab label="Pflanzen" />
        </Tabs>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 3 }}>
        <Routes>
          <Route
            path="/"
            element={
              <DashboardPage
                onNavigateToPlant={(id) => navigate(`/plants/${id}`)}
              />
            }
          />
          <Route
            path="/plants"
            element={
              <PlantListPage
                onSelect={(id) => navigate(`/plants/${id}`)}
              />
            }
          />
          <Route path="/plants/:id" element={<PlantDetailRoute />} />
        </Routes>
      </Container>
    </Box>
  );
}

export default function App() {
  return (
    <HashRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AppContent />
        </ThemeProvider>
      </QueryClientProvider>
    </HashRouter>
  );
}
