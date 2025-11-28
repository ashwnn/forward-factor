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

                    {user?.telegram_chat_id ? (
                        <div className="space-y-4">
                            {/* Connected Status */}
                            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-3">
                                        <div className="flex-shrink-0">
                                            <svg className="h-8 w-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-green-800">Bot Connected</p>
                                            {user.telegram_username && (
                                                <p className="text-sm text-green-600">@{user.telegram_username}</p>
                                            )}
                                        </div>
                                    </div>
                                    <button
                                        onClick={unlinkTelegram}
                                        className="px-4 py-2 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 transition-colors"
                                    >
                                        Disconnect
                                    </button>
                                </div>
                            </div>

                            {/* Bot Features */}
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <h3 className="text-sm font-semibold text-blue-900 mb-2">What you can do with the bot:</h3>
                                <ul className="text-sm text-blue-800 space-y-1">
                                    <li>• Receive real-time signal notifications</li>
                                    <li>• Manage your watchlist on-the-go</li>
                                    <li>• View your trade history</li>
                                    <li>• Track signal decisions</li>
                                </ul>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {/* Not Connected Status */}
                            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                                <div className="flex items-start space-x-3">
                                    <svg className="h-6 w-6 text-yellow-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                    </svg>
                                    <div>
                                        <p className="text-sm font-medium text-yellow-800">Bot Not Connected</p>
                                        <p className="text-sm text-yellow-700 mt-1">Link your Telegram account to receive signal notifications</p>
                                    </div>
                                </div>
                            </div>

                            {/* Instructions */}
                            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                                <h3 className="text-sm font-semibold text-gray-900 mb-3">How to connect:</h3>
                                <ol className="text-sm text-gray-700 space-y-2 list-decimal list-inside">
                                    <li>Copy your unique link code below</li>
                                    <li>Click "Open Telegram Bot" or search for <span className="font-mono bg-gray-100 px-1 rounded">@ForwardFactorBot</span> on Telegram</li>
                                    <li>Send the code to the bot or use the deep link</li>
                                    <li>Start receiving signals!</li>
                                </ol>
                            </div>

                            {/* Link Code Display */}
                            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg p-5">
                                <p className="text-sm font-medium text-gray-700 mb-2">Your Unique Link Code</p>
                                <div className="flex items-center gap-3">
                                    <code className="flex-1 text-3xl font-mono font-bold text-blue-700 bg-white px-4 py-3 rounded-lg border-2 border-blue-300 tracking-wider">
                                        {user?.link_code || 'Loading...'}
                                    </code>
                                    <button
                                        onClick={() => {
                                            navigator.clipboard.writeText(user?.link_code || '');
                                            setSuccess('Link code copied to clipboard!');
                                            setTimeout(() => setSuccess(''), 3000);
                                        }}
                                        className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
                                        title="Copy to clipboard"
                                    >
                                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                        </svg>
                                        <span className="hidden sm:inline">Copy</span>
                                    </button>
                                </div>
                                <p className="text-xs text-gray-600 mt-2">
                                    ⓘ This code is unique to your account and can only be used once
                                </p>
                            </div>

                            {/* Action Button */}
                            <div>
                                <a
                                    href={`https://t.me/ForwardFactorBot?start=${user?.link_code}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="w-full inline-flex justify-center items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg space-x-2"
                                >
                                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.461-1.901-.903-1.056-.693-1.653-1.124-2.678-1.8-1.185-.781-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.248-.024c-.106.024-1.793 1.14-5.061 3.345-.479.33-.913.491-1.302.481-.428-.008-1.252-.241-1.865-.44-.752-.244-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635.099-.002.321.023.465.14.121.099.155.232.171.326.016.094.036.308.02.475z" />
                                    </svg>
                                    <span>Open Telegram Bot</span>
                                </a>
                            </div>

                            <p className="text-xs text-center text-gray-500">
                                Don't have Telegram? <a href="https://telegram.org/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Download it here</a>
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
