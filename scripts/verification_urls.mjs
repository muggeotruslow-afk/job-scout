// Baidu's Page bundle redirects debugger-connected browsers to about:blank.
// The same official bundle exposes dev=0 to disable that UI-only check.
// Keep the original source URL; this parameter is used only for verification.
export function verificationUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol === 'https:' && url.hostname === 'talent.baidu.com' &&
        /^\/jobs\/detail\/INTERN\/[^/]+\/?$/.test(url.pathname)) {
      url.searchParams.set('dev', '0');
      return url.href;
    }
  } catch {
    // Leave invalid URLs to the existing liveness URL guard.
  }
  return value;
}
