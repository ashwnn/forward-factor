'use client';

import { useState } from 'react';
import { Decision } from '@/types';

interface TradeDetailsDialogProps {
    decision?: Decision;
    onSave: (tradeDetails: TradeDetails) => Promise<void>;
    onClose: () => void;
}

export interface TradeDetails {
    entry_price?: number;
    exit_price?: number;
    pnl?: number;
    notes?: string;
}

export default function TradeDetailsDialog({ decision, onSave, onClose }: TradeDetailsDialogProps) {
    const [entryPrice, setEntryPrice] = useState(decision?.entry_price?.toString() || '');
    const [exitPrice, setExitPrice] = useState(decision?.exit_price?.toString() || '');
    const [pnl, setPnl] = useState(decision?.pnl?.toString() || '');
    const [notes, setNotes] = useState(decision?.notes || '');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const handleSave = async () => {
        try {
            setSaving(true);
            setError('');

            const tradeDetails: TradeDetails = {
                entry_price: entryPrice ? parseFloat(entryPrice) : undefined,
                exit_price: exitPrice ? parseFloat(exitPrice) : undefined,
                pnl: pnl ? parseFloat(pnl) : undefined,
                notes: notes || undefined,
            };

            await onSave(tradeDetails);
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save trade details');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full relative">
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
                >
                    ✕
                </button>

                <h2 className="text-2xl font-bold text-gray-900 mb-4">Trade Details</h2>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                        {error}
                    </div>
                )}

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Entry Price
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            value={entryPrice}
                            onChange={(e) => setEntryPrice(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="0.00"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Exit Price
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            value={exitPrice}
                            onChange={(e) => setExitPrice(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="0.00"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            PnL
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            value={pnl}
                            onChange={(e) => setPnl(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="0.00"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Notes
                        </label>
                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            rows={3}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Enter trade notes..."
                        />
                    </div>
                </div>

                <div className="flex gap-3 mt-6">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex-1 bg-blue-700 text-white py-2 px-4 rounded-lg hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {saving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                        onClick={onClose}
                        className="flex-1 bg-gray-700 text-white py-2 px-4 rounded-lg hover:bg-gray-800"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
