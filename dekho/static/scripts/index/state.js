export function readLabelCatalog() {
  const tracksLabelCatalogElement = document.getElementById("tracks-label-catalog-data");
  if (!(tracksLabelCatalogElement instanceof HTMLScriptElement)) {
    return [];
  }
  try {
    const parsedCatalog = JSON.parse(tracksLabelCatalogElement.textContent || "[]");
    return Array.isArray(parsedCatalog) ? parsedCatalog : [];
  } catch (error) {
    return [];
  }
}

export function createTrackLabelMap(tracksLabelCatalog) {
  const trackLabelByKey = new Map();
  if (!Array.isArray(tracksLabelCatalog)) {
    return trackLabelByKey;
  }
  tracksLabelCatalog.forEach((group) => {
    const labels = Array.isArray(group?.labels) ? group.labels : [];
    labels.forEach((entry) => {
      if (!entry || typeof entry !== "object") {
        return;
      }
      const key = typeof entry.key === "string" ? entry.key : "";
      const label = typeof entry.label === "string" ? entry.label : "";
      if (!key || !label || trackLabelByKey.has(key)) {
        return;
      }
      trackLabelByKey.set(key, label);
    });
  });
  return trackLabelByKey;
}

export function createUiState() {
  return {
    activeTrackId: null,
    activeTrackData: null,
    hasUnsavedUserDataChanges: false,
    selectedTrackFilterLabelKeys: new Set(),
    selectedMissingTrackFilterCategories: new Set(),
    queueTrackIds: [],
    queueIndex: -1,
    queueStatus: "idle",
    playbackMode: "none",
    queueNotice: "",
    lastQueueSnapshotMeta: null,
  };
}

export function clearQueue(state) {
  state.queueTrackIds = [];
  state.queueIndex = -1;
  state.queueStatus = "idle";
  state.queueNotice = "";
  state.lastQueueSnapshotMeta = null;
}

export function setQueueSnapshot(state, trackIds, queueIndex = 0) {
  const normalizedTrackIds = Array.isArray(trackIds)
    ? trackIds.filter((trackId) => typeof trackId === "string" && trackId.trim() !== "")
    : [];
  state.queueTrackIds = normalizedTrackIds;
  if (normalizedTrackIds.length === 0) {
    state.queueIndex = -1;
    state.queueStatus = "idle";
    state.lastQueueSnapshotMeta = null;
    return;
  }
  const nextIndex = Number.isInteger(queueIndex) ? queueIndex : 0;
  state.queueIndex = Math.min(Math.max(nextIndex, 0), normalizedTrackIds.length - 1);
  state.queueStatus = "ready";
  state.lastQueueSnapshotMeta = {
    createdAt: Date.now(),
    count: normalizedTrackIds.length,
  };
}

export function hasQueueTracks(state) {
  return Array.isArray(state.queueTrackIds) && state.queueTrackIds.length > 0;
}

export function markTrackUserDataSaved(state, setStatus) {
  state.hasUnsavedUserDataChanges = false;
  setStatus("saved");
}

export function markTrackUserDataUnsaved(state, setStatus) {
  state.hasUnsavedUserDataChanges = true;
  setStatus("unsaved changes");
}

export function confirmDiscardUnsavedChanges(state, nextTrackId = null) {
  if (
    state.hasUnsavedUserDataChanges
    && state.activeTrackId
    && nextTrackId
    && state.activeTrackId !== nextTrackId
  ) {
    return window.confirm("You have unsaved changes. Leave this track without saving?");
  }
  return true;
}
