import axios from 'axios';

// Base Axios instance configured for Flask backend
export const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1',
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
