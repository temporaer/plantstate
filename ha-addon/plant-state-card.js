/**
 * Plant-State Lovelace Card — minimalist garden task overview.
 *
 * Config:
 *   type: custom:plant-state-card
 *   entity: sensor.garten_tasks     # sensor with task data
 *   panel_url: /hassio/ingress/...  # add-on ingress URL (for deep links)
 */

const TASK_EMOJI = {
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

const URG = { acute: "🔴", soon: "🟡", relaxed: "⚪" };
const URG_LABEL = { acute: "akut", soon: "bald", relaxed: "entspannt" };
const URG_COLOR = { acute: "#ef5350", soon: "#ffb74d", relaxed: "#bdbdbd" };

class PlantStateCard extends HTMLElement {
  _config = {};
  _hass = null;
  _listening = false;

  setConfig(config) {
    this._config = {
      entity: config.entity || "sensor.garten_tasks",
      panel_url: config.panel_url || "",
      title: config.title ?? "🌱 Garten",
      max_tasks: config.max_tasks ?? 6,
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _navigate(path) {
    if (!this._hass) return;
    // Determine the add-on slug for ingress navigation
    let slug = this._config.addon_slug;
    if (!slug) {
      // Auto-detect from HA panel registry: find the hashed panel key
      const panels = this._hass.panels || {};
      for (const key of Object.keys(panels)) {
        if (key.endsWith("_plant_state") && /^[0-9a-f]{8}_/.test(key)) {
          slug = key;
          break;
        }
      }
    }
    if (!slug) return;
    const target = `/hassio/ingress/${slug}` + (path ? `/#${path}` : "");
    this._hass.navigate(target);
  }

  _render() {
    const entity = this._hass?.states[this._config.entity];

    // --- Loading / not found ---
    if (!entity) {
      this.innerHTML = `
        <ha-card>
          <div style="padding:16px;color:var(--secondary-text-color);font-size:14px">
            <span style="opacity:.6">🌱</span> Warte auf Daten…
          </div>
        </ha-card>`;
      return;
    }

    // --- Parse tasks ---
    let tasks = [];
    try {
      const raw = entity.attributes.tasks;
      tasks = typeof raw === "string" ? JSON.parse(raw) : raw || [];
    } catch {
      tasks = [];
    }

    // --- Count by urgency ---
    const counts = { acute: 0, soon: 0, relaxed: 0 };
    for (const t of tasks) counts[t.urgency] = (counts[t.urgency] || 0) + 1;

    // --- Build urgency badges ---
    const badges = ["acute", "soon", "relaxed"]
      .filter((u) => counts[u] > 0)
      .map(
        (u) =>
          `<span class="badge" style="--c:${URG_COLOR[u]}" data-filter="${u}">
            ${URG[u]} ${counts[u]} ${URG_LABEL[u]}
          </span>`
      )
      .join('<span class="sep">·</span>');

    // --- Build task chips (limited) ---
    const shown = tasks.slice(0, this._config.max_tasks);
    const chips = shown
      .map(
        (t) =>
          `<span class="chip" data-plant-id="${t.plant_id}" title="${t.explanation_summary || ""}">
            ${TASK_EMOJI[t.task_type] || "🌱"} ${t.plant_name}
          </span>`
      )
      .join("");
    const overflow =
      tasks.length > this._config.max_tasks
        ? `<span class="chip overflow">+${tasks.length - this._config.max_tasks}</span>`
        : "";

    // --- Empty state ---
    if (tasks.length === 0) {
      this.innerHTML = `
        <ha-card>
          <style>${this._styles()}</style>
          <div class="wrap">
            <div class="header">${this._config.title}</div>
            <div class="empty">Keine Aufgaben — alles gut! 🎉</div>
          </div>
        </ha-card>`;
      return;
    }

    // --- Render ---
    this.innerHTML = `
      <ha-card>
        <style>${this._styles()}</style>
        <div class="wrap">
          <div class="header">
            <span class="title">${this._config.title}</span>
          </div>
          <div class="badges">${badges}</div>
          <div class="chips">${chips}${overflow}</div>
          <div class="footer"><span class="open-link">▸ Öffnen</span></div>
        </div>
      </ha-card>`;

    // --- Delegated click handler (survives re-renders) ---
    if (!this._listening) {
      this._listening = true;
      this.addEventListener("click", (e) => {
        // Use composedPath to see through ha-card's shadow DOM boundary
        const path = e.composedPath();
        let target = null;
        for (const el of path) {
          if (el.matches && el.matches("[data-plant-id], [data-filter], .open-link")) {
            target = el;
            break;
          }
        }
        if (!target) return;
        e.preventDefault();
        e.stopPropagation();
        if (target.dataset && target.dataset.plantId) {
          this._navigate(`/plants/${target.dataset.plantId}`);
        } else if (target.dataset && target.dataset.filter) {
          this._navigate("/");
        } else if (target.classList && target.classList.contains("open-link")) {
          this._navigate("/");
        }
      });
    }
  }

  _styles() {
    return `
      .wrap {
        padding: 16px;
      }
      .header {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
      }
      .title {
        font-size: 16px;
        font-weight: 500;
        color: var(--primary-text-color);
      }
      .badges {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }
      .badge {
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        padding: 2px 8px;
        border-radius: 12px;
        background: color-mix(in srgb, var(--c) 15%, transparent);
        color: var(--primary-text-color);
        transition: background .15s;
      }
      .badge:hover {
        background: color-mix(in srgb, var(--c) 30%, transparent);
      }
      .sep {
        color: var(--secondary-text-color);
        font-size: 12px;
      }
      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 6px;
      }
      .chip {
        font-size: 13px;
        padding: 3px 10px;
        border-radius: 16px;
        background: var(--secondary-background-color, #f5f5f5);
        color: var(--primary-text-color);
        cursor: pointer;
        white-space: nowrap;
        transition: background .15s;
      }
      .chip:hover {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
      }
      .chip.overflow {
        background: transparent;
        color: var(--secondary-text-color);
        cursor: default;
        font-style: italic;
      }
      .footer {
        text-align: right;
        margin-top: 4px;
      }
      .open-link {
        font-size: 13px;
        color: var(--primary-color);
        cursor: pointer;
        font-weight: 500;
      }
      .open-link:hover {
        text-decoration: underline;
      }
      .empty {
        font-size: 14px;
        color: var(--secondary-text-color);
        padding: 8px 0;
      }
    `;
  }

  getCardSize() {
    return 2;
  }

  static getStubConfig() {
    return { entity: "sensor.garten_tasks" };
  }
}

customElements.define("plant-state-card", PlantStateCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "plant-state-card",
  name: "Plant-State",
  description: "Minimalist garden task overview",
  preview: true,
});
