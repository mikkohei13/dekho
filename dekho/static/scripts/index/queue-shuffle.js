function bytesToHex(bytes) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function hashTrackSeed(trackId, seed) {
  const payload = `${seed}:${trackId}`;
  const encoded = new TextEncoder().encode(payload);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return bytesToHex(new Uint8Array(digest));
}

export async function sortTrackIdsBySeed(trackIds, seed) {
  const ids = Array.isArray(trackIds) ? trackIds.filter((id) => typeof id === "string" && id) : [];
  const hashed = await Promise.all(
    ids.map(async (trackId) => ({
      trackId,
      hash: await hashTrackSeed(trackId, seed),
    })),
  );
  hashed.sort((a, b) => {
    if (a.hash < b.hash) {
      return -1;
    }
    if (a.hash > b.hash) {
      return 1;
    }
    if (a.trackId < b.trackId) {
      return -1;
    }
    if (a.trackId > b.trackId) {
      return 1;
    }
    return 0;
  });
  return hashed.map((entry) => entry.trackId);
}

export function parseShuffleSeed(value, fallback = 42) {
  const parsed = Number.parseInt(String(value ?? "").trim(), 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}
