/**
 * Analytics Redux Slice
 * 
 * Manages state for developer dashboard analytics:
 * - API usage statistics
 * - Daily usage trends
 * - Endpoint breakdown
 * - Search jobs tracking
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { analyticsAPI, searchJobsAPI } from '../api';

// Types
interface UsageSummary {
  total_requests: number;
  successful_requests: number;
  error_requests: number;
  error_rate: number;
  avg_response_time_ms: number;
  p95_response_time_ms: number;
  p99_response_time_ms: number;
}

interface DailyUsage {
  date: string;
  total: number;
  successful: number;
  errors: number;
  avg_response_time_ms: number;
}

interface EndpointUsage {
  endpoint: string;
  method: string;
  total: number;
  successful: number;
  errors: number;
  avg_response_time_ms: number;
}

interface SearchJob {
  job_id: string;
  user_id: number;
  query: string;
  algorithm: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  results_count: number;
  execution_time_ms: number;
  created_at: string;
  completed_at: string | null;
  results?: any[];
}

interface Pagination {
  page: number;
  per_page: number;
  total_pages: number;
  total_items: number;
  has_next: boolean;
  has_prev: boolean;
}

interface AnalyticsState {
  summary: UsageSummary | null;
  dailyUsage: DailyUsage[];
  endpointUsage: EndpointUsage[];
  searchJobs: SearchJob[];
  selectedJob: SearchJob | null;
  pagination: Pagination | null;
  loading: boolean;
  jobsLoading: boolean;
  error: string | null;
}

const initialState: AnalyticsState = {
  summary: null,
  dailyUsage: [],
  endpointUsage: [],
  searchJobs: [],
  selectedJob: null,
  pagination: null,
  loading: false,
  jobsLoading: false,
  error: null,
};

// Async Thunks
export const fetchUsageStats = createAsyncThunk(
  'analytics/fetchUsageStats',
  async (params: { startDate?: string; endDate?: string; apiKeyId?: string } = {}) => {
    const response = await analyticsAPI.getUsageStats(params);
    return response;
  }
);

export const fetchDailyUsage = createAsyncThunk(
  'analytics/fetchDailyUsage',
  async (params: { startDate?: string; endDate?: string; apiKeyId?: string } = {}) => {
    const response = await analyticsAPI.getDailyUsage(params);
    return response;
  }
);

export const fetchEndpointUsage = createAsyncThunk(
  'analytics/fetchEndpointUsage',
  async () => {
    const response = await analyticsAPI.getEndpointUsage();
    return response;
  }
);

export const fetchSearchJobs = createAsyncThunk(
  'analytics/fetchSearchJobs',
  async (params: { status?: string; page?: number; perPage?: number } = {}) => {
    const response = await searchJobsAPI.listJobs(params);
    return response;
  }
);

export const fetchJobDetails = createAsyncThunk(
  'analytics/fetchJobDetails',
  async (jobId: string) => {
    const response = await searchJobsAPI.getJobDetails(jobId);
    return response;
  }
);

// Slice
const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearSelectedJob: (state) => {
      state.selectedJob = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Usage Stats
      .addCase(fetchUsageStats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUsageStats.fulfilled, (state, action) => {
        state.loading = false;
        state.summary = action.payload.summary;
      })
      .addCase(fetchUsageStats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch usage stats';
      })
      // Daily Usage
      .addCase(fetchDailyUsage.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchDailyUsage.fulfilled, (state, action) => {
        state.loading = false;
        state.dailyUsage = action.payload.daily;
      })
      .addCase(fetchDailyUsage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch daily usage';
      })
      // Endpoint Usage
      .addCase(fetchEndpointUsage.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchEndpointUsage.fulfilled, (state, action) => {
        state.loading = false;
        state.endpointUsage = action.payload.endpoints;
      })
      .addCase(fetchEndpointUsage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch endpoint usage';
      })
      // Search Jobs
      .addCase(fetchSearchJobs.pending, (state) => {
        state.jobsLoading = true;
      })
      .addCase(fetchSearchJobs.fulfilled, (state, action) => {
        state.jobsLoading = false;
        state.searchJobs = action.payload.jobs;
        state.pagination = action.payload.pagination;
      })
      .addCase(fetchSearchJobs.rejected, (state, action) => {
        state.jobsLoading = false;
        state.error = action.error.message || 'Failed to fetch search jobs';
      })
      // Job Details
      .addCase(fetchJobDetails.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchJobDetails.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedJob = action.payload;
      })
      .addCase(fetchJobDetails.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch job details';
      });
  },
});

export const { clearError, clearSelectedJob } = analyticsSlice.actions;
export default analyticsSlice.reducer;
