'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import { HistoryEntry } from '@/types';
import DashboardLayout from '../dashboard/layout';
import TradeDetailsDialog, { TradeDetails } from '@/components/TradeDetailsDialog';

export default function HistoryPage() {
    const [history, setHistory] = useState<HistoryEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [editingEntry, setEditingEntry] = useState<HistoryEntry | null>(null);

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

    const handleSaveTradeDetails = async (tradeDetails: TradeDetails) => {
        if (!editingEntry?.decision) return;

        await apiClient.post(`/api/signals/${editingEntry.signal.id}/decision`, {
            decision: editingEntry.decision.decision,
            ...tradeDetails,
        });

        // Refresh history
        await fetchHistory();
    };

    return (
        <DashboardLayout>
            <div className="px-2 sm:px-4 py-4 sm:py-6">
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4 sm:mb-6">Signal History</h1>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-3 sm:px-4 py-2 sm:py-3 rounded mb-3 sm:mb-4 text-sm">
                        {error}
                    </div>
                )}

                {loading ? (
                    <p className="text-sm">Loading history...</p>
                ) : history.length === 0 ? (
                    <div className="bg-white shadow rounded-lg p-4 sm:p-6">
                        <p className="text-sm sm:text-base text-gray-600">No signal history yet.</p>
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
                                    <div className="flex items-center gap-2">
                                        <p className="text-xl font-bold text-blue-600">
                                            FF: {(entry.signal.ff_value * 100).toFixed(2)}%
                                        </p>
                                        {entry.decision && (
                                            <div className="flex flex-col items-end gap-2">
                                                <span
                                                    className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${entry.decision.decision === 'placed'
                                                        ? 'bg-green-100 text-green-800'
                                                        : 'bg-gray-100 text-gray-800'
                                                        }`}
                                                >
                                                    {entry.decision.decision.toUpperCase()}
                                                </span>
                                                {entry.decision.decision === 'placed' && (
                                                    <button
                                                        onClick={() => setEditingEntry(entry)}
                                                        className="text-sm text-blue-600 hover:text-blue-800 underline"
                                                    >
                                                        Edit Trade
                                                    </button>
                                                )}
                                            </div>
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

                                {(entry.decision?.pnl !== undefined && entry.decision.pnl !== null) || entry.decision?.entry_price || entry.decision?.exit_price ? (
                                    <div className="border-t pt-4 mt-4">
                                        <h4 className="text-sm font-semibold text-gray-700 mb-3">Trade Details</h4>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                                            {entry.decision?.entry_price && (
                                                <div>
                                                    <p className="text-sm text-gray-500">Entry Price</p>
                                                    <p className="font-semibold">${entry.decision.entry_price.toFixed(2)}</p>
                                                </div>
                                            )}
                                            {entry.decision?.exit_price && (
                                                <div>
                                                    <p className="text-sm text-gray-500">Exit Price</p>
                                                    <p className="font-semibold">${entry.decision.exit_price.toFixed(2)}</p>
                                                </div>
                                            )}
                                            {entry.decision?.pnl !== undefined && entry.decision.pnl !== null && (
                                                <div>
                                                    <p className="text-sm text-gray-500">PnL</p>
                                                    <p className={`font-bold text-lg ${entry.decision.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                        {entry.decision.pnl >= 0 ? '+' : ''}{entry.decision.pnl.toFixed(2)}
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                        {entry.decision?.notes && (
                                            <div className="mt-3">
                                                <p className="text-sm text-gray-500">Notes</p>
                                                <p className="text-gray-700 mt-1">{entry.decision.notes}</p>
                                            </div>
                                        )}
                                    </div>
                                ) : null}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {editingEntry && (
                <TradeDetailsDialog
                    decision={editingEntry.decision}
                    onSave={handleSaveTradeDetails}
                    onClose={() => setEditingEntry(null)}
                />
            )}
        </DashboardLayout>
    );
}
