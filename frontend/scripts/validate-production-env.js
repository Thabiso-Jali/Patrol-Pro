const apiBaseUrl = process.env.REACT_APP_API_BASE_URL?.trim();

if (!apiBaseUrl) {
  console.error(
    'Production build blocked: REACT_APP_API_BASE_URL must point to the deployed API origin.'
  );
  process.exit(1);
}

let parsed;
try {
  parsed = new URL(apiBaseUrl);
} catch {
  console.error('Production build blocked: REACT_APP_API_BASE_URL must be a valid URL.');
  process.exit(1);
}

if (!['http:', 'https:'].includes(parsed.protocol)) {
  console.error('Production build blocked: API URL must use HTTP or HTTPS.');
  process.exit(1);
}

if (['localhost', '127.0.0.1'].includes(parsed.hostname)) {
  console.error('Production build blocked: API URL cannot use localhost.');
  process.exit(1);
}
