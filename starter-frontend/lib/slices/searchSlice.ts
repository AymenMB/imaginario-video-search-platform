import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { searchAPI } from '../api';

interface SearchResult {
  video_id: number;
  title: string;
  relevance_score: number;
  matched_text: string;
}

interface SearchState {
  results: SearchResult[];
  loading: boolean;
  error: string | null;
  currentJobId: string | null;
}

const initialState: SearchState = {
  results: [],
  loading: false,
  error: null,
  currentJobId: null,
};

export const submitSearch = createAsyncThunk(
  'search/submitSearch',
  async ({ userId, query, videoIds }: { userId: number; query: string; videoIds?: number[] }) => {
    return await searchAPI.submitSearch(userId, query, videoIds);
  }
);

export const getSearchResults = createAsyncThunk(
  'search/getSearchResults',
  async ({ userId, jobId }: { userId: number; jobId: string }) => {
    return await searchAPI.getSearchResults(userId, jobId);
  }
);

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    clearResults: (state) => {
      state.results = [];
      state.currentJobId = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitSearch.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(submitSearch.fulfilled, (state, action) => {
        state.currentJobId = action.payload.job_id;
        if (action.payload.status === 'completed' && action.payload.results) {
          state.results = action.payload.results;
          state.loading = false;
        }
      })
      .addCase(submitSearch.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Search failed';
      })
      .addCase(getSearchResults.fulfilled, (state, action) => {
        if (action.payload.status === 'completed') {
          state.results = action.payload.results || [];
          state.loading = false;
        }
      });
  },
});

export const { clearResults } = searchSlice.actions;
export default searchSlice.reducer;

