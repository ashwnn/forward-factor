'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/auth-context';
import apiClient from '@/lib/api-client';
import { Ticker } from '@/types';
import TradingViewWidget from '@/components/TradingViewWidget';

export default function DashboardPage() {
    const { user } = useAuth();
    const [watchlist, setWatchlist] = useState<Ticker[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchWatchlist = async () => {
            try {
                const response = await apiClient.get('/api/watchlist');
                setWatchlist(response.data);
            } catch (err) {
                console.error('Failed to load watchlist', err);
            } finally {
                setLoading(false);
            }
        };

        fetchWatchlist();
    }, []);

    return (
        <div className="px-4 py-6 sm:px-0">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>

            <div className="bg-white shadow rounded-lg p-6 mb-6">
                <h2 className="text-xl font-semibold mb-4">Welcome!</h2>
                <p className="text-gray-600">
                    You're logged in as <span className="font-medium">{user?.email}</span>
                </p>
                {user?.telegram_username && (
                    <p className="text-gray-600 mt-2">
                        Telegram: <span className="font-medium">@{user.telegram_username}</span>
                    </p>
                )}
            </div>

            <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Your Watchlist</h2>
                {loading ? (
                    <p>Loading charts...</p>
                ) : watchlist.length === 0 ? (
                    <div className="bg-white shadow rounded-lg p-6">
                        <p className="text-gray-600">
                            Your watchlist is empty. Go to the <a href="/watchlist" className="text-blue-600 hover:underline">Watchlist</a> page to add tickers.
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {watchlist.map((item) => (
                            <div key={item.ticker} className="bg-white shadow rounded-lg overflow-hidden h-80">
                                <div className="h-full w-full">
                                    <TradingViewWidget ticker={item.ticker} />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
