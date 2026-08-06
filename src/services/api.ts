import axios from 'axios';

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Ensure the base URL always ends with /api/v1 to avoid bypassing the API version prefix
const getNormalizedBaseUrl = (url: string) => {
  if (!url) return '/api/v1';
  const cleanUrl = url.replace(/\/+$/, '');
  if ((cleanUrl.startsWith('http://') || cleanUrl.startsWith('https://')) && !cleanUrl.endsWith('/api/v1')) {
    return `${cleanUrl}/api/v1`;
  }
  return cleanUrl;
};

// Base Axios instance configured for Flask backend
export const api = axios.create({
  baseURL: getNormalizedBaseUrl(rawBaseUrl),
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.warn('API Error (falling back to mock responses if available):', error.message);
    return Promise.reject(error);
  }
);

export default api;
