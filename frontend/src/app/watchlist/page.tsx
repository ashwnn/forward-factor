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
            <div className="px-4 py-6 sm:px-0">
                <h1 className="text-3xl font-bold text-gray-900 mb-6">Watchlist</h1>

                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Add Ticker</h2>
                    <form onSubmit={addTicker} className="flex gap-4">
                        <input
                            type="text"
                            value={newTicker}
                            onChange={(e) => setNewTicker(e.target.value)}
                            placeholder="Enter ticker symbol (e.g., SPY)"
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button
                            type="submit"
                            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            Add
                        </button>
                    </form>
                    {error && (
                        <p className="mt-2 text-sm text-red-600">{error}</p>
                    )}
                </div>

                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-xl font-semibold mb-4">Your Tickers</h2>
                    {loading ? (
                        <p>Loading...</p>
                    ) : watchlist.length === 0 ? (
                        <p className="text-gray-600">No tickers in your watchlist yet.</p>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                            {watchlist.map((item) => (
                                <div
                                    key={item.ticker}
                                    className="border border-gray-200 rounded-lg p-4 flex justify-between items-center"
                                >
                                    <div>
                                        <p className="font-semibold text-lg">{item.ticker}</p>
                                        <p className="text-sm text-gray-500">
                                            Added: {new Date(item.added_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => removeTicker(item.ticker)}
                                        className="text-red-600 hover:text-red-800 font-medium"
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
