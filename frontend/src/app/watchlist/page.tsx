'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import { Ticker } from '@/types';
import DashboardLayout from '../dashboard/layout';

export default function WatchlistPage() {
    const [watchlist, setWatchlist] = useState<Ticker[]>([]);
    const [newTicker, setNewTicker] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchWatchlist();
    }, []);

    const fetchWatchlist = async () => {
        try {
            const response = await apiClient.get('/api/watchlist');
            setWatchlist(response.data);
        } catch (err: any) {
            setError('Failed to load watchlist');
        } finally {
            setLoading(false);
        }
    };

    const addTicker = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        try {
            await apiClient.post('/api/watchlist', { ticker: newTicker.toUpperCase() });
            setNewTicker('');
            fetchWatchlist();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to add ticker');
        }
    };

    const removeTicker = async (ticker: string) => {
        try {
            await apiClient.delete(`/api/watchlist/${ticker}`);
            fetchWatchlist();
        } catch (err: any) {
            setError('Failed to remove ticker');
        }
    };

    return (
        <DashboardLayout>
            <div className="px-2 sm:px-4 py-4 sm:py-6">
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4 sm:mb-6">Watchlist</h1>

                <div className="bg-white shadow rounded-lg p-4 sm:p-6 mb-4 sm:mb-6">
                    <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">Add Ticker</h2>
                    <form onSubmit={addTicker} className="flex flex-col sm:flex-row gap-2 sm:gap-4">
                        <input
                            type="text"
                            value={newTicker}
                            onChange={(e) => setNewTicker(e.target.value)}
                            placeholder="Enter ticker symbol (e.g., SPY)"
                            className="flex-1 px-3 sm:px-4 py-2 sm:py-2.5 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button
                            type="submit"
                            className="px-6 py-2.5 bg-blue-700 text-white rounded-md hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors font-medium min-h-[44px]"
                        >
                            Add
                        </button>
                    </form>
                    {error && (
                        <p className="mt-2 text-sm text-red-600">{error}</p>
                    )}
                </div>

                <div className="bg-white shadow rounded-lg p-4 sm:p-6">
                    <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">Your Tickers</h2>
                    {loading ? (
                        <p className="text-sm">Loading...</p>
                    ) : watchlist.length === 0 ? (
                        <p className="text-sm sm:text-base text-gray-600">No tickers in your watchlist yet.</p>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                            {watchlist.map((item) => (
                                <div
                                    key={item.ticker}
                                    className="border border-gray-200 rounded-lg p-3 sm:p-4 flex justify-between items-center hover:border-gray-300 transition-colors"
                                >
                                    <div className="flex-1 min-w-0">
                                        <p className="font-semibold text-base sm:text-lg truncate">{item.ticker}</p>
                                        <p className="text-xs sm:text-sm text-gray-500">
                                            Added: {new Date(item.added_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => removeTicker(item.ticker)}
                                        className="text-red-600 hover:text-red-800 font-medium text-sm ml-2 px-2 py-1 min-h-[36px] sm:min-h-[32px]"
                                    >
                                        Remove
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </DashboardLayout>
    );
}
