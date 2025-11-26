'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import { HistoryEntry } from '@/types';
import DashboardLayout from '../dashboard/layout';

export default function HistoryPage() {
    const [history, setHistory] = useState<HistoryEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        try {
            const response = await apiClient.get('/api/signals/history');
            setHistory(response.data);
        } catch (err: any) {
            setError('Failed to load history');
        } finally {
            setLoading(false);
        }
    };

    return (
        <DashboardLayout>
            <div className="px-4 py-6 sm:px-0">
                <h1 className="text-3xl font-bold text-gray-900 mb-6">Signal History</h1>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                        {error}
                    </div>
                )}

                {loading ? (
                    <p>Loading history...</p>
                ) : history.length === 0 ? (
                    <div className="bg-white shadow rounded-lg p-6">
                        <p className="text-gray-600">No signal history yet.</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {history.map((entry) => (
                            <div key={entry.signal.id} className="bg-white shadow rounded-lg p-6">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="text-xl font-bold text-gray-900">{entry.signal.ticker}</h3>
                                        <p className="text-sm text-gray-500">
                                            Signal: {new Date(entry.signal.as_of_ts).toLocaleString()}
                                        </p>
                                        {entry.decision && (
                                            <p className="text-sm text-gray-500">
                                                Decision: {new Date(entry.decision.decision_ts).toLocaleString()}
                                            </p>
                                        )}
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xl font-bold text-blue-600">
                                            FF: {(entry.signal.ff_value * 100).toFixed(2)}%
                                        </p>
                                        {entry.decision && (
                                            <span
                                                className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${entry.decision.decision === 'placed'
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-gray-100 text-gray-800'
                                                    }`}
                                            >
                                                {entry.decision.decision.toUpperCase()}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                    <div>
                                        <p className="text-sm text-gray-500">Front IV</p>
                                        <p className="font-semibold">{(entry.signal.front_iv * 100).toFixed(2)}%</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-500">Back IV</p>
                                        <p className="font-semibold">{(entry.signal.back_iv * 100).toFixed(2)}%</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-500">Front DTE</p>
                                        <p className="font-semibold">{entry.signal.front_dte}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-500">Back DTE</p>
                                        <p className="font-semibold">{entry.signal.back_dte}</p>
                                    </div>
                                </div>

                                {entry.decision?.pnl !== undefined && entry.decision.pnl !== null && (
                                    <div className="border-t pt-4 mt-4">
                                        <div className="flex justify-between items-center">
                                            <div>
                                                <p className="text-sm text-gray-500">Exit Price</p>
                                                <p className="font-semibold">${entry.decision.exit_price?.toFixed(2) || '-'}</p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm text-gray-500">PnL</p>
                                                <p className={`font-bold text-lg ${entry.decision.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                    {entry.decision.pnl >= 0 ? '+' : ''}{entry.decision.pnl.toFixed(2)}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
