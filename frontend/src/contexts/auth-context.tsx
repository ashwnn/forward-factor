'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import { User, LoginResponse } from '@/types';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check if user is logged in on mount
        const token = localStorage.getItem('access_token');
        const savedUser = localStorage.getItem('user');

        if (token && savedUser) {
            setUser(JSON.parse(savedUser));
            // Optionally verify token is still valid
            verifyToken();
        }
        setLoading(false);
    }, []);

    const verifyToken = async () => {
        try {
            const response = await apiClient.get('/api/auth/me');
            setUser(response.data);
            localStorage.setItem('user', JSON.stringify(response.data));
        } catch (error) {
            // Token is invalid, clear everything
            logout();
        }
    };

    const login = async (email: string, password: string) => {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);

        const response = await apiClient.post<LoginResponse>('/api/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });

        const { access_token, user: userData } = response.data;

        localStorage.setItem('access_token', access_token);
        localStorage.setItem('user', JSON.stringify(userData));
        setUser(userData);
    };

    const register = async (email: string, password: string) => {
        const response = await apiClient.post<LoginResponse>('/api/auth/register', {
            email,
            password,
        });

        const { access_token, user: userData } = response.data;

        localStorage.setItem('access_token', access_token);
        localStorage.setItem('user', JSON.stringify(userData));
        setUser(userData);
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
