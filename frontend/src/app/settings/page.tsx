'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import { Settings } from '@/types';
import DashboardLayout from '../dashboard/layout';

export default function SettingsPage() {
    const [settings, setSettings] = useState<Settings | null>(null);
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        fetchSettings();
        fetchUser();
    }, []);

    const fetchSettings = async () => {
        try {
            const response = await apiClient.get('/api/settings');
            setSettings(response.data);
        } catch (err: any) {
            setError('Failed to load settings');
        } finally {
            setLoading(false);
        }
    };

    const fetchUser = async () => {
        try {
            const response = await apiClient.get('/api/auth/me');
            setUser(response.data);
        } catch (err: any) {
            console.error('Failed to fetch user info:', err);
        }
    };

    const saveSettings = async () => {
        if (!settings) return;

        setSaving(true);
        setError('');
        setSuccess('');

        try {
            await apiClient.put('/api/settings', settings);
            setSuccess('Settings saved successfully!');
        } catch (err: any) {
            setError('Failed to save settings');
        } finally {
            setSaving(false);
        }
    };

    const unlinkTelegram = async () => {
        setError('');
        setSuccess('');

        try {
            await apiClient.post('/api/auth/unlink-telegram');
            setSuccess('Telegram account unlinked successfully!');
            await fetchUser(); // Refresh user data
        } catch (err: any) {
            setError('Failed to unlink Telegram account');
        }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="px-4 py-6 sm:px-0">
                    <p>Loading settings...</p>
                </div>
            </DashboardLayout>
        );
    }

    if (!settings) {
        return (
            <DashboardLayout>
                <div className="px-4 py-6 sm:px-0">
                    <p className="text-red-600">Failed to load settings</p>
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="px-4 py-6 sm:px-0">
                <h1 className="text-3xl font-bold text-gray-900 mb-6">Settings</h1>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                        {error}
                    </div>
                )}
                {success && (
                    <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
                        {success}
                    </div>
                )}

                {/* Telegram Account Section */}
                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Telegram Bot Connection</h2>

                    {/* Link Key - Always Shown */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Your Link Key
                        </label>
                        <div className="flex items-center gap-2">
                            <input
                                type="password"
                                value={user?.link_code || ''}
                                readOnly
                                className="flex-1 px-4 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm"
                                placeholder="••••••••••••••••"
                            />
                            <button
                                onClick={() => {
                                    navigator.clipboard.writeText(user?.link_code || '');
                                    setSuccess('Link key copied to clipboard!');
                                    setTimeout(() => setSuccess(''), 2000);
                                }}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center gap-2"
                                title="Copy link key"
                            >
                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                                Copy
                            </button>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                            Use this key with <code className="bg-gray-100 px-1 rounded">/start &lt;key&gt;</code> in Telegram to link chats
                        </p>
                    </div>

                    {/* Connected Chats */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Connected Chats {user?.telegram_chats?.length > 0 && `(${user.telegram_chats.length})`}
                        </label>

                        {user?.telegram_chats && user.telegram_chats.length > 0 ? (
                            <div className="border border-gray-300 rounded-md divide-y divide-gray-200">
                                {user.telegram_chats.map((chat: any, index: number) => {
                                    // Build display name: "FirstName LastName" or "@username" or "Chat ID"
                                    const displayName = chat.first_name
                                        ? `${chat.first_name}${chat.last_name ? ' ' + chat.last_name : ''}`
                                        : chat.username
                                            ? `@${chat.username}`
                                            : `Chat ${chat.chat_id.slice(-8)}`;

                                    return (
                                        <div key={chat.chat_id} className="px-4 py-3 hover:bg-gray-50 transition-colors">
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <svg className="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                        </svg>
                                                        <div>
                                                            <p className="text-sm font-medium text-gray-900">
                                                                {displayName}
                                                            </p>
                                                            {chat.username && chat.first_name && (
                                                                <p className="text-xs text-gray-500">
                                                                    @{chat.username}
                                                                </p>
                                                            )}
                                                            <p className="text-xs text-gray-500">
                                                                Linked on {new Date(chat.linked_at).toLocaleDateString()} at {new Date(chat.linked_at).toLocaleTimeString()}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                                <span className="text-xs text-gray-400 font-mono">ID: {chat.chat_id.slice(-8)}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="border border-gray-200 rounded-md px-4 py-8 text-center">
                                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                </svg>
                                <p className="mt-2 text-sm text-gray-500">No chats connected yet</p>
                                <p className="mt-1 text-xs text-gray-400">
                                    Copy your link key above and use <code className="bg-gray-100 px-1 rounded">/start &lt;key&gt;</code> in Telegram
                                </p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Discovery Mode Section */}
                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Discovery Mode</h2>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-600 mb-1">
                                Enable market-wide scanning to discover signals from the top 100 most liquid optionable stocks.
                            </p>
                            <p className="text-xs text-gray-500">
                                When enabled, you&apos;ll receive signals from stocks you haven&apos;t explicitly subscribed to.
                            </p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={settings.discovery_mode}
                                onChange={(e) =>
                                    setSettings({ ...settings, discovery_mode: e.target.checked })
                                }
                                className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                    </div>
                </div>

                {/* Signal Settings */}
                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Signal Settings</h2>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-900 mb-1">
                                Forward Factor Threshold
                            </label>
                            <p className="text-xs text-gray-600 mb-2">
                                Minimum FF value to trigger a signal. Use 1.5 for conservative signals, 1.0 for more aggressive signals. Example: 1.2
                            </p>
                            <input
                                type="number"
                                step="0.01"
                                value={settings.ff_threshold}
                                onChange={(e) =>
                                    setSettings({ ...settings, ff_threshold: parseFloat(e.target.value) })
                                }
                                className="w-full px-4 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-900 mb-1">
                                Vol Point
                            </label>
                            <p className="text-xs text-gray-600 mb-2">
                                Which strike to use for volatility calculations. ATM = At-The-Money, 35d = 35 Delta options. Example: ATM
                            </p>
                            <select
                                value={settings.vol_point}
                                onChange={(e) => setSettings({ ...settings, vol_point: e.target.value })}
                                className="w-full px-4 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="ATM">ATM</option>
                                <option value="35d_put">35 Delta Put</option>
                                <option value="35d_call">35 Delta Call</option>
                            </select>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-900 mb-1">
                                    Min Open Interest
                                </label>
                                <p className="text-xs text-gray-600 mb-2">
                                    Minimum open interest required for options to ensure liquidity. Example: 100
                                </p>
                                <input
                                    type="number"
                                    value={settings.min_open_interest}
                                    onChange={(e) =>
                                        setSettings({ ...settings, min_open_interest: parseInt(e.target.value) })
                                    }
                                    className="w-full px-4 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-900 mb-1">
                                    Min Volume
                                </label>
                                <p className="text-xs text-gray-600 mb-2">
                                    Minimum daily options volume required to ensure active trading. Example: 50
                                </p>
                                <input
                                    type="number"
                                    value={settings.min_volume}
                                    onChange={(e) =>
                                        setSettings({ ...settings, min_volume: parseInt(e.target.value) })
                                    }
                                    className="w-full px-4 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-900 mb-1">
                                Cooldown Minutes
                            </label>
                            <p className="text-xs text-gray-600 mb-2">
                                Minimum time (in minutes) between signals for the same ticker to avoid spam. Example: 60 (1 hour)
                            </p>
                            <input
                                type="number"
                                value={settings.cooldown_minutes}
                                onChange={(e) =>
                                    setSettings({ ...settings, cooldown_minutes: parseInt(e.target.value) })
                                }
                                className="w-full px-4 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-900 mb-1">
                                Timezone
                            </label>
                            <p className="text-xs text-gray-600 mb-2">
                                Your timezone for quiet hours and scheduling. Use IANA format. Example: America/New_York, Europe/London, Asia/Tokyo
                            </p>
                            <input
                                type="text"
                                value={settings.timezone}
                                onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                                className="w-full px-4 py-2 border border-gray-300 rounded-md text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="America/New_York"
                            />
                        </div>
                    </div>

                    <button
                        onClick={saveSettings}
                        disabled={saving}
                        className="mt-6 w-full bg-blue-700 text-white px-4 py-2 rounded-md hover:bg-blue-800 disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Settings'}
                    </button>
                </div>
            </div>
        </DashboardLayout>
    );
}
