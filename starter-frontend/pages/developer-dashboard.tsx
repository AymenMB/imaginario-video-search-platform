/**
 * Developer Dashboard Page
 * 
 * A comprehensive dashboard for API users to monitor:
 * - API usage statistics and analytics
 * - Search jobs tracking with real-time updates
 * - API key usage insights
 */

import { useEffect, useState, useCallback } from 'react';
import useWebSocket from '@/lib/hooks/useWebSocket';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@/lib/store';
import {
    fetchUsageStats,
    fetchDailyUsage,
    fetchEndpointUsage,
    fetchSearchJobs,
    fetchJobDetails,
    clearSelectedJob
} from '@/lib/slices/analyticsSlice';
import { fetchApiKeys } from '@/lib/slices/apiKeySlice';
import { logout } from '@/lib/slices/authSlice';
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';

// Colors for charts
const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function DeveloperDashboard() {
    const router = useRouter();
    const dispatch = useDispatch<AppDispatch>();

    const { isAuthenticated, user, isHydrated } = useSelector((state: RootState) => state.auth);
    const { summary, dailyUsage, endpointUsage, searchJobs, selectedJob, pagination, loading, jobsLoading } =
        useSelector((state: RootState) => state.analytics);
    const { apiKeys } = useSelector((state: RootState) => state.apiKeys);

    const [activeTab, setActiveTab] = useState<'overview' | 'jobs' | 'keys'>('overview');
    const [statusFilter, setStatusFilter] = useState<string>('');
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [showJobModal, setShowJobModal] = useState(false);

    // WebSocket for real-time notifications
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const { isConnected, isAuthenticated: wsAuthenticated, lastNotification, notifications, clearNotifications } = useWebSocket(token);
    const [showNotification, setShowNotification] = useState(false);

    // Initial data fetch
    useEffect(() => {
        // Wait for hydration before checking auth
        if (!isHydrated) return;

        if (!isAuthenticated) {
            router.push('/login');
            return;
        }

        dispatch(fetchUsageStats({}));
        dispatch(fetchDailyUsage({}));
        dispatch(fetchEndpointUsage());
        dispatch(fetchSearchJobs({ page: 1, perPage: 10 }));
        dispatch(fetchApiKeys());
    }, [dispatch, isAuthenticated, isHydrated, router]);

    // Auto refresh for jobs (polling fallback)
    useEffect(() => {
        if (!autoRefresh || activeTab !== 'jobs') return;

        const interval = setInterval(() => {
            dispatch(fetchSearchJobs({ status: statusFilter || undefined, page: currentPage, perPage: 10 }));
        }, 5000);

        return () => clearInterval(interval);
    }, [autoRefresh, activeTab, statusFilter, currentPage, dispatch]);

    // WebSocket real-time notification handling
    useEffect(() => {
        if (lastNotification) {
            // Show notification toast
            setShowNotification(true);

            // Auto-refresh data when job update received
            if (lastNotification.type === 'job_status_update') {
                dispatch(fetchSearchJobs({ status: statusFilter || undefined, page: currentPage, perPage: 10 }));
            }

            // Hide notification after 5 seconds
            const timeout = setTimeout(() => setShowNotification(false), 5000);
            return () => clearTimeout(timeout);
        }
    }, [lastNotification, dispatch, statusFilter, currentPage]);

    const handleRefresh = useCallback(() => {
        dispatch(fetchUsageStats({}));
        dispatch(fetchDailyUsage({}));
        dispatch(fetchEndpointUsage());
        dispatch(fetchSearchJobs({ status: statusFilter || undefined, page: currentPage, perPage: 10 }));
    }, [dispatch, statusFilter, currentPage]);

    const handleViewJobDetails = async (jobId: string) => {
        await dispatch(fetchJobDetails(jobId));
        setShowJobModal(true);
    };

    const handleFilterChange = (status: string) => {
        setStatusFilter(status);
        setCurrentPage(1);
        dispatch(fetchSearchJobs({ status: status || undefined, page: 1, perPage: 10 }));
    };

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        dispatch(fetchSearchJobs({ status: statusFilter || undefined, page, perPage: 10 }));
    };

    const handleRetryJob = async (jobId: string) => {
        try {
            const { searchJobsAPI } = await import('@/lib/api');
            await searchJobsAPI.retryJob(jobId);
            // Refresh jobs list
            dispatch(fetchSearchJobs({ status: statusFilter || undefined, page: currentPage, perPage: 10 }));
        } catch (error) {
            console.error('Failed to retry job:', error);
        }
    };

    const handleCancelJob = async (jobId: string) => {
        try {
            const { searchJobsAPI } = await import('@/lib/api');
            await searchJobsAPI.cancelJob(jobId);
            // Refresh jobs list
            dispatch(fetchSearchJobs({ status: statusFilter || undefined, page: currentPage, perPage: 10 }));
        } catch (error) {
            console.error('Failed to cancel job:', error);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-800';
            case 'processing': return 'bg-blue-100 text-blue-800';
            case 'queued': return 'bg-yellow-100 text-yellow-800';
            case 'failed': return 'bg-red-100 text-red-800';
            case 'cancelled': return 'bg-gray-100 text-gray-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleString();
    };

    const exportData = (format: 'csv' | 'json') => {
        const data = {
            summary,
            dailyUsage,
            endpointUsage,
            exportedAt: new Date().toISOString()
        };

        if (format === 'json') {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'api-usage-export.json';
            a.click();
        } else {
            // Simple CSV export
            const rows = [
                ['Date', 'Total', 'Successful', 'Errors', 'Avg Response Time'],
                ...dailyUsage.map((d: any) => [d.date, d.total, d.successful, d.errors, d.avg_response_time_ms])
            ];
            const csv = rows.map(r => r.join(',')).join('\n');
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'api-usage-export.csv';
            a.click();
        }
    };

    // Show loading while hydrating
    if (!isHydrated) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-gray-500">Loading...</div>
            </div>
        );
    }

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-gray-50">
            {/* WebSocket Real-time Notification Banner */}
            {showNotification && lastNotification && (
                <div className="fixed top-4 right-4 z-50 max-w-md bg-indigo-600 text-white px-6 py-3 rounded-lg shadow-lg animate-pulse">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <span className="text-lg">🔔</span>
                            <span className="font-medium">{lastNotification.message}</span>
                        </div>
                        <button
                            onClick={() => setShowNotification(false)}
                            className="ml-4 text-white hover:text-gray-200"
                        >
                            ✕
                        </button>
                    </div>
                </div>
            )}

            {/* Navigation - matches index.tsx */}
            <nav className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex items-center space-x-8">
                            <div className="flex items-center space-x-3">
                                <h1 className="text-xl font-bold text-indigo-600">
                                    Developer Dashboard
                                </h1>
                                {/* WebSocket Connection Status */}
                                <div className="flex items-center space-x-1">
                                    <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
                                    <span className="text-xs text-gray-500">
                                        {isConnected ? (wsAuthenticated ? 'Live' : 'Connecting...') : 'Offline'}
                                    </span>
                                </div>
                            </div>
                            <div className="hidden md:flex space-x-1">
                                <button
                                    onClick={() => setActiveTab('overview')}
                                    className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'overview'
                                        ? 'bg-indigo-600 text-white'
                                        : 'text-gray-600 hover:bg-gray-100'
                                        }`}
                                >
                                    Overview
                                </button>
                                <button
                                    onClick={() => setActiveTab('jobs')}
                                    className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'jobs'
                                        ? 'bg-indigo-600 text-white'
                                        : 'text-gray-600 hover:bg-gray-100'
                                        }`}
                                >
                                    Search Jobs
                                </button>
                                <button
                                    onClick={() => setActiveTab('keys')}
                                    className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'keys'
                                        ? 'bg-indigo-600 text-white'
                                        : 'text-gray-600 hover:bg-gray-100'
                                        }`}
                                >
                                    API Keys
                                </button>
                            </div>
                        </div>
                        <div className="flex items-center space-x-4">
                            <Link href="/" className="text-gray-600 hover:text-gray-900 transition">
                                Video Library
                            </Link>
                            <Link href="/api-keys" className="text-gray-600 hover:text-gray-900 transition">
                                Manage Keys
                            </Link>
                            <button
                                onClick={() => {
                                    dispatch(logout());
                                    router.push('/login');
                                }}
                                className="text-gray-600 hover:text-gray-900 transition"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                {/* Mobile Tabs */}
                <div className="md:hidden flex space-x-2 mb-6 overflow-x-auto pb-2">
                    <button
                        onClick={() => setActiveTab('overview')}
                        className={`px-4 py-2 rounded-lg whitespace-nowrap font-medium ${activeTab === 'overview' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border'
                            }`}
                    >
                        Overview
                    </button>
                    <button
                        onClick={() => setActiveTab('jobs')}
                        className={`px-4 py-2 rounded-lg whitespace-nowrap font-medium ${activeTab === 'jobs' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border'
                            }`}
                    >
                        Search Jobs
                    </button>
                    <button
                        onClick={() => setActiveTab('keys')}
                        className={`px-4 py-2 rounded-lg whitespace-nowrap font-medium ${activeTab === 'keys' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border'
                            }`}
                    >
                        API Keys
                    </button>
                </div>

                {/* Overview Tab */}
                {activeTab === 'overview' && (
                    <div className="space-y-6">
                        {/* Header with actions */}
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                            <div>
                                <h2 className="text-2xl font-bold text-gray-900">API Usage Analytics</h2>
                                <p className="text-gray-500">Last 30 days</p>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleRefresh}
                                    disabled={loading}
                                    className="px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg transition disabled:opacity-50 text-gray-700"
                                >
                                    {loading ? 'Refreshing...' : '🔄 Refresh'}
                                </button>
                                <button
                                    onClick={() => exportData('csv')}
                                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
                                >
                                    📊 Export CSV
                                </button>
                                <button
                                    onClick={() => exportData('json')}
                                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
                                >
                                    📋 Export JSON
                                </button>
                            </div>
                        </div>

                        {/* Stats Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-gray-500 text-sm">Total Requests</p>
                                        <p className="text-3xl font-bold text-gray-900 mt-1">{summary?.total_requests?.toLocaleString() ?? 0}</p>
                                    </div>
                                    <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                                        <span className="text-xl">📊</span>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-gray-500 text-sm">Success Rate</p>
                                        <p className="text-3xl font-bold text-green-600 mt-1">
                                            {summary ? (100 - summary.error_rate).toFixed(1) : 100}%
                                        </p>
                                    </div>
                                    <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                                        <span className="text-xl">✓</span>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-gray-500 text-sm">Avg Response Time</p>
                                        <p className="text-3xl font-bold text-yellow-600 mt-1">{summary?.avg_response_time_ms?.toFixed(0) ?? 0}ms</p>
                                    </div>
                                    <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                                        <span className="text-xl">⚡</span>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-gray-500 text-sm">P95 Response Time</p>
                                        <p className="text-3xl font-bold text-purple-600 mt-1">{summary?.p95_response_time_ms ?? 0}ms</p>
                                    </div>
                                    <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                                        <span className="text-xl">📈</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Charts Row */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Daily Usage Chart */}
                            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Requests</h3>
                                <div className="h-64">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={dailyUsage}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                            <XAxis
                                                dataKey="date"
                                                stroke="#6b7280"
                                                tick={{ fill: '#6b7280', fontSize: 12 }}
                                                tickFormatter={(value) => value.slice(5)}
                                            />
                                            <YAxis stroke="#6b7280" tick={{ fill: '#6b7280' }} />
                                            <Tooltip
                                                contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                                                labelStyle={{ color: '#111827' }}
                                            />
                                            <Legend />
                                            <Line
                                                type="monotone"
                                                dataKey="total"
                                                stroke="#6366f1"
                                                strokeWidth={2}
                                                dot={false}
                                                name="Total"
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="successful"
                                                stroke="#22c55e"
                                                strokeWidth={2}
                                                dot={false}
                                                name="Successful"
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="errors"
                                                stroke="#ef4444"
                                                strokeWidth={2}
                                                dot={false}
                                                name="Errors"
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Response Time Chart */}
                            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Response Time (ms)</h3>
                                <div className="h-64">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={dailyUsage}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                            <XAxis
                                                dataKey="date"
                                                stroke="#6b7280"
                                                tick={{ fill: '#6b7280', fontSize: 12 }}
                                                tickFormatter={(value) => value.slice(5)}
                                            />
                                            <YAxis stroke="#6b7280" tick={{ fill: '#6b7280' }} />
                                            <Tooltip
                                                contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                                                labelStyle={{ color: '#111827' }}
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="avg_response_time_ms"
                                                stroke="#f59e0b"
                                                strokeWidth={2}
                                                dot={false}
                                                name="Avg Response Time"
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </div>

                        {/* Endpoint Usage */}
                        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">Requests by Endpoint</h3>
                            <div className="h-80">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={endpointUsage.slice(0, 10)} layout="vertical">
                                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                        <XAxis type="number" stroke="#6b7280" tick={{ fill: '#6b7280' }} />
                                        <YAxis
                                            type="category"
                                            dataKey="endpoint"
                                            stroke="#6b7280"
                                            tick={{ fill: '#6b7280', fontSize: 10 }}
                                            width={150}
                                        />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                                            labelStyle={{ color: '#111827' }}
                                        />
                                        <Legend />
                                        <Bar dataKey="successful" fill="#22c55e" name="Successful" stackId="a" />
                                        <Bar dataKey="errors" fill="#ef4444" name="Errors" stackId="a" />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                )}

                {/* Search Jobs Tab */}
                {activeTab === 'jobs' && (
                    <div className="space-y-6">
                        {/* Header */}
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                            <div>
                                <h2 className="text-2xl font-bold text-gray-900">Search Jobs</h2>
                                <p className="text-gray-500">Track your search operations in real-time</p>
                            </div>
                            <div className="flex items-center gap-4">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={autoRefresh}
                                        onChange={(e) => setAutoRefresh(e.target.checked)}
                                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                    />
                                    <span className="text-sm text-gray-600">Auto-refresh (5s)</span>
                                </label>
                                <button
                                    onClick={handleRefresh}
                                    disabled={jobsLoading}
                                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition disabled:opacity-50"
                                >
                                    {jobsLoading ? 'Loading...' : '🔄 Refresh'}
                                </button>
                            </div>
                        </div>

                        {/* Filters */}
                        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex flex-wrap gap-4">
                            <div>
                                <label className="block text-sm text-gray-500 mb-1">Status Filter</label>
                                <select
                                    value={statusFilter}
                                    onChange={(e) => handleFilterChange(e.target.value)}
                                    className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-700 focus:ring-indigo-500 focus:border-indigo-500"
                                >
                                    <option value="">All Statuses</option>
                                    <option value="queued">Queued</option>
                                    <option value="processing">Processing</option>
                                    <option value="completed">Completed</option>
                                    <option value="failed">Failed</option>
                                    <option value="cancelled">Cancelled</option>
                                </select>
                            </div>
                        </div>

                        {/* Jobs Table */}
                        <div className="bg-white rounded-xl overflow-hidden shadow-sm border border-gray-100">
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-gray-50 border-b border-gray-200">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Job ID</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Query</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Results</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time (ms)</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200">
                                        {searchJobs.length === 0 ? (
                                            <tr>
                                                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                                                    No search jobs found. Start a search from the Video Library.
                                                </td>
                                            </tr>
                                        ) : (
                                            searchJobs.map((job) => (
                                                <tr key={job.job_id} className="hover:bg-gray-50 transition">
                                                    <td className="px-6 py-4">
                                                        <code className="text-xs text-indigo-600 bg-indigo-50 px-2 py-1 rounded">{job.job_id.slice(0, 8)}...</code>
                                                    </td>
                                                    <td className="px-6 py-4 max-w-xs truncate text-gray-900">{job.query}</td>
                                                    <td className="px-6 py-4">
                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                                                            {job.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-gray-900">{job.results_count}</td>
                                                    <td className="px-6 py-4 text-gray-900">{job.execution_time_ms ?? '-'}</td>
                                                    <td className="px-6 py-4 text-sm text-gray-500">
                                                        {formatDate(job.created_at)}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="flex items-center gap-2">
                                                            <button
                                                                onClick={() => handleViewJobDetails(job.job_id)}
                                                                className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                                                            >
                                                                Details
                                                            </button>
                                                            {(job.status === 'completed' || job.status === 'failed') && (
                                                                <button
                                                                    onClick={() => handleRetryJob(job.job_id)}
                                                                    className="text-green-600 hover:text-green-800 text-sm font-medium"
                                                                    title="Retry this job"
                                                                >
                                                                    🔄 Retry
                                                                </button>
                                                            )}
                                                            {(job.status === 'queued' || job.status === 'processing') && (
                                                                <button
                                                                    onClick={() => handleCancelJob(job.job_id)}
                                                                    className="text-red-600 hover:text-red-800 text-sm font-medium"
                                                                    title="Cancel this job"
                                                                >
                                                                    ❌ Cancel
                                                                </button>
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination */}
                            {pagination && pagination.total_pages > 1 && (
                                <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between items-center">
                                    <p className="text-sm text-gray-500">
                                        Page {pagination.page} of {pagination.total_pages} ({pagination.total_items} total)
                                    </p>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handlePageChange(pagination.page - 1)}
                                            disabled={!pagination.has_prev}
                                            className="px-3 py-1 bg-white border border-gray-300 rounded disabled:opacity-50 text-gray-700"
                                        >
                                            Previous
                                        </button>
                                        <button
                                            onClick={() => handlePageChange(pagination.page + 1)}
                                            disabled={!pagination.has_next}
                                            className="px-3 py-1 bg-white border border-gray-300 rounded disabled:opacity-50 text-gray-700"
                                        >
                                            Next
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* API Keys Tab */}
                {activeTab === 'keys' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center">
                            <div>
                                <h2 className="text-2xl font-bold text-gray-900">API Key Usage</h2>
                                <p className="text-gray-500">Monitor usage across your API keys</p>
                            </div>
                            <Link
                                href="/api-keys"
                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition"
                            >
                                Manage API Keys
                            </Link>
                        </div>

                        {/* API Keys Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {apiKeys.length === 0 ? (
                                <div className="col-span-full bg-white rounded-xl p-8 text-center shadow-sm border border-gray-100">
                                    <p className="text-gray-500 mb-4">No API keys found.</p>
                                    <Link
                                        href="/api-keys"
                                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition inline-block"
                                    >
                                        Create API Key
                                    </Link>
                                </div>
                            ) : (
                                apiKeys.map((key) => (
                                    <div key={key.id} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <h3 className="font-semibold text-lg text-gray-900">{key.name}</h3>
                                                <p className="text-xs text-gray-500 mt-1">
                                                    Created: {new Date(key.created_at).toLocaleDateString()}
                                                </p>
                                            </div>
                                            <span className={`px-2 py-1 rounded-full text-xs ${key.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
                                                }`}>
                                                {key.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </div>
                                        <div className="space-y-2 text-sm">
                                            <div className="flex justify-between">
                                                <span className="text-gray-500">Last Used:</span>
                                                <span className="text-gray-900">{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}
            </main>

            {/* Job Details Modal */}
            {showJobModal && selectedJob && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl">
                        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
                            <h3 className="text-xl font-bold text-gray-900">Job Details</h3>
                            <button
                                onClick={() => {
                                    setShowJobModal(false);
                                    dispatch(clearSelectedJob());
                                }}
                                className="text-gray-400 hover:text-gray-600 text-2xl"
                            >
                                ×
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto max-h-[60vh] space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm text-gray-500">Job ID</p>
                                    <code className="text-indigo-600 bg-indigo-50 px-2 py-1 rounded text-sm">{selectedJob.job_id}</code>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-500">Status</p>
                                    <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(selectedJob.status)}`}>
                                        {selectedJob.status}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-500">Algorithm</p>
                                    <p className="text-gray-900">{selectedJob.algorithm}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-500">Execution Time</p>
                                    <p className="text-gray-900">{selectedJob.execution_time_ms}ms</p>
                                </div>
                            </div>

                            <div>
                                <p className="text-sm text-gray-500">Query</p>
                                <p className="bg-gray-50 rounded p-3 mt-1 text-gray-900 border">{selectedJob.query}</p>
                            </div>

                            <div>
                                <p className="text-sm text-gray-500 mb-2">Results ({selectedJob.results_count})</p>
                                <div className="bg-gray-50 rounded p-4 max-h-60 overflow-y-auto border">
                                    {selectedJob.results && selectedJob.results.length > 0 ? (
                                        <div className="space-y-3">
                                            {selectedJob.results.map((result: any, idx: number) => (
                                                <div key={idx} className="border-b border-gray-200 pb-3 last:border-0 last:pb-0">
                                                    <p className="font-medium text-gray-900">{result.title}</p>
                                                    <p className="text-sm text-gray-500">{result.matched_text}</p>
                                                    <p className="text-xs text-indigo-600 mt-1">
                                                        Relevance: {(result.relevance_score * 100).toFixed(0)}%
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-gray-500">No results</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
