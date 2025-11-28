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
                    <h2 className="text-xl font-semibold mb-4">Telegram Account</h2>
                    {user?.telegram_chat_id ? (
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">Status</p>
                                <p className="text-lg font-medium text-green-600 flex items-center">
                                    <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                                    Connected
                                    {user.telegram_username && <span className="text-gray-500 ml-2">(@{user.telegram_username})</span>}
                                </p>
                            </div>
                            <button
                                onClick={unlinkTelegram}
                                className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                            >
                                Unlink
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <p className="text-gray-600">
                                Link your Telegram account to receive real-time signals and manage your watchlist.
                            </p>

                            <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
                                <p className="text-sm text-gray-500 mb-2">Your Link Code</p>
                                <div className="flex items-center gap-2">
                                    <code className="text-2xl font-mono font-bold text-blue-700 bg-blue-50 px-3 py-1 rounded">
                                        {user?.link_code || 'Loading...'}
                                    </code>
                                    <button
                                        onClick={() => {
                                            navigator.clipboard.writeText(user?.link_code || '');
                                            setSuccess('Link code copied to clipboard!');
                                            setTimeout(() => setSuccess(''), 3000);
                                        }}
                                        className="text-sm text-blue-600 hover:text-blue-800 underline"
                                    >
                                        Copy
                                    </button>
                                </div>
                            </div>

                            <div className="flex flex-col sm:flex-row gap-3">
                                <a
                                    href={`https://t.me/ForwardFactorBot?start=${user?.link_code}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex justify-center items-center px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                                >
                                    Open in Telegram
                                </a>
                            </div>

                            <p className="text-xs text-gray-500 mt-2">
                                Click the button above or send the code manually to <a href="https://t.me/ForwardFactorBot" className="text-blue-600 hover:underline">@ForwardFactorBot</a>
                            </p>
                        </div>
                    )}
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
