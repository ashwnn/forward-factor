'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import { Settings } from '@/types';
import DashboardLayout from '../dashboard/layout';

export default function SettingsPage() {
    const [settings, setSettings] = useState<Settings | null>(null);
    const [telegramUsername, setTelegramUsername] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        fetchSettings();
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

    const linkTelegram = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        try {
            await apiClient.post('/api/auth/link-telegram', {
                telegram_username: telegramUsername,
            });
            setSuccess('Telegram account linked successfully!');
            setTelegramUsername('');
        } catch (err: any) {
            setError('Failed to link Telegram account');
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

                {/* Link Telegram */}
                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Link Telegram Account</h2>
                    <form onSubmit={linkTelegram} className="flex gap-4">
                        <input
                            type="text"
                            value={telegramUsername}
                            onChange={(e) => setTelegramUsername(e.target.value)}
                            placeholder="Enter Telegram username (without @)"
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button
                            type="submit"
                            className="px-6 py-2 bg-blue-700 text-white rounded-md hover:bg-blue-800"
                        >
                            Link
                        </button>
                    </form>
                </div>

                {/* Signal Settings */}
                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Signal Settings</h2>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Forward Factor Threshold
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                value={settings.ff_threshold}
                                onChange={(e) =>
                                    setSettings({ ...settings, ff_threshold: parseFloat(e.target.value) })
                                }
                                className="w-full px-4 py-2 border border-gray-300 rounded-md"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Vol Point
                            </label>
                            <select
                                value={settings.vol_point}
                                onChange={(e) => setSettings({ ...settings, vol_point: e.target.value })}
                                className="w-full px-4 py-2 border border-gray-300 rounded-md"
                            >
                                <option value="ATM">ATM</option>
                                <option value="35d_put">35 Delta Put</option>
                                <option value="35d_call">35 Delta Call</option>
                            </select>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Min Open Interest
                                </label>
                                <input
                                    type="number"
                                    value={settings.min_open_interest}
                                    onChange={(e) =>
                                        setSettings({ ...settings, min_open_interest: parseInt(e.target.value) })
                                    }
                                    className="w-full px-4 py-2 border border-gray-300 rounded-md"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Min Volume
                                </label>
                                <input
                                    type="number"
                                    value={settings.min_volume}
                                    onChange={(e) =>
                                        setSettings({ ...settings, min_volume: parseInt(e.target.value) })
                                    }
                                    className="w-full px-4 py-2 border border-gray-300 rounded-md"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Cooldown Minutes
                            </label>
                            <input
                                type="number"
                                value={settings.cooldown_minutes}
                                onChange={(e) =>
                                    setSettings({ ...settings, cooldown_minutes: parseInt(e.target.value) })
                                }
                                className="w-full px-4 py-2 border border-gray-300 rounded-md"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Timezone
                            </label>
                            <input
                                type="text"
                                value={settings.timezone}
                                onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                                className="w-full px-4 py-2 border border-gray-300 rounded-md"
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
