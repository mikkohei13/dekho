async function parseJsonResponse(response, fallbackMessage) {
  let payload = {};
  try {
    payload = await response.json();
  } catch (error) {
    payload = {};
  }
  if (!response.ok) {
    throw new Error(payload.error || fallbackMessage);
  }
  return payload;
}

export async function fetchTrackDetails(trackId) {
  const response = await fetch(`/api/tracks/${encodeURIComponent(trackId)}`);
  return parseJsonResponse(response, "Unable to load track details.");
}

export async function fetchTrackRemoteData(trackId) {
  const response = await fetch(`/api/tracks/${encodeURIComponent(trackId)}/remote-data`, {
    method: "POST",
  });
  return parseJsonResponse(response, "Failed to fetch data from Suno.");
}

export async function saveTrackUserData(trackId, payload) {
  const response = await fetch(`/api/tracks/${encodeURIComponent(trackId)}/user-data`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response, "Failed to save track data.");
}
