import { parseLabelKeys } from "./dom.js";
import { confirmDiscardUnsavedChanges } from "./state.js";

export function setScanLinkBusy(scanLink) {
  if (!(scanLink instanceof HTMLAnchorElement)) {
    return;
  }
  scanLink.dataset.scanBusy = "true";
  scanLink.setAttribute("aria-disabled", "true");
  scanLink.classList.add("is-disabled");
  scanLink.textContent = "Scanning...";
}

export function bindTrackItemEvents(trackItems, state, loadTrackDetails, onStartQueueFromTrack) {
  trackItems.forEach((item) => {
    const trackId = item.dataset.trackId;
    if (!trackId) {
      return;
    }

    const openTrack = () => {
      if (!confirmDiscardUnsavedChanges(state, trackId)) {
        return;
      }
      loadTrackDetails(trackId, item);
    };

    item.addEventListener("click", (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.closest(".track-item-queue-btn")) {
        return;
      }
      openTrack();
    });
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        const target = event.target;
        if (target instanceof HTMLElement && target.closest(".track-item-queue-btn")) {
          return;
        }
        event.preventDefault();
        openTrack();
      }
    });

    const queueButton = item.querySelector(".track-item-queue-btn");
    if (queueButton instanceof HTMLButtonElement) {
      queueButton.addEventListener("click", (event) => {
        event.stopPropagation();
        onStartQueueFromTrack?.(trackId);
      });
    }
  });
}

export function bindFilterEvents({
  tracksFilterInput,
  tracksLabelFilterOptions,
  tracksClearFiltersButton,
  tracksLabelFilter,
  selectedTrackFilterLabelKeys,
  selectedMissingTrackFilterCategories,
  applyTracksFilter,
  renderTrackLabelFilterOptions,
}) {
  if (tracksFilterInput instanceof HTMLInputElement) {
    tracksFilterInput.addEventListener("input", applyTracksFilter);
  }

  if (tracksLabelFilterOptions instanceof HTMLElement) {
    tracksLabelFilterOptions.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement) || !target.classList.contains("tracks-filter-option-input")) {
        return;
      }
      const missingCategory = target.dataset.missingCategory;
      if (missingCategory) {
        if (target.checked) {
          selectedMissingTrackFilterCategories.add(missingCategory);
        } else {
          selectedMissingTrackFilterCategories.delete(missingCategory);
        }
        applyTracksFilter();
        return;
      }
      const labelKey = target.dataset.labelKey;
      if (!labelKey) {
        return;
      }
      if (target.checked) {
        selectedTrackFilterLabelKeys.add(labelKey);
      } else {
        selectedTrackFilterLabelKeys.delete(labelKey);
      }
      applyTracksFilter();
    });
  }

  if (tracksClearFiltersButton instanceof HTMLButtonElement) {
    tracksClearFiltersButton.addEventListener("click", () => {
      selectedTrackFilterLabelKeys.clear();
      selectedMissingTrackFilterCategories.clear();
      if (tracksFilterInput instanceof HTMLInputElement) {
        tracksFilterInput.value = "";
      }
      if (tracksLabelFilter instanceof HTMLDetailsElement) {
        tracksLabelFilter.open = false;
      }
      renderTrackLabelFilterOptions();
      applyTracksFilter();
    });
  }

  if (tracksLabelFilter instanceof HTMLDetailsElement) {
    tracksLabelFilter.addEventListener("toggle", () => {
      if (tracksLabelFilter.open) {
        renderTrackLabelFilterOptions();
      }
    });

    document.addEventListener("click", (event) => {
      if (!tracksLabelFilter.open) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Node) || tracksLabelFilter.contains(target)) {
        return;
      }
      tracksLabelFilter.open = false;
    });
  }
}

export function bindScanLinkEvent(scanLink) {
  if (!(scanLink instanceof HTMLAnchorElement)) {
    return;
  }
  scanLink.addEventListener("click", (event) => {
    if (scanLink.dataset.scanBusy === "true") {
      event.preventDefault();
      return;
    }
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    setScanLinkBusy(scanLink);
  });
}

export function bindContentPanelEvents({
  contentPanel,
  contentPanelBody,
  state,
  setTrackUserDataSaveStatus,
  onGetRemoteData,
  onSaveUserData,
  onPlayCurrentTrack,
}) {
  if (!(contentPanel instanceof HTMLElement)) {
    return;
  }

  contentPanel.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.id === "get-remote-data-btn" && state.activeTrackId) {
      if (state.hasUnsavedUserDataChanges) {
        const shouldContinue = window.confirm("You have unsaved changes. Continue without saving?");
        if (!shouldContinue) {
          return;
        }
      }
      onGetRemoteData(state.activeTrackId);
    }
    if (target.id === "save-track-user-data-btn" && state.activeTrackId) {
      onSaveUserData(state.activeTrackId);
    }
    if (target.id === "play-current-track-btn" && state.activeTrackData) {
      onPlayCurrentTrack(state.activeTrackData);
    }
  });

  const markDirtyIfTrackForm = (target) => {
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.closest("#track-user-data-form")) {
      state.hasUnsavedUserDataChanges = true;
      setTrackUserDataSaveStatus("unsaved changes");
    }
  };

  contentPanel.addEventListener("input", (event) => {
    markDirtyIfTrackForm(event.target);
  });

  contentPanel.addEventListener("change", (event) => {
    markDirtyIfTrackForm(event.target);
  });

  contentPanel.addEventListener("submit", (event) => {
    const target = event.target;
    if (target instanceof HTMLFormElement && target.id === "track-user-data-form") {
      event.preventDefault();
    }
  });

  contentPanel.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }
    if (!target.closest("#track-user-data-form")) {
      return;
    }
    event.preventDefault();
  });
}

export function bindQueuePanelEvents({
  tracksPanel,
  onToggleQueueDrawer,
  onRecreateQueueFromFilter,
  onResumeQueue,
  onPlayQueueIndex,
  onShowQueueTrack,
}) {
  if (!(tracksPanel instanceof HTMLElement)) {
    return;
  }
  tracksPanel.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.id === "queue-drawer-toggle-btn") {
      onToggleQueueDrawer();
      return;
    }
    if (target.id === "recreate-queue-btn") {
      onRecreateQueueFromFilter();
      return;
    }
    if (target.id === "resume-queue-btn") {
      onResumeQueue();
      return;
    }
    const playButton = target.closest(".queue-track-play-btn");
    if (playButton instanceof HTMLButtonElement) {
      const index = Number.parseInt(playButton.dataset.queueIndex || "", 10);
      if (!Number.isFinite(index)) {
        return;
      }
      onPlayQueueIndex(index);
      return;
    }
    const showButton = target.closest(".queue-track-show-btn");
    if (showButton instanceof HTMLButtonElement) {
      const trackId = showButton.dataset.trackId || "";
      if (!trackId) {
        return;
      }
      onShowQueueTrack(trackId);
    }
  });
}

export function bindPersistentQueueControls({
  previousQueueTrackButton,
  nextQueueTrackButton,
  onPreviousQueueTrack,
  onNextQueueTrack,
}) {
  if (previousQueueTrackButton instanceof HTMLButtonElement) {
    previousQueueTrackButton.addEventListener("click", onPreviousQueueTrack);
  }
  if (nextQueueTrackButton instanceof HTMLButtonElement) {
    nextQueueTrackButton.addEventListener("click", onNextQueueTrack);
  }
}

export function showPlayingTrackInContentPanel(state, selectedTrackPlayer, loadTrackDetails) {
  const trackId = selectedTrackPlayer instanceof HTMLAudioElement
    ? (selectedTrackPlayer.dataset.trackId ?? "")
    : "";
  if (!trackId) {
    return;
  }
  const trackItem = document.querySelector(`.track-item[data-track-id="${CSS.escape(trackId)}"]`);
  if (!(trackItem instanceof HTMLElement)) {
    return;
  }
  if (!confirmDiscardUnsavedChanges(state, trackId)) {
    return;
  }
  loadTrackDetails(trackId, trackItem);
}

export function collectSelectedTrackLabels(contentPanelBody) {
  const selectedLabelInputs = contentPanelBody
    ? contentPanelBody.querySelectorAll(".track-label-input:checked")
    : [];
  const labels = [];
  selectedLabelInputs.forEach((input) => {
    if (!(input instanceof HTMLInputElement)) {
      return;
    }
    const labelKey = input.dataset.labelKey;
    if (typeof labelKey !== "string" || !labelKey) {
      return;
    }
    labels.push(labelKey);
  });
  return labels;
}

export function refreshTrackBadgesFromDataAttrs(trackItems, renderTrackItemTitle) {
  trackItems.forEach((item) => {
    const displayTitle = item.dataset.displayTitle || "Unknown";
    const labelKeys = parseLabelKeys(item.dataset.labelKeys);
    const trackHasRemoteTags = item.dataset.hasRemoteTags === "1";
    renderTrackItemTitle(item, displayTitle, labelKeys, trackHasRemoteTags);
  });
}
