export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char]
  ));
}

export function domSafeValue(value) {
  return String(value ?? "").replace(/[^a-zA-Z0-9_-]/g, "-");
}

export function parseLabelKeys(labelKeysValue) {
  return String(labelKeysValue ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}
