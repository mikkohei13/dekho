import { fetchTrackDetails, fetchTrackRemoteData, saveTrackUserData } from "./api.js";
import {
  bindContentPanelEvents,
  bindFilterEvents,
  bindScanLinkEvent,
  bindTrackItemEvents,
  collectSelectedTrackLabels,
  showPlayingTrackInContentPanel,
} from "./events.js";
import {
  applyTracksFilter,
  renderTrackItemTitle,
  renderTrackLabelFilterOptions,
  renderTrackListItem,
} from "./render-track-list.js";
import {
  renderDetails,
  updatePersistentTrackHeader,
  updatePersistentTrackTitleIfPlaying,
} from "./render-track-details.js";
import {
  createTrackLabelMap,
  createUiState,
  markTrackUserDataSaved,
  readLabelCatalog,
} from "./state.js";
import { escapeHtml, parseLabelKeys } from "./dom.js";

const scanLink = document.querySelector(".scan-link");
const trackItems = Array.from(document.querySelectorAll(".track-item"));
const tracksFilterInput = document.getElementById("tracks-filter-input");
const tracksFilterCount = document.getElementById("tracks-filter-count");
const tracksLabelFilter = document.getElementById("tracks-label-filter");
const tracksLabelFilterSummary = document.getElementById("tracks-label-filter-summary");
const tracksLabelFilterOptions = document.getElementById("tracks-label-filter-options");
const tracksSelectedLabels = document.getElementById("tracks-selected-labels");
const tracksClearFiltersButton = document.getElementById("tracks-clear-filters-btn");
const contentPanel = document.getElementById("content-panel");
const contentPanelBody = document.getElementById("content-panel-body");
const persistentTrackHeader = document.getElementById("persistent-track-header");
const persistentTrackTitle = document.getElementById("persistent-track-title");
const selectedTrackPlayer = document.getElementById("selected-track-player");
const showPlayingTrackButton = document.getElementById("show-playing-track-btn");

const tracksLabelCatalog = readLabelCatalog();
const trackLabelByKey = createTrackLabelMap(tracksLabelCatalog);
const state = createUiState();

function setTrackUserDataSaveStatus(statusText) {
  const saveStatus = document.getElementById("track-user-data-save-status");
  if (!(saveStatus instanceof HTMLElement)) {
    return;
  }
  saveStatus.textContent = statusText;
}

function renderFilterOptions() {
  renderTrackLabelFilterOptions({
    tracksLabelFilterOptions,
    tracksLabelCatalog,
    selectedTrackFilterLabelKeys: state.selectedTrackFilterLabelKeys,
    selectedMissingTrackFilterCategories: state.selectedMissingTrackFilterCategories,
  });
}

function applyFilter() {
  applyTracksFilter({
    trackItems,
    tracksFilterInput,
    tracksFilterCount,
    selectedTrackFilterLabelKeys: state.selectedTrackFilterLabelKeys,
    selectedMissingTrackFilterCategories: state.selectedMissingTrackFilterCategories,
    tracksLabelFilterSummary,
    tracksSelectedLabels,
    tracksClearFiltersButton,
    trackLabelByKey,
  });
}

function renderTrackAndDetails(trackId, data) {
  renderTrackListItem(trackId, data, {
    trackLabelByKey,
    applyFilter,
  });
  renderDetails(data, contentPanelBody);
  state.activeTrackData = data;
  markTrackUserDataSaved(state, setTrackUserDataSaveStatus);
}

async function loadTrackDetails(trackId, item) {
  trackItems.forEach((trackItem) => trackItem.classList.remove("is-active"));
  item.classList.add("is-active");
  state.activeTrackId = trackId;
  state.activeTrackData = null;
  if (contentPanelBody instanceof HTMLElement) {
    contentPanelBody.innerHTML = "<p class=\"empty-state\">Loading track details...</p>";
  }

  try {
    const data = await fetchTrackDetails(trackId);
    renderTrackAndDetails(trackId, data);
  } catch (error) {
    if (contentPanelBody instanceof HTMLElement) {
      contentPanelBody.innerHTML = `<p class="empty-state">${escapeHtml(error.message || "Unable to load track details.")}</p>`;
    }
  }
}

async function fetchRemoteData(trackId) {
  const button = document.getElementById("get-remote-data-btn");
  const error = document.getElementById("remote-data-error");
  if (!(button instanceof HTMLButtonElement) || !(error instanceof HTMLElement)) {
    return;
  }

  error.textContent = "";
  button.disabled = true;
  button.textContent = "Fetching...";

  try {
    const payload = await fetchTrackRemoteData(trackId);
    renderTrackListItem(trackId, payload, { trackLabelByKey, applyFilter });
    updatePersistentTrackTitleIfPlaying(payload, { persistentTrackTitle, selectedTrackPlayer });
    renderDetails(payload, contentPanelBody);
    state.activeTrackData = payload;
    markTrackUserDataSaved(state, setTrackUserDataSaveStatus);
  } catch (fetchError) {
    error.textContent = fetchError.message || "Failed to fetch data from Suno.";
  } finally {
    const nextButton = document.getElementById("get-remote-data-btn");
    if (nextButton instanceof HTMLButtonElement) {
      nextButton.disabled = false;
      nextButton.textContent = "Get data from Suno";
    }
  }
}

async function saveUserData(trackId) {
  const button = document.getElementById("save-track-user-data-btn");
  const error = document.getElementById("track-user-data-error");
  const titleInput = document.getElementById("title-new-input");
  const notesInput = document.getElementById("notes-input");
  if (
    !(button instanceof HTMLButtonElement)
    || !(error instanceof HTMLElement)
    || !(titleInput instanceof HTMLInputElement)
    || !(notesInput instanceof HTMLTextAreaElement)
  ) {
    return;
  }

  error.textContent = "";
  button.disabled = true;
  button.textContent = "Saving...";

  const labels = collectSelectedTrackLabels(contentPanelBody);
  try {
    const payload = await saveTrackUserData(trackId, {
      title_new: titleInput.value,
      notes: notesInput.value,
      labels,
    });
    renderTrackListItem(trackId, payload, { trackLabelByKey, applyFilter });
    updatePersistentTrackTitleIfPlaying(payload, { persistentTrackTitle, selectedTrackPlayer });
    renderDetails(payload, contentPanelBody);
    state.activeTrackData = payload;
    markTrackUserDataSaved(state, setTrackUserDataSaveStatus);
  } catch (saveError) {
    error.textContent = saveError.message || "Failed to save track data.";
  } finally {
    const nextButton = document.getElementById("save-track-user-data-btn");
    if (nextButton instanceof HTMLButtonElement) {
      nextButton.disabled = false;
      nextButton.textContent = "Save";
    }
  }
}

bindTrackItemEvents(trackItems, state, loadTrackDetails);
bindFilterEvents({
  tracksFilterInput,
  tracksLabelFilterOptions,
  tracksClearFiltersButton,
  tracksLabelFilter,
  selectedTrackFilterLabelKeys: state.selectedTrackFilterLabelKeys,
  selectedMissingTrackFilterCategories: state.selectedMissingTrackFilterCategories,
  applyTracksFilter: applyFilter,
  renderTrackLabelFilterOptions: renderFilterOptions,
});
bindScanLinkEvent(scanLink);
bindContentPanelEvents({
  contentPanel,
  contentPanelBody,
  state,
  setTrackUserDataSaveStatus,
  onGetRemoteData: fetchRemoteData,
  onSaveUserData: saveUserData,
  onPlayCurrentTrack: (activeTrackData) => {
    updatePersistentTrackHeader(activeTrackData, {
      persistentTrackHeader,
      persistentTrackTitle,
      selectedTrackPlayer,
      showPlayingTrackButton,
    });
    if (selectedTrackPlayer instanceof HTMLAudioElement) {
      const playAttempt = selectedTrackPlayer.play();
      if (playAttempt && typeof playAttempt.catch === "function") {
        playAttempt.catch(() => {});
      }
    }
  },
});

renderFilterOptions();
applyFilter();
trackItems.forEach((item) => {
  const displayTitle = item.dataset.displayTitle || "Unknown";
  const labelKeys = parseLabelKeys(item.dataset.labelKeys);
  const trackHasRemoteTags = item.dataset.hasRemoteTags === "1";
  renderTrackItemTitle(item, displayTitle, labelKeys, trackHasRemoteTags);
});

if (showPlayingTrackButton instanceof HTMLButtonElement) {
  showPlayingTrackButton.disabled = true;
  showPlayingTrackButton.addEventListener("click", () => {
    showPlayingTrackInContentPanel(state, selectedTrackPlayer, loadTrackDetails);
  });
}
