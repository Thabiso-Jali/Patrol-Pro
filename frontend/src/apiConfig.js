const configuredBaseUrl = process.env.REACT_APP_API_BASE_URL?.trim();
const developmentDefault =
  process.env.NODE_ENV === 'development'
    ? ['http://', 'localhost', ':8000'].join('')
    : '';

if (process.env.NODE_ENV === 'production' && !configuredBaseUrl) {
  throw new Error(
    'REACT_APP_API_BASE_URL is required for production builds and must point to the deployed API.'
  );
}

const serviceBaseUrl = (configuredBaseUrl || developmentDefault).replace(/\/+$/, '');

export const API_BASE_URL = serviceBaseUrl.endsWith('/api/v1')
  ? serviceBaseUrl
  : `${serviceBaseUrl}/api/v1`;
