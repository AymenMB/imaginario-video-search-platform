import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@/lib/store';
import { fetchVideos, createVideo, updateVideo, deleteVideo } from '@/lib/slices/videoSlice';
import { submitSearch, getSearchResults, clearResults } from '@/lib/slices/searchSlice';
import { logout } from '@/lib/slices/authSlice';

export default function Home() {
  const router = useRouter();
  const dispatch = useDispatch<AppDispatch>();
  const { user, isAuthenticated, isHydrated } = useSelector((state: RootState) => state.auth);
  const { videos, loading: videosLoading } = useSelector((state: RootState) => state.videos);
  const { results: searchResults, loading: searchLoading } = useSelector((state: RootState) => state.search);

  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingVideo, setEditingVideo] = useState<any>(null);
  const [newVideo, setNewVideo] = useState({ title: '', description: '', duration: 0 });

  useEffect(() => {
    // Wait for hydration before checking auth
    if (!isHydrated) return;

    if (!isAuthenticated || !user) {
      router.push('/login');
      return;
    }
    dispatch(fetchVideos(user.id));
  }, [dispatch, isAuthenticated, isHydrated, user, router]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !user) return;

    dispatch(clearResults());
    const result = await dispatch(submitSearch({ userId: user.id, query: searchQuery }));

    if (submitSearch.fulfilled.match(result)) {
      const jobId = result.payload.job_id;
      if (jobId) {
        // Poll for results
        const pollResults = async () => {
          const results = await dispatch(getSearchResults({ userId: user.id, jobId }));
          if (getSearchResults.fulfilled.match(results) && results.payload.status === 'completed') {
            return;
          }
          setTimeout(pollResults, 500);
        };
        pollResults();
      }
    }
  };

  const handleCreateVideo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    await dispatch(createVideo({ userId: user.id, data: newVideo }));
    setShowCreateModal(false);
    setNewVideo({ title: '', description: '', duration: 0 });
    dispatch(fetchVideos(user.id));
  };

  const handleEditVideo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !editingVideo) return;

    await dispatch(updateVideo({ userId: user.id, videoId: editingVideo.id, data: editingVideo }));
    setEditingVideo(null);
    dispatch(fetchVideos(user.id));
  };

  const handleDeleteVideo = async (videoId: number) => {
    if (!user || !confirm('Are you sure you want to delete this video?')) return;
    await dispatch(deleteVideo({ userId: user.id, videoId }));
    dispatch(fetchVideos(user.id));
  };

  // Show nothing while hydrating or if not authenticated
  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold">Video Search Platform</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/developer-dashboard" className="text-gray-700 hover:text-gray-900">
                Developer Dashboard
              </Link>
              <Link href="/api-keys" className="text-gray-700 hover:text-gray-900">
                API Keys
              </Link>
              <button
                onClick={() => {
                  dispatch(logout());
                  router.push('/login');
                }}
                className="text-gray-700 hover:text-gray-900"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Search Section */}
          <div className="mb-6 bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl font-bold mb-4">Search Videos</h2>
            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search videos..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={searchLoading}
                className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {searchLoading ? 'Searching...' : 'Search'}
              </button>
            </form>

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div className="mt-4">
                <h3 className="text-lg font-semibold mb-2">Search Results</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {searchResults.map((result) => (
                    <div key={result.video_id} className="border rounded-lg p-4">
                      <h4 className="font-semibold">{result.title}</h4>
                      <p className="text-sm text-gray-600 mt-1">{result.matched_text}</p>
                      <p className="text-xs text-indigo-600 mt-2">
                        Relevance: {(result.relevance_score * 100).toFixed(0)}%
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Video Library */}
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">My Videos</h2>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Create Video
              </button>
            </div>

            {videosLoading ? (
              <p className="text-gray-500">Loading videos...</p>
            ) : videos.length === 0 ? (
              <p className="text-gray-500">No videos yet. Create your first video!</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {videos.map((video) => (
                  <div key={video.id} className="border rounded-lg p-4 hover:shadow-lg transition">
                    <h3 className="font-semibold text-lg">{video.title}</h3>
                    <p className="text-sm text-gray-600 mt-2 line-clamp-2">{video.description || 'No description'}</p>
                    <p className="text-xs text-gray-500 mt-2">Duration: {video.duration}s</p>
                    <div className="flex gap-2 mt-4">
                      <button
                        onClick={() => setEditingVideo(video)}
                        className="flex-1 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteVideo(video.id)}
                        className="flex-1 px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Create Video Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-xl font-bold mb-4">Create Video</h3>
            <form onSubmit={handleCreateVideo}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Title *</label>
                <input
                  type="text"
                  required
                  value={newVideo.title}
                  onChange={(e) => setNewVideo({ ...newVideo, title: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={newVideo.description}
                  onChange={(e) => setNewVideo({ ...newVideo, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  rows={3}
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Duration (seconds)</label>
                <input
                  type="number"
                  value={newVideo.duration}
                  onChange={(e) => setNewVideo({ ...newVideo, duration: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Video Modal */}
      {editingVideo && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-xl font-bold mb-4">Edit Video</h3>
            <form onSubmit={handleEditVideo}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Title *</label>
                <input
                  type="text"
                  required
                  value={editingVideo.title}
                  onChange={(e) => setEditingVideo({ ...editingVideo, title: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={editingVideo.description || ''}
                  onChange={(e) => setEditingVideo({ ...editingVideo, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  rows={3}
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Duration (seconds)</label>
                <input
                  type="number"
                  value={editingVideo.duration}
                  onChange={(e) => setEditingVideo({ ...editingVideo, duration: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setEditingVideo(null)}
                  className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
