import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Fab,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import RefreshIcon from "@mui/icons-material/Refresh";
import CloseIcon from "@mui/icons-material/Close";
import { api } from "../api";
import type { Plant } from "../api";
import { PlantImage } from "../components/PlantImage";
import { RuleCard } from "../components/RuleCard";
import { taskTypeLabel } from "../labels";

// ─── Add Plant Dialog ────────────────────────────────────────────────

function AddPlantDialog({
  open,
  onClose,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [step, setStep] = useState(0);
  const [plantName, setPlantName] = useState("");
  const [method, setMethod] = useState<"prompt" | "agent" | null>(null);
  const [prompt, setPrompt] = useState("");
  const [agentId, setAgentId] = useState("");
  const [jsonText, setJsonText] = useState("");
  const [preview, setPreview] = useState<object | null>(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  const { data: agents } = useQuery({
    queryKey: ["ha-agents"],
    queryFn: api.listHaAgents,
    enabled: open,
  });

  const reset = () => {
    setStep(0);
    setPlantName("");
    setMethod(null);
    setPrompt("");
    setAgentId("");
    setJsonText("");
    setPreview(null);
    setError("");
    setGenerating(false);
    setCopied(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleCopyPrompt = async () => {
    setError("");
    try {
      const res = await api.getPlantPrompt(plantName);
      setPrompt(res.combined_prompt);
      setMethod("prompt");
      setStep(1);
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  const handleGenerate = async () => {
    if (!agentId) return;
    setError("");
    setGenerating(true);
    try {
      const result = await api.generatePlant(plantName, agentId);
      setPreview(result);
      setJsonText(JSON.stringify(result, null, 2));
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setGenerating(false);
    }
  };

  const handleParseJson = () => {
    setError("");
    try {
      const parsed = JSON.parse(jsonText);
      setPreview(parsed);
      setStep(2);
    } catch {
      setError("Ungültiges JSON — bitte prüfen und nochmal versuchen.");
    }
  };

  const handleSave = async () => {
    if (!preview) return;
    setError("");
    try {
      await api.createPlant(preview);
      onSaved();
      handleClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ pr: 6 }}>
        🌱 Pflanze hinzufügen
        <IconButton
          onClick={handleClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Stepper activeStep={step} sx={{ mb: 3, mt: 1 }}>
          <Step><StepLabel>Name</StepLabel></Step>
          <Step><StepLabel>Konfiguration</StepLabel></Step>
          <Step><StepLabel>Vorschau</StepLabel></Step>
        </Stepper>

        {step === 0 && (
          <Box>
            <TextField
              autoFocus
              fullWidth
              label="Pflanzenname"
              placeholder="z.B. Tomate, Lavendel, Hortensie…"
              value={plantName}
              onChange={(e) => setPlantName(e.target.value)}
              sx={{ mb: 2 }}
            />
            <Stack spacing={1.5}>
              <Button
                variant="outlined"
                startIcon={<ContentCopyIcon />}
                onClick={handleCopyPrompt}
                disabled={!plantName.trim()}
              >
                📋 Prompt für ChatGPT kopieren
              </Button>
              {agents && agents.length > 0 && (
                <>
                  <FormControl fullWidth size="small">
                    <InputLabel>HA Agent wählen</InputLabel>
                    <Select
                      value={agentId}
                      label="HA Agent wählen"
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
                    variant="contained"
                    startIcon={generating ? <CircularProgress size={18} /> : <SmartToyIcon />}
                    onClick={handleGenerate}
                    disabled={!plantName.trim() || !agentId || generating}
                  >
                    {generating ? "Generiere…" : "🤖 Mit HA Agent generieren"}
                  </Button>
                </>
              )}
            </Stack>
          </Box>
        )}

        {step === 1 && method === "prompt" && (
          <Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Kopiere diesen Prompt und füge ihn in ChatGPT / Claude ein.
              Dann paste das Ergebnis-JSON unten ein:
            </Typography>
            <Box sx={{ position: "relative", mb: 2 }}>
              <TextField
                fullWidth
                multiline
                minRows={6}
                maxRows={12}
                value={prompt}
                slotProps={{ input: { readOnly: true, sx: { fontFamily: "monospace", fontSize: 12 } } }}
              />
              <Tooltip title={copied ? "Kopiert! ✓" : "Prompt kopieren"}>
                <IconButton
                  size="small"
                  onClick={() => copyToClipboard(prompt)}
                  sx={{ position: "absolute", top: 8, right: 8 }}
                >
                  <ContentCopyIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
              Ergebnis-JSON einfügen:
            </Typography>
            <TextField
              fullWidth
              multiline
              minRows={6}
              maxRows={12}
              placeholder='{"name": "Tomate", "rules": [...] }'
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              slotProps={{ input: { sx: { fontFamily: "monospace", fontSize: 12 } } }}
            />
          </Box>
        )}

        {step === 2 && preview && (
          <Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Vorschau — prüfe ob alles stimmt:
            </Typography>
            <TextField
              fullWidth
              multiline
              minRows={8}
              maxRows={16}
              value={JSON.stringify(preview, null, 2)}
              onChange={(e) => {
                setJsonText(e.target.value);
                try {
                  setPreview(JSON.parse(e.target.value));
                  setError("");
                } catch {
                  setError("Ungültiges JSON");
                }
              }}
              slotProps={{ input: { sx: { fontFamily: "monospace", fontSize: 12 } } }}
            />
          </Box>
        )}

        {error && (
          <Typography color="error" variant="body2" sx={{ mt: 1 }}>
            {error}
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        {step === 1 && method === "prompt" && (
          <Button onClick={handleParseJson} disabled={!jsonText.trim()}>
            Weiter →
          </Button>
        )}
        {step === 2 && (
          <Button variant="contained" onClick={handleSave}>
            💾 Speichern
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

// ─── Plant List Page ─────────────────────────────────────────────────

export function PlantListPage({
  onSelect,
}: {
  onSelect: (id: string) => void;
}) {
  const queryClient = useQueryClient();
  const { data: plants, isLoading, error } = useQuery({
    queryKey: ["plants"],
    queryFn: api.listPlants,
  });
  const [filter, setFilter] = useState("");
  const [rulesPlant, setRulesPlant] = useState<Plant | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<Plant | null>(null);
  const [regenAgentId, setRegenAgentId] = useState("");
  const [regenRunning, setRegenRunning] = useState(false);
  const [regenResult, setRegenResult] = useState<{ succeeded: number; total: number; failed: { name: string; error: string }[] } | null>(null);

  const { data: agents } = useQuery({
    queryKey: ["ha-agents"],
    queryFn: () => api.listHaAgents(),
  });

  const handleRegenerateAll = async () => {
    if (!regenAgentId) return;
    setRegenRunning(true);
    setRegenResult(null);
    try {
      const result = await api.regenerateAll(regenAgentId);
      setRegenResult(result);
      queryClient.invalidateQueries({ queryKey: ["plants"] });
      queryClient.invalidateQueries({ queryKey: ["relevant-now"] });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setRegenResult({ succeeded: 0, total: 0, failed: [{ name: "Request", error: msg }] });
    } finally {
      setRegenRunning(false);
    }
  };

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      api.setPlantActive(id, active),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plants"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deletePlant(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plants"] });
      setDeleteConfirm(null);
    },
  });

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
            <Card sx={{ opacity: plant.active ? 1 : 0.5, transition: "opacity 0.2s" }}>
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
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "flex-end", px: 1, pb: 0.5 }}>
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

      {/* KI Regeneration — below the grid */}
      {agents && agents.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            🤖 KI-Regeneration
          </Typography>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>KI-Agent</InputLabel>
              <Select
                value={regenAgentId}
                label="KI-Agent"
                onChange={(e) => setRegenAgentId(e.target.value)}
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
              startIcon={regenRunning ? <CircularProgress size={16} /> : <RefreshIcon />}
              disabled={!regenAgentId || regenRunning}
              onClick={handleRegenerateAll}
            >
              {regenRunning ? "Generiere…" : "Alle neu generieren"}
            </Button>
          </Stack>
          {regenResult && (
            <Alert
              severity={regenResult.failed.length === 0 ? "success" : "warning"}
              onClose={() => setRegenResult(null)}
              sx={{ mt: 1 }}
            >
              {regenResult.succeeded}/{regenResult.total} Pflanzen aktualisiert.
              {regenResult.failed.length > 0 && (
                <> Fehler: {regenResult.failed.map((f) => `${f.name} (${f.error})`).join(", ")}</>
              )}
            </Alert>
          )}
        </Box>
      )}

      {/* FAB: Add Plant */}
      <Fab
        color="primary"
        onClick={() => setAddOpen(true)}
        sx={{ position: "fixed", bottom: 24, right: 24 }}
        aria-label="Pflanze hinzufügen"
      >
        <AddIcon />
      </Fab>

      {/* Add Plant Dialog */}
      <AddPlantDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ["plants"] })}
      />

      {/* Delete Confirmation */}
      <Dialog open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Pflanze löschen?</DialogTitle>
        <DialogContent>
          <Typography>
            <strong>{deleteConfirm?.name}</strong> und alle zugehörigen Aufgaben
            werden unwiderruflich gelöscht.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Abbrechen</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => deleteConfirm && deleteMutation.mutate(deleteConfirm.id)}
          >
            🗑️ Löschen
          </Button>
        </DialogActions>
      </Dialog>

      {/* Rules Dialog */}
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
                <RuleCard key={rule.id} rule={rule} debug />
              ))}

              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                Verwaltung
              </Typography>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                <Tooltip title={rulesPlant.active ? "Deaktivieren" : "Aktivieren"}>
                  <Switch
                    size="small"
                    checked={rulesPlant.active}
                    onChange={() =>
                      toggleMutation.mutate(
                        { id: rulesPlant.id, active: !rulesPlant.active },
                        { onSuccess: (updated) => setRulesPlant({ ...rulesPlant, active: (updated as Plant).active }) },
                      )
                    }
                  />
                </Tooltip>
                <Typography variant="body2">
                  {rulesPlant.active ? "Aktiv" : "Deaktiviert"}
                </Typography>
                <Box sx={{ flex: 1 }} />
                <Button
                  size="small"
                  color="error"
                  variant="outlined"
                  startIcon={<DeleteIcon />}
                  onClick={() => {
                    setRulesPlant(null);
                    setDeleteConfirm(rulesPlant);
                  }}
                >
                  Löschen
                </Button>
              </Stack>
            </DialogContent>
          </>
        )}
      </Dialog>
    </Box>
  );
}
