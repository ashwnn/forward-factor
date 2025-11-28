'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import { Signal } from '@/types';
import DashboardLayout from '../dashboard/layout';

export default function SignalsPage() {
    const [signals, setSignals] = useState<Signal[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchSignals();
    }, []);

    const fetchSignals = async () => {
        try {
            const response = await apiClient.get('/api/signals');
            setSignals(response.data);
        } catch (err: any) {
            setError('Failed to load signals');
        } finally {
            setLoading(false);
        }
    };

    const recordDecision = async (signalId: string, decision: 'placed' | 'ignored') => {
        try {
            await apiClient.post(`/api/signals/${signalId}/decision`, { decision });
            alert(`Decision recorded: ${decision}`);
        } catch (err: any) {
            alert('Failed to record decision');
        }
    };

    return (
        <DashboardLayout>
            <div className="px-2 sm:px-4 py-4 sm:py-6">
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4 sm:mb-6">Recent Signals</h1>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-3 sm:px-4 py-2 sm:py-3 rounded mb-3 sm:mb-4 text-sm">
                        {error}
                    </div>
                )}

                {loading ? (
                    <p className="text-sm">Loading signals...</p>
                ) : signals.length === 0 ? (
                    <div className="bg-white shadow rounded-lg p-4 sm:p-6">
                        <p className="text-sm sm:text-base text-gray-600">No signals found for your watchlist.</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {signals.map((signal) => (
                            <div key={signal.id} className="bg-white shadow rounded-lg p-6">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="text-2xl font-bold text-gray-900">{signal.ticker}</h3>
                                        <p className="text-sm text-gray-500">
                                            {new Date(signal.as_of_ts).toLocaleString()}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-2xl font-bold text-blue-600">
                                            FF: {(signal.ff_value * 100).toFixed(2)}%
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            Quality: {signal.quality_score.toFixed(2)}
                                        </p>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                    <div>
                                        <p className="text-sm text-gray-500">Front IV</p>
                                        <p className="font-semibold">{(signal.front_iv * 100).toFixed(2)}%</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-500">Back IV</p>
                                        <p className="font-semibold">{(signal.back_iv * 100).toFixed(2)}%</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-500">Forward IV</p>
                                        <p className="font-semibold">{(signal.sigma_fwd * 100).toFixed(2)}%</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-500">Vol Point</p>
                                        <p className="font-semibold">{signal.vol_point}</p>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <p className="text-sm text-gray-500">Front Expiry</p>
                                        <p className="font-semibold">
                                            {new Date(signal.front_expiry).toLocaleDateString()} ({signal.front_dte} DTE)
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-500">Back Expiry</p>
                                        <p className="font-semibold">
                                            {new Date(signal.back_expiry).toLocaleDateString()} ({signal.back_dte} DTE)
                                        </p>
                                    </div>
                                </div>

                                <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
                                    <button
                                        onClick={() => recordDecision(signal.id, 'placed')}
                                        className="flex-1 bg-green-700 text-white px-4 py-2.5 sm:py-2 rounded-md hover:bg-green-800 font-medium min-h-[44px] transition-colors"
                                    >
                                        Place Trade
                                    </button>
                                    <button
                                        onClick={() => recordDecision(signal.id, 'ignored')}
                                        className="flex-1 bg-gray-700 text-white px-4 py-2.5 sm:py-2 rounded-md hover:bg-gray-800 font-medium min-h-[44px] transition-colors"
                                    >
                                        Ignore
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
