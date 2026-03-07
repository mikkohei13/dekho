import { domSafeValue, escapeHtml } from "./dom.js";
import { getDisplayTitle, hasRemoteTags } from "./render-track-list.js";

function getTrackImageSrc(trackId) {
  const id = String(trackId ?? "").trim();
  if (!id) {
    return "";
  }
  return `/api/tracks/${encodeURIComponent(id)}/image`;
}

function getTrackSpectrogramSrc(trackId) {
  const id = String(trackId ?? "").trim();
  if (!id) {
    return "";
  }
  return `/api/tracks/${encodeURIComponent(id)}/spectrogram`;
}

function renderLabelGroups(labelCatalog, selectedLabels) {
  if (!Array.isArray(labelCatalog) || labelCatalog.length === 0) {
    return "<p class=\"empty-state\">No labels configured.</p>";
  }

  const selectedKeys = new Set(Array.isArray(selectedLabels) ? selectedLabels : []);

  return labelCatalog.map((group) => {
    const category = typeof group.category === "string" ? group.category : "";
    const displayName = typeof group.display_name === "string" ? group.display_name : category;
    const labels = Array.isArray(group.labels) ? group.labels : [];
    if (!category || labels.length === 0) {
      return "";
    }

    const optionsHtml = labels
      .map((labelEntry) => {
        if (!labelEntry || typeof labelEntry !== "object") {
          return "";
        }
        const labelKey = typeof labelEntry.key === "string" ? labelEntry.key : "";
        const label = typeof labelEntry.label === "string" ? labelEntry.label : "";
        if (!labelKey || !label) {
          return "";
        }
        const inputId = `track-label-${domSafeValue(labelKey)}`;
        const checked = selectedKeys.has(labelKey) ? " checked" : "";
        return `
          <label for="${escapeHtml(inputId)}" class="track-label-option">
            <input
              id="${escapeHtml(inputId)}"
              class="track-label-input"
              type="checkbox"
              data-label-key="${escapeHtml(labelKey)}"${checked}
            >
            <span>${escapeHtml(label)}</span>
          </label>
        `;
      })
      .join("");

    return `
      <fieldset class="track-label-category ${domSafeValue(displayName)}">
        <legend>${escapeHtml(displayName)}</legend>
        <div class="track-label-options">
          ${optionsHtml}
        </div>
      </fieldset>
    `;
  }).join("");
}

export function updatePersistentTrackHeader(data, refs) {
  const { persistentTrackHeader, persistentTrackTitle, selectedTrackPlayer, showPlayingTrackButton } = refs;
  if (
    !(persistentTrackHeader instanceof HTMLElement)
    || !(persistentTrackTitle instanceof HTMLElement)
    || !(selectedTrackPlayer instanceof HTMLAudioElement)
  ) {
    return;
  }

  const trackId = data.track_id ?? "";
  if (!trackId) {
    persistentTrackHeader.hidden = true;
    if (showPlayingTrackButton instanceof HTMLButtonElement) {
      showPlayingTrackButton.disabled = true;
    }
    delete selectedTrackPlayer.dataset.trackId;
    selectedTrackPlayer.removeAttribute("src");
    selectedTrackPlayer.load();
    return;
  }

  const displayTitle = getDisplayTitle(data) || "Untitled Track";
  const nextSrc = `/api/tracks/${encodeURIComponent(trackId)}/audio`;
  const currentSrc = selectedTrackPlayer.getAttribute("src") || "";

  persistentTrackHeader.hidden = false;
  selectedTrackPlayer.dataset.trackId = trackId;
  if (showPlayingTrackButton instanceof HTMLButtonElement) {
    showPlayingTrackButton.disabled = false;
  }
  persistentTrackTitle.textContent = displayTitle;

  // Keep playback uninterrupted when form save rerenders the details for same track.
  if (currentSrc !== nextSrc) {
    selectedTrackPlayer.setAttribute("src", nextSrc);
    selectedTrackPlayer.load();
  }
}

export function updatePersistentTrackTitleIfPlaying(data, refs) {
  const { persistentTrackTitle, selectedTrackPlayer } = refs;
  if (
    !(persistentTrackTitle instanceof HTMLElement)
    || !(selectedTrackPlayer instanceof HTMLAudioElement)
  ) {
    return;
  }
  const trackId = data.track_id ?? "";
  const playingTrackId = selectedTrackPlayer.dataset.trackId ?? "";
  if (!trackId || playingTrackId !== trackId) {
    return;
  }
  const displayTitle = getDisplayTitle(data) || "Untitled Track";
  persistentTrackTitle.textContent = displayTitle;
}

export function renderDetails(data, contentPanelBody) {
  const title = data.title ?? "";
  const titleNew = data.title_new ?? "";
  const notes = data.notes ?? "";
  const trackId = data.track_id ?? "";
  const url = data.url ?? "";
  const filepath = data.filepath ?? "";
  const duration = data.duration ?? "";
  const dateCreated = data.date_created ?? "";
  const tags = data.tags ?? "";
  const negativeTags = data.negative_tags ?? "";
  const hasCoverClipId = Boolean(data.has_cover_clip_id);
  const majorModelVersion = data.major_model_version ?? "";
  const modelName = data.model_name ?? "";
  const personaName = data.persona_name ?? "";
  const prompt = data.prompt ?? "";
  const labels = Array.isArray(data.labels) ? data.labels : [];
  const labelCatalog = Array.isArray(data.label_catalog) ? data.label_catalog : [];
  const displayTitle = getDisplayTitle(data) || "Untitled Track";

  if (!(contentPanelBody instanceof HTMLElement)) {
    return;
  }

  contentPanelBody.innerHTML = `
    <section id="track-info">
      <header class="panel-header track-info-header">
        <h2>
          ${escapeHtml(displayTitle)}${hasRemoteTags(tags) ? "<span class=\"remote-tags-indicator\">✦</span>" : ""}
        </h2>
        <button id="play-current-track-btn" type="button">▶ Play</button>
      </header>
      <div class="track-form">
        <form id="track-user-data-form">
          <label for="title-new-input">title_new</label>
          <input id="title-new-input" name="title_new" type="text" value="${escapeHtml(titleNew)}">
          <label for="notes-input">notes</label>
          <textarea id="notes-input" name="notes" rows="4">${escapeHtml(notes)}</textarea>
          <div class="track-labels">
            <div class="track-labels-groups">
              ${renderLabelGroups(labelCatalog, labels)}
            </div>
          </div>
          <div class="track-user-data-actions">
            <button id="save-track-user-data-btn" type="button">Save</button>
            <span
              id="track-user-data-save-status"
              class="track-user-data-save-status track-user-data-save-status--saved"
            >saved</span>
            <span id="track-user-data-error" class="track-user-data-error"></span>
          </div>
        </form>
      </div>
      <div class="track-details">
        <img
          class="track-details-image"
          src="${escapeHtml(getTrackImageSrc(trackId))}"
          width="200"
          height="200"
        >
        <img
          class="track-details-spectrogram"
          src="${escapeHtml(getTrackSpectrogramSrc(trackId))}"
          alt="Spectrogram"
          loading="lazy"
          onerror="this.hidden = true;"
        >
        <p id="track-info-title">${escapeHtml(title || "-")}</p>
        <p id="track-info-id">${escapeHtml(trackId)}</p>
        <p id="track-info-url">${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a>` : "-"}</p>
        <p id="track-info-filepath">${escapeHtml(filepath)}</p>
        <p id="track-info-duration">${escapeHtml(duration)}</p>
        <p id="track-info-date-created">${escapeHtml(dateCreated)}</p>
      </div>
      <div class="track-moredetails">
        <div class="remote-actions">
          <button id="get-remote-data-btn" type="button">Get data from Suno</button>
          <span id="remote-data-error" class="remote-data-error"></span>
        </div>
        <h4>Tags</h4>
        <div id="track-info-tags">${escapeHtml(tags || "-")}</div>
        <h4>Negative Tags</h4>
        <div id="track-info-negative-tags">${escapeHtml(negativeTags || "-")}</div>
        <h4>Has Cover Clip ID</h4>
        <div id="track-info-has-cover-clip-id">${hasCoverClipId ? "True" : "False"}</div>
        <h4>Major Model Version</h4>
        <div id="track-info-major-model-version">${escapeHtml(majorModelVersion || "-")}</div>
        <h4>Model Name</h4>
        <div id="track-info-model-name">${escapeHtml(modelName || "-")}</div>
        <h4>Persona Name</h4>
        <div id="track-info-persona-name">${escapeHtml(personaName || "-")}</div>
        <h4>Lyrics Prompt</h4>
        <div id="track-info-prompt">${escapeHtml(prompt || "-")}</div>
      </div>
    </section>
  `;
}
