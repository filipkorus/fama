import axios from 'axios'
import { API_URL } from '../config'
import { getStoredToken, storeAuthData, clearAuthData } from './auth'

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  withCredentials: true,
});

// Add request interceptor
api.interceptors.request.use(
  (config) => {

    const token = getStoredToken();
    if (token) {
      config.headers = config.headers || {};
      config.headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(config.data instanceof FormData)) {
      config.headers = config.headers || {};
      if (!config.headers['Content-Type']) {
        config.headers['Content-Type'] = 'application/json';
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {

    const originalRequest: any = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const { data } = await axios.post(
          `${API_URL}/api/auth/refresh`,
          {},
          { withCredentials: true }
        )

        const newToken = data.access_token as string

        const username = localStorage.getItem('username') || ''
        storeAuthData(newToken, username)

        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`

        return api(originalRequest)
      } catch (refreshError) {
        clearAuthData()
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)
