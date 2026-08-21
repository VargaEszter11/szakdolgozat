/**
 * Shared display-name helpers (profile avatar, header avatar, etc.).
 */
(function (root) {
  function displayNameInitials(name) {
    if (!name || !String(name).trim()) return '?';
    var s = String(name).trim();
    var parts = s.split(/[\s._-]+/).filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    if (s.length >= 2) return s.slice(0, 2).toUpperCase();
    return s.charAt(0).toUpperCase();
  }

  root.displayNameInitials = displayNameInitials;
})(typeof window !== 'undefined' ? window : globalThis);
