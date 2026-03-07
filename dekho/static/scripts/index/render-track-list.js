import { domSafeValue, escapeHtml, parseLabelKeys } from "./dom.js";

const MISSING_LABEL_FILTER_CATEGORIES = ["playlist", "like", "setting"];

function hasPlaylistLabel(labelKeys) {
  if (!Array.isArray(labelKeys)) {
    return false;
  }
  return labelKeys.some((labelKey) => labelKey.startsWith("playlist."));
}

function getTrackLikeStars(labelKeys) {
  const labelKeySet = new Set(Array.isArray(labelKeys) ? labelKeys : []);
  if (labelKeySet.has("like.like3")) {
    return 3;
  }
  if (labelKeySet.has("like.like2")) {
    return 2;
  }
  if (labelKeySet.has("like.like1")) {
    return 1;
  }
  return 0;
}

function remoteTagsIndicatorHtml() {
  return "<span class=\"remote-tags-indicator\">✦</span>";
}

function getTrackBadgesHtml(labelKeys, trackHasRemoteTags) {
  let badgesHtml = "";
  if (hasPlaylistLabel(labelKeys)) {
    badgesHtml += "<span class=\"track-badge playlist-badge\" title=\"In playlist\">≣</span>";
  }
  const starCount = getTrackLikeStars(labelKeys);
  if (starCount > 0) {
    badgesHtml += `<span class="track-badge likes-badge" title="Rating">${"★".repeat(starCount)}</span>`;
  }
  if (trackHasRemoteTags) {
    badgesHtml += remoteTagsIndicatorHtml();
  }
  return badgesHtml;
}

export function getDisplayTitle(data) {
  return data.title_new || "Unknown";
}

export function hasRemoteTags(tags) {
  return tags !== null && tags !== undefined && String(tags).trim() !== "";
}

export function toTrackMetaText(value) {
  const text = String(value ?? "").trim();
  return text || "-";
}

export function renderTrackItemTitle(trackItem, displayTitle, labelKeys, trackHasRemoteTags) {
  const titleElement = trackItem.querySelector("[data-track-item-title]");
  if (!(titleElement instanceof HTMLElement)) {
    return;
  }
  titleElement.innerHTML = `${escapeHtml(displayTitle)}${getTrackBadgesHtml(labelKeys, trackHasRemoteTags)}`;
}

export function updateTrackItemLabels(trackId, labelKeys, trackLabelByKey) {
  const trackItem = document.querySelector(`.track-item[data-track-id="${CSS.escape(trackId)}"]`);
  if (!(trackItem instanceof HTMLElement)) {
    return;
  }

  const normalizedKeys = Array.isArray(labelKeys)
    ? labelKeys
      .filter((key) => typeof key === "string" && key)
      .map((key) => key.trim())
      .filter(Boolean)
    : [];
  trackItem.dataset.labelKeys = normalizedKeys.join(",");

  const labelsElement = trackItem.querySelector("[data-track-item-labels]");
  if (labelsElement instanceof HTMLElement) {
    const visibleLabels = normalizedKeys
      .map((key) => trackLabelByKey.get(key) || key)
      .join(", ");
    labelsElement.textContent = visibleLabels || "-";
  }

  const displayTitle = trackItem.dataset.displayTitle || "Unknown";
  const trackHasRemoteTags = trackItem.dataset.hasRemoteTags === "1";
  renderTrackItemTitle(trackItem, displayTitle, normalizedKeys, trackHasRemoteTags);
}

function getTrackItemLabelKeys(item) {
  return new Set(parseLabelKeys(item.dataset.labelKeys));
}

function getTrackItemLabelCategories(item) {
  const categories = new Set();
  parseLabelKeys(item.dataset.labelKeys).forEach((labelKey) => {
    const category = labelKey.split(".", 1)[0];
    if (category) {
      categories.add(category);
    }
  });
  return categories;
}

export function renderTrackLabelFilterOptions({
  tracksLabelFilterOptions,
  tracksLabelCatalog,
  selectedTrackFilterLabelKeys,
  selectedMissingTrackFilterCategories,
}) {
  if (!(tracksLabelFilterOptions instanceof HTMLElement)) {
    return;
  }
  if (!Array.isArray(tracksLabelCatalog) || tracksLabelCatalog.length === 0) {
    tracksLabelFilterOptions.innerHTML = "<p class=\"empty-state\">No labels configured.</p>";
    return;
  }

  const categories = [];
  tracksLabelCatalog.forEach((group) => {
    const categoryName = typeof group?.display_name === "string" && group.display_name
      ? group.display_name
      : (typeof group?.category === "string" ? group.category : "");
    const labels = Array.isArray(group?.labels) ? group.labels : [];
    if (!categoryName || labels.length === 0) {
      return;
    }
    const options = [];
    labels.forEach((labelEntry) => {
      if (!labelEntry || typeof labelEntry !== "object") {
        return;
      }
      const key = typeof labelEntry.key === "string" ? labelEntry.key : "";
      const label = typeof labelEntry.label === "string" ? labelEntry.label : "";
      if (!key || !label) {
        return;
      }
      options.push({ key, label });
    });
    if (options.length > 0) {
      categories.push({ categoryName, options });
    }
  });

  const missingCategorySectionHtml = `
    <section class="tracks-filter-category">
      <h4 class="tracks-filter-category-heading">Missing category labels</h4>
      <div class="tracks-filter-category-options">
        ${MISSING_LABEL_FILTER_CATEGORIES.map((categoryName) => {
          const inputId = `tracks-filter-missing-${domSafeValue(categoryName)}`;
          const checked = selectedMissingTrackFilterCategories.has(categoryName) ? " checked" : "";
          return `
            <label for="${escapeHtml(inputId)}" class="tracks-filter-option">
              <input
                id="${escapeHtml(inputId)}"
                class="tracks-filter-option-input"
                type="checkbox"
                data-missing-category="${escapeHtml(categoryName)}"${checked}
              >
              <span>No ${escapeHtml(categoryName)} label</span>
            </label>
          `;
        }).join("")}
      </div>
    </section>
  `;

  const labelCategorySectionsHtml = categories.map(({ categoryName, options }) => {
    const optionsHtml = options.map(({ key, label }) => {
      const inputId = `tracks-filter-label-${domSafeValue(key)}`;
      const checked = selectedTrackFilterLabelKeys.has(key) ? " checked" : "";
      return `
        <label for="${escapeHtml(inputId)}" class="tracks-filter-option">
          <input
            id="${escapeHtml(inputId)}"
            class="tracks-filter-option-input"
            type="checkbox"
            data-label-key="${escapeHtml(key)}"${checked}
          >
          <span>${escapeHtml(label)}</span>
        </label>
      `;
    }).join("");

    return `
      <section class="tracks-filter-category">
        <h4 class="tracks-filter-category-heading">${escapeHtml(categoryName)}</h4>
        <div class="tracks-filter-category-options">${optionsHtml}</div>
      </section>
    `;
  }).join("");

  tracksLabelFilterOptions.innerHTML = `${missingCategorySectionHtml}${labelCategorySectionsHtml}`;
}

export function updateTracksFilterSummary({
  tracksLabelFilterSummary,
  tracksSelectedLabels,
  tracksClearFiltersButton,
  tracksFilterInput,
  selectedTrackFilterLabelKeys,
  selectedMissingTrackFilterCategories,
  trackLabelByKey,
}) {
  if (tracksLabelFilterSummary instanceof HTMLElement) {
    const selectedCount = selectedTrackFilterLabelKeys.size + selectedMissingTrackFilterCategories.size;
    tracksLabelFilterSummary.textContent = `Labels (${selectedCount})`;
  }

  if (tracksSelectedLabels instanceof HTMLElement) {
    const selectedLabels = Array.from(selectedTrackFilterLabelKeys)
      .map((key) => trackLabelByKey.get(key) || key);
    const missingCategoryLabels = Array.from(selectedMissingTrackFilterCategories)
      .map((category) => `No ${category}`);
    const selectedFilterTexts = selectedLabels.concat(missingCategoryLabels);
    if (selectedFilterTexts.length === 0) {
      tracksSelectedLabels.hidden = true;
      tracksSelectedLabels.textContent = "";
    } else {
      const maxVisible = 8;
      const visibleLabels = selectedFilterTexts.slice(0, maxVisible).join(", ");
      const moreCount = selectedFilterTexts.length - maxVisible;
      tracksSelectedLabels.hidden = false;
      tracksSelectedLabels.textContent = moreCount > 0
        ? `Selected: ${visibleLabels} (+${moreCount})`
        : `Selected: ${visibleLabels}`;
    }
  }

  if (tracksClearFiltersButton instanceof HTMLButtonElement) {
    const hasTextQuery = tracksFilterInput instanceof HTMLInputElement && tracksFilterInput.value.trim() !== "";
    const hasLabelFilters = selectedTrackFilterLabelKeys.size > 0 || selectedMissingTrackFilterCategories.size > 0;
    tracksClearFiltersButton.disabled = !hasTextQuery && !hasLabelFilters;
  }
}

function updateTracksFilterCount(trackItems, tracksFilterCount) {
  if (!(tracksFilterCount instanceof HTMLElement)) {
    return;
  }
  const total = trackItems.length;
  const matched = trackItems.filter((item) => !item.hidden).length;
  tracksFilterCount.textContent = `${matched}/${total} tracks`;
}

export function applyTracksFilter({
  trackItems,
  tracksFilterInput,
  tracksFilterCount,
  selectedTrackFilterLabelKeys,
  selectedMissingTrackFilterCategories,
  tracksLabelFilterSummary,
  tracksSelectedLabels,
  tracksClearFiltersButton,
  trackLabelByKey,
}) {
  const query = String(tracksFilterInput instanceof HTMLInputElement ? tracksFilterInput.value : "")
    .trim()
    .toLocaleLowerCase();
  trackItems.forEach((item) => {
    const trackMetaBlock = item.querySelector(".track-meta-block");
    const haystack = `${item.textContent || ""} ${trackMetaBlock?.textContent || ""}`.toLocaleLowerCase();
    const textMatches = query ? haystack.includes(query) : true;
    const trackLabelKeys = getTrackItemLabelKeys(item);
    const labelsMatch = Array.from(selectedTrackFilterLabelKeys).every(
      (labelKey) => trackLabelKeys.has(labelKey)
    );
    const trackLabelCategories = getTrackItemLabelCategories(item);
    const missingCategoryMatches = Array.from(selectedMissingTrackFilterCategories).every(
      (category) => !trackLabelCategories.has(category)
    );
    item.hidden = !(textMatches && labelsMatch && missingCategoryMatches);
  });
  updateTracksFilterCount(trackItems, tracksFilterCount);
  updateTracksFilterSummary({
    tracksLabelFilterSummary,
    tracksSelectedLabels,
    tracksClearFiltersButton,
    tracksFilterInput,
    selectedTrackFilterLabelKeys,
    selectedMissingTrackFilterCategories,
    trackLabelByKey,
  });
}

export function refreshTrackItemBadges(trackItems) {
  trackItems.forEach((item) => {
    const displayTitle = item.dataset.displayTitle || "Unknown";
    const labelKeys = parseLabelKeys(item.dataset.labelKeys);
    const trackHasRemoteTags = item.dataset.hasRemoteTags === "1";
    renderTrackItemTitle(item, displayTitle, labelKeys, trackHasRemoteTags);
  });
}

function getTrackItemById(trackId) {
  const item = document.querySelector(`.track-item[data-track-id="${CSS.escape(trackId)}"]`);
  return item instanceof HTMLElement ? item : null;
}

function getTrackItemDisplayTitle(item) {
  if (!(item instanceof HTMLElement)) {
    return "Unknown";
  }
  return item.dataset.displayTitle
    || item.querySelector("[data-track-item-display-title]")?.textContent?.trim()
    || "Unknown";
}

function getQueueTrackImageSrc(trackId) {
  return `/api/tracks/${encodeURIComponent(trackId)}/image`;
}

export function getVisibleTrackIds(trackItems) {
  if (!Array.isArray(trackItems)) {
    return [];
  }
  return trackItems
    .filter((item) => item instanceof HTMLElement && !item.hidden)
    .map((item) => item.dataset.trackId || "")
    .filter(Boolean);
}

export function renderQueueDrawer({
  queueTrackIds,
  queueIndex,
  queueList,
  queueCount,
  queueEmptyState,
  queueNotice,
  queueNoticeText,
  selectedTrackPlayer,
  playbackMode,
}) {
  if (!(queueList instanceof HTMLElement)) {
    return;
  }
  const hasQueue = Array.isArray(queueTrackIds) && queueTrackIds.length > 0;
  if (queueCount instanceof HTMLElement) {
    queueCount.textContent = hasQueue
      ? `${Math.max(queueIndex + 1, 1)}/${queueTrackIds.length}`
      : "0/0";
  }
  if (queueEmptyState instanceof HTMLElement) {
    queueEmptyState.hidden = hasQueue;
  }
  if (queueNotice instanceof HTMLElement) {
    queueNotice.textContent = queueNoticeText || "";
    queueNotice.hidden = !queueNoticeText;
  }
  if (!hasQueue) {
    queueList.innerHTML = "";
    return;
  }
  const playingTrackId = selectedTrackPlayer instanceof HTMLAudioElement
    ? (selectedTrackPlayer.dataset.trackId || "")
    : "";
  const listHtml = queueTrackIds.map((trackId, index) => {
    const item = getTrackItemById(trackId);
    const title = getTrackItemDisplayTitle(item);
    const isQueuedCurrent = index === queueIndex;
    const isPlaying = playbackMode === "queue" && playingTrackId === trackId;
    return `
      <li>
        <button
          type="button"
          class="queue-track-item${isQueuedCurrent ? " is-current" : ""}${isPlaying ? " is-playing" : ""}"
          data-queue-index="${index}"
          data-track-id="${escapeHtml(trackId)}"
        >
          <img
            class="track-item-image queue-track-image"
            src="${escapeHtml(getQueueTrackImageSrc(trackId))}"
            width="34"
            height="34"
            loading="lazy"
          >
          <span class="queue-track-title">${escapeHtml(title)}</span>
        </button>
      </li>
    `;
  }).join("");
  queueList.innerHTML = listHtml;
}

export function renderTrackListItem(trackId, data, deps) {
  const { trackLabelByKey, applyFilter } = deps;
  const trackItem = document.querySelector(`.track-item[data-track-id="${CSS.escape(trackId)}"]`);
  if (!(trackItem instanceof HTMLElement)) {
    return;
  }

  const displayTitle = getDisplayTitle(data);
  trackItem.dataset.displayTitle = displayTitle;
  trackItem.dataset.hasRemoteTags = hasRemoteTags(data.tags) ? "1" : "0";

  const trackMetaTitle = trackItem.querySelector("[data-track-item-display-title]");
  if (trackMetaTitle instanceof HTMLElement) {
    trackMetaTitle.textContent = displayTitle;
  }

  const trackMetaTags = trackItem.querySelector("[data-track-item-tags]");
  if (trackMetaTags instanceof HTMLElement) {
    trackMetaTags.textContent = toTrackMetaText(data.tags);
  }

  const trackMetaNotes = trackItem.querySelector("[data-track-item-notes]");
  if (trackMetaNotes instanceof HTMLElement) {
    trackMetaNotes.textContent = toTrackMetaText(data.notes);
  }

  updateTrackItemLabels(trackId, data.labels, trackLabelByKey);
  applyFilter();
}
