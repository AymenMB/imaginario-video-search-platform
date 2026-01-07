import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { apiKeyAPI } from '../api';

interface ApiKey {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

interface ApiKeyState {
  apiKeys: ApiKey[];
  loading: boolean;
  error: string | null;
  newlyCreatedKey: string | null;
}

const initialState: ApiKeyState = {
  apiKeys: [],
  loading: false,
  error: null,
  newlyCreatedKey: null,
};

export const fetchApiKeys = createAsyncThunk(
  'apiKeys/fetchApiKeys',
  async () => {
    const response = await apiKeyAPI.listApiKeys();
    return response.api_keys;
  }
);

export const createApiKey = createAsyncThunk(
  'apiKeys/createApiKey',
  async (name: string) => {
    return await apiKeyAPI.createApiKey(name);
  }
);

export const deleteApiKey = createAsyncThunk(
  'apiKeys/deleteApiKey',
  async (keyId: string) => {
    await apiKeyAPI.deleteApiKey(keyId);
    return keyId;
  }
);

const apiKeySlice = createSlice({
  name: 'apiKeys',
  initialState,
  reducers: {
    clearNewlyCreatedKey: (state) => {
      state.newlyCreatedKey = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchApiKeys.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchApiKeys.fulfilled, (state, action) => {
        state.loading = false;
        state.apiKeys = action.payload;
      })
      .addCase(fetchApiKeys.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch API keys';
      })
      .addCase(createApiKey.fulfilled, (state, action) => {
        state.newlyCreatedKey = action.payload.api_key;
        state.apiKeys.push({
          id: action.payload.api_key_id,
          name: action.payload.name,
          is_active: true,
          created_at: action.payload.created_at,
          last_used_at: null,
        });
      })
      .addCase(deleteApiKey.fulfilled, (state, action) => {
        state.apiKeys = state.apiKeys.filter(k => k.id !== action.payload);
      });
  },
});

export const { clearNewlyCreatedKey } = apiKeySlice.actions;
export default apiKeySlice.reducer;

