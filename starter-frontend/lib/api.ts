/**
 * API Client
 * 
 * Complete API client for all endpoints including:
 * - Authentication
 * - Videos
 * - Search
 * - API Keys
 * - Analytics (for Developer Dashboard)
 */

import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

// Create axios instance
const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: async (email: string, password: string, name?: string) => {
    const response = await apiClient.post('/auth/register', { email, password, name });
    return response.data;
  },

  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { email, password });
    if (response.data.token && typeof window !== 'undefined') {
      localStorage.setItem('token', response.data.token);
    }
    return response.data;
  },

  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
  },
};

// Video API
export const videoAPI = {
  listVideos: async (userId: number, page?: number, perPage?: number) => {
    const params = new URLSearchParams();
    if (page) params.append('page', page.toString());
    if (perPage) params.append('per_page', perPage.toString());
    const query = params.toString();
    const url = `/users/${userId}/videos${query ? `?${query}` : ''}`;
    const response = await apiClient.get(url);
    return response.data;
  },

  getVideo: async (userId: number, videoId: number) => {
    const response = await apiClient.get(`/users/${userId}/videos/${videoId}`);
    return response.data;
  },

  createVideo: async (userId: number, data: { title: string; description?: string; duration?: number }) => {
    const response = await apiClient.post(`/users/${userId}/videos`, data);
    return response.data;
  },

  updateVideo: async (userId: number, videoId: number, data: Partial<{ title: string; description: string; duration: number }>) => {
    const response = await apiClient.put(`/users/${userId}/videos/${videoId}`, data);
    return response.data;
  },

  deleteVideo: async (userId: number, videoId: number) => {
    const response = await apiClient.delete(`/users/${userId}/videos/${videoId}`);
    return response.data;
  },
};

// Search API
export const searchAPI = {
  submitSearch: async (userId: number, query: string, videoIds?: number[], algorithm?: string) => {
    const response = await apiClient.post(`/users/${userId}/search`, {
      query,
      video_ids: videoIds,
      algorithm: algorithm || 'text_search'
    });
    return response.data;
  },

  getSearchResults: async (userId: number, jobId: string) => {
    const response = await apiClient.get(`/users/${userId}/search/${jobId}`);
    return response.data;
  },
};

// API Key API
export const apiKeyAPI = {
  createApiKey: async (name: string) => {
    const response = await apiClient.post('/auth/api-keys', { name });
    return response.data;
  },

  listApiKeys: async () => {
    const response = await apiClient.get('/auth/api-keys');
    return response.data;
  },

  deleteApiKey: async (keyId: string) => {
    const response = await apiClient.delete(`/auth/api-keys/${keyId}`);
    return response.data;
  },

  getApiKeyUsage: async (keyId: string) => {
    const response = await apiClient.get(`/auth/api-keys/${keyId}/usage`);
    return response.data;
  },

  getApiKeyDailyUsage: async (keyId: string) => {
    const response = await apiClient.get(`/auth/api-keys/${keyId}/usage/daily`);
    return response.data;
  },
};

// Analytics API (for Developer Dashboard)
export const analyticsAPI = {
  getUsageStats: async (params: { startDate?: string; endDate?: string; apiKeyId?: string } = {}) => {
    const queryParams = new URLSearchParams();
    if (params.startDate) queryParams.append('start_date', params.startDate);
    if (params.endDate) queryParams.append('end_date', params.endDate);
    if (params.apiKeyId) queryParams.append('api_key_id', params.apiKeyId);
    const query = queryParams.toString();
    const response = await apiClient.get(`/analytics/usage${query ? `?${query}` : ''}`);
    return response.data;
  },

  getDailyUsage: async (params: { startDate?: string; endDate?: string; apiKeyId?: string } = {}) => {
    const queryParams = new URLSearchParams();
    if (params.startDate) queryParams.append('start_date', params.startDate);
    if (params.endDate) queryParams.append('end_date', params.endDate);
    if (params.apiKeyId) queryParams.append('api_key_id', params.apiKeyId);
    const query = queryParams.toString();
    const response = await apiClient.get(`/analytics/usage/daily${query ? `?${query}` : ''}`);
    return response.data;
  },

  getEndpointUsage: async () => {
    const response = await apiClient.get('/analytics/usage/endpoints');
    return response.data;
  },
};

// Search Jobs API (for Developer Dashboard)
export const searchJobsAPI = {
  listJobs: async (params: { status?: string; page?: number; perPage?: number } = {}) => {
    const queryParams = new URLSearchParams();
    if (params.status) queryParams.append('status', params.status);
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.perPage) queryParams.append('per_page', params.perPage.toString());
    const query = queryParams.toString();
    const response = await apiClient.get(`/search/jobs${query ? `?${query}` : ''}`);
    return response.data;
  },

  getJobDetails: async (jobId: string) => {
    const response = await apiClient.get(`/search/jobs/${jobId}/details`);
    return response.data;
  },

  retryJob: async (jobId: string) => {
    const response = await apiClient.post(`/search/jobs/${jobId}/retry`);
    return response.data;
  },

  cancelJob: async (jobId: string) => {
    const response = await apiClient.post(`/search/jobs/${jobId}/cancel`);
    return response.data;
  },
};

// System API (for monitoring)
export const systemAPI = {
  getCircuitBreakerStatus: async () => {
    const response = await apiClient.get('/system/circuit-breaker');
    return response.data;
  },
};

export default apiClient;

