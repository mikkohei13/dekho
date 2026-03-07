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
  };
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
