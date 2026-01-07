/**
 * WebSocket Hook for Real-time Notifications
 * 
 * Provides real-time job status updates and analytics notifications
 * using Socket.IO client connected to the API Gateway.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

interface JobNotification {
    type: 'job_status_update';
    job_id: string;
    status: string;
    message: string;
    timestamp: string;
}

interface AnalyticsNotification {
    type: 'analytics_update';
    message: string;
    timestamp: string;
}

interface WebSocketState {
    isConnected: boolean;
    isAuthenticated: boolean;
    lastNotification: JobNotification | AnalyticsNotification | null;
    notifications: (JobNotification | AnalyticsNotification)[];
}

export function useWebSocket(token: string | null) {
    const socketRef = useRef<Socket | null>(null);
    const [state, setState] = useState<WebSocketState>({
        isConnected: false,
        isAuthenticated: false,
        lastNotification: null,
        notifications: [],
    });

    // Connect to WebSocket server
    const connect = useCallback(() => {
        if (!token || socketRef.current?.connected) return;

        const socket = io(API_URL, {
            transports: ['websocket', 'polling'],
            autoConnect: true,
        });

        socket.on('connect', () => {
            console.log('WebSocket connected');
            setState(prev => ({ ...prev, isConnected: true }));

            // Authenticate with JWT token
            socket.emit('authenticate', { token });
        });

        socket.on('authenticated', (data: { user_id: number; message: string }) => {
            console.log('WebSocket authenticated:', data);
            setState(prev => ({ ...prev, isAuthenticated: true }));

            // Subscribe to job updates
            socket.emit('subscribe_jobs', { user_id: data.user_id });
        });

        socket.on('auth_error', (error: { error: string }) => {
            console.error('WebSocket auth error:', error);
            setState(prev => ({ ...prev, isAuthenticated: false }));
        });

        socket.on('job_update', (notification: JobNotification) => {
            console.log('Job update received:', notification);
            setState(prev => ({
                ...prev,
                lastNotification: notification,
                notifications: [notification, ...prev.notifications].slice(0, 50),
            }));
        });

        socket.on('notification', (notification: JobNotification | AnalyticsNotification) => {
            console.log('Notification received:', notification);
            setState(prev => ({
                ...prev,
                lastNotification: notification,
                notifications: [notification, ...prev.notifications].slice(0, 50),
            }));
        });

        socket.on('analytics_update', (notification: AnalyticsNotification) => {
            console.log('Analytics update received:', notification);
            setState(prev => ({
                ...prev,
                lastNotification: notification,
                notifications: [notification, ...prev.notifications].slice(0, 50),
            }));
        });

        socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            setState(prev => ({
                ...prev,
                isConnected: false,
                isAuthenticated: false
            }));
        });

        socket.on('connect_error', (error: Error) => {
            console.error('WebSocket connection error:', error);
        });

        socketRef.current = socket;
    }, [token]);

    // Disconnect from WebSocket server
    const disconnect = useCallback(() => {
        if (socketRef.current) {
            socketRef.current.disconnect();
            socketRef.current = null;
            setState({
                isConnected: false,
                isAuthenticated: false,
                lastNotification: null,
                notifications: [],
            });
        }
    }, []);

    // Clear notifications
    const clearNotifications = useCallback(() => {
        setState(prev => ({ ...prev, notifications: [], lastNotification: null }));
    }, []);

    // Connect on mount if token exists
    useEffect(() => {
        if (token) {
            connect();
        }

        return () => {
            disconnect();
        };
    }, [token, connect, disconnect]);

    return {
        ...state,
        connect,
        disconnect,
        clearNotifications,
        socket: socketRef.current,
    };
}

export default useWebSocket;
