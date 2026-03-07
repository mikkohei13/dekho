import { fetchTrackDetails, fetchTrackRemoteData, saveTrackUserData } from "./api.js";
import {
  bindPersistentQueueControls,
  bindContentPanelEvents,
  bindFilterEvents,
  bindQueuePanelEvents,
  bindScanLinkEvent,
  bindTrackItemEvents,
  collectSelectedTrackLabels,
  showPlayingTrackInContentPanel,
} from "./events.js";
import {
  applyTracksFilter,
  getVisibleTrackIds,
  renderTrackItemTitle,
  renderQueueDrawer,
  renderTrackLabelFilterOptions,
  renderTrackListItem,
} from "./render-track-list.js";
import {
  renderDetails,
  updatePersistentTrackHeader,
  updatePersistentTrackTitleIfPlaying,
} from "./render-track-details.js";
import {
  hasQueueTracks,
  setQueueSnapshot,
  createTrackLabelMap,
  createUiState,
  markTrackUserDataSaved,
  readLabelCatalog,
} from "./state.js";
import { escapeHtml, parseLabelKeys } from "./dom.js";

const scanLink = document.querySelector(".scan-link");
const tracksPanel = document.getElementById("tracks-panel");
const trackItems = Array.from(document.querySelectorAll(".track-item"));
const tracksFilterInput = document.getElementById("tracks-filter-input");
const tracksFilterCount = document.getElementById("tracks-filter-count");
const tracksLabelFilter = document.getElementById("tracks-label-filter");
const tracksLabelFilterSummary = document.getElementById("tracks-label-filter-summary");
const tracksLabelFilterOptions = document.getElementById("tracks-label-filter-options");
const tracksSelectedLabels = document.getElementById("tracks-selected-labels");
const tracksClearFiltersButton = document.getElementById("tracks-clear-filters-btn");
const queueDrawerToggleButton = document.getElementById("queue-drawer-toggle-btn");
const queueDrawerBody = document.getElementById("queue-drawer-body");
const queueList = document.getElementById("queue-track-list");
const queueCount = document.getElementById("queue-count");
const queueEmptyState = document.getElementById("queue-empty-state");
const queueNotice = document.getElementById("queue-notice");
const recreateQueueButton = document.getElementById("recreate-queue-btn");
const resumeQueueButton = document.getElementById("resume-queue-btn");
const contentPanel = document.getElementById("content-panel");
const contentPanelBody = document.getElementById("content-panel-body");
const persistentTrackHeader = document.getElementById("persistent-track-header");
const persistentTrackTitle = document.getElementById("persistent-track-title");
const previousQueueTrackButton = document.getElementById("prev-queue-track-btn");
const nextQueueTrackButton = document.getElementById("next-queue-track-btn");
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
  renderQueueState();
}

function renderTrackAndDetails(trackId, data) {
  renderTrackListItem(trackId, data, {
    trackLabelByKey,
    applyFilter,
  });
  renderDetails(data, contentPanelBody);
  state.activeTrackData = data;
  markTrackUserDataSaved(state, setTrackUserDataSaveStatus);
  renderQueueState();
}

function getTrackItemById(trackId) {
  const item = document.querySelector(`.track-item[data-track-id="${CSS.escape(trackId)}"]`);
  return item instanceof HTMLElement ? item : null;
}

function getTrackTitleById(trackId) {
  const trackItem = getTrackItemById(trackId);
  if (!(trackItem instanceof HTMLElement)) {
    return "Unknown";
  }
  return trackItem.dataset.displayTitle
    || trackItem.querySelector("[data-track-item-display-title]")?.textContent?.trim()
    || "Unknown";
}

function setQueueNotice(message) {
  state.queueNotice = String(message || "");
}

function updateQueueButtonsState() {
  const hasQueue = hasQueueTracks(state);
  const isQueuePlayback = state.playbackMode === "queue";
  if (resumeQueueButton instanceof HTMLButtonElement) {
    resumeQueueButton.disabled = !hasQueue;
  }
  const hasVisibleTracks = getVisibleTrackIds(trackItems).length > 0;
  if (recreateQueueButton instanceof HTMLButtonElement) {
    recreateQueueButton.disabled = !hasVisibleTracks;
  }
  if (previousQueueTrackButton instanceof HTMLButtonElement) {
    previousQueueTrackButton.disabled = !isQueuePlayback || state.queueIndex <= 0;
  }
  if (nextQueueTrackButton instanceof HTMLButtonElement) {
    nextQueueTrackButton.disabled = !isQueuePlayback || state.queueIndex >= state.queueTrackIds.length - 1;
  }
}

function renderQueueState() {
  renderQueueDrawer({
    queueTrackIds: state.queueTrackIds,
    queueIndex: state.queueIndex,
    queueList,
    queueCount,
    queueEmptyState,
    queueNotice,
    queueNoticeText: state.queueNotice,
    selectedTrackPlayer,
    playbackMode: state.playbackMode,
  });
  updateQueueButtonsState();
}

function toggleQueueDrawer(forceOpen = null) {
  if (!(queueDrawerBody instanceof HTMLElement)) {
    return;
  }
  const shouldOpen = forceOpen === null ? queueDrawerBody.hidden : Boolean(forceOpen);
  queueDrawerBody.hidden = !shouldOpen;
  if (queueDrawerToggleButton instanceof HTMLButtonElement) {
    queueDrawerToggleButton.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
    queueDrawerToggleButton.textContent = shouldOpen ? "Hide queue" : "Show queue";
  }
}

function setQueueFromVisibleTracks(startTrackId = null) {
  const visibleTrackIds = getVisibleTrackIds(trackItems);
  if (visibleTrackIds.length === 0) {
    setQueueSnapshot(state, []);
    setQueueNotice("No tracks match current filters.");
    renderQueueState();
    return false;
  }
  const nextIndex = startTrackId ? visibleTrackIds.indexOf(startTrackId) : 0;
  if (startTrackId && nextIndex < 0) {
    setQueueSnapshot(state, visibleTrackIds, 0);
    setQueueNotice("Selected track is not visible in current filter.");
    renderQueueState();
    return false;
  }
  setQueueSnapshot(state, visibleTrackIds, Math.max(nextIndex, 0));
  setQueueNotice("");
  renderQueueState();
  return true;
}

function setPlaybackTrack(trackId, playbackMode) {
  const title = getTrackTitleById(trackId);
  updatePersistentTrackHeader(
    { track_id: trackId, title_new: title },
    {
      persistentTrackHeader,
      persistentTrackTitle,
      selectedTrackPlayer,
      showPlayingTrackButton,
    }
  );
  state.playbackMode = playbackMode;
  if (selectedTrackPlayer instanceof HTMLAudioElement) {
    const playAttempt = selectedTrackPlayer.play();
    if (playAttempt && typeof playAttempt.catch === "function") {
      playAttempt.catch(() => {
        setQueueNotice("Playback blocked by browser. Click play again.");
        renderQueueState();
      });
    }
  }
  renderQueueState();
}

function playQueueAtIndex(queueIndex) {
  if (!hasQueueTracks(state)) {
    setQueueNotice("Queue is empty.");
    renderQueueState();
    return;
  }
  const nextIndex = Math.max(0, Math.min(queueIndex, state.queueTrackIds.length - 1));
  const nextTrackId = state.queueTrackIds[nextIndex] || "";
  if (!nextTrackId) {
    setQueueNotice("Queue track is not available.");
    renderQueueState();
    return;
  }
  state.queueIndex = nextIndex;
  state.queueStatus = "playing";
  setQueueNotice("");
  const item = getTrackItemById(nextTrackId);
  if (!(item instanceof HTMLElement)) {
    setQueueNotice("Queue track is missing. Skipped.");
    const canAdvance = nextIndex < state.queueTrackIds.length - 1;
    if (canAdvance) {
      playQueueAtIndex(nextIndex + 1);
      return;
    }
    state.playbackMode = "none";
    state.queueStatus = "ready";
    renderQueueState();
    return;
  }
  setPlaybackTrack(nextTrackId, "queue");
}

function startQueueFromTrack(trackId) {
  const queueCreated = setQueueFromVisibleTracks(trackId);
  if (!queueCreated) {
    return;
  }
  toggleQueueDrawer(true);
  playQueueAtIndex(state.queueIndex);
}

function recreateQueueFromFilter() {
  const queueCreated = setQueueFromVisibleTracks(null);
  if (!queueCreated) {
    return;
  }
  state.queueStatus = "ready";
  renderQueueState();
}

function resumeQueue() {
  if (!hasQueueTracks(state)) {
    setQueueNotice("Queue is empty.");
    renderQueueState();
    return;
  }
  const resumeIndex = state.queueIndex >= 0 ? state.queueIndex : 0;
  playQueueAtIndex(resumeIndex);
}

function moveQueue(delta) {
  if (!hasQueueTracks(state)) {
    return;
  }
  playQueueAtIndex(state.queueIndex + delta);
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

bindTrackItemEvents(trackItems, state, loadTrackDetails, startQueueFromTrack);
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
bindQueuePanelEvents({
  tracksPanel,
  onToggleQueueDrawer: toggleQueueDrawer,
  onRecreateQueueFromFilter: recreateQueueFromFilter,
  onResumeQueue: resumeQueue,
  onSelectQueueIndex: playQueueAtIndex,
});
bindPersistentQueueControls({
  previousQueueTrackButton,
  nextQueueTrackButton,
  onPreviousQueueTrack: () => moveQueue(-1),
  onNextQueueTrack: () => moveQueue(1),
});
bindContentPanelEvents({
  contentPanel,
  contentPanelBody,
  state,
  setTrackUserDataSaveStatus,
  onGetRemoteData: fetchRemoteData,
  onSaveUserData: saveUserData,
  onPlayCurrentTrack: (activeTrackData) => {
    if (hasQueueTracks(state)) {
      state.queueStatus = "paused";
    }
    state.playbackMode = "single";
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
    renderQueueState();
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

if (selectedTrackPlayer instanceof HTMLAudioElement) {
  selectedTrackPlayer.addEventListener("ended", () => {
    if (state.playbackMode !== "queue") {
      return;
    }
    const nextIndex = state.queueIndex + 1;
    if (nextIndex >= state.queueTrackIds.length) {
      state.playbackMode = "none";
      state.queueStatus = "ready";
      setQueueNotice("Queue finished.");
      renderQueueState();
      return;
    }
    playQueueAtIndex(nextIndex);
  });
}

renderQueueState();
