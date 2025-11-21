'use client';

import { useAuth } from '@/contexts/auth-context';

export default function DashboardPage() {
    const { user } = useAuth();

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

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="bg-white shadow rounded-lg p-6">
                    <h3 className="text-lg font-semibold mb-2">Watchlist</h3>
                    <p className="text-gray-600 text-sm">
                        Manage your ticker subscriptions and monitor Forward Factor signals.
                    </p>
                </div>

                <div className="bg-white shadow rounded-lg p-6">
                    <h3 className="text-lg font-semibold mb-2">Signals</h3>
                    <p className="text-gray-600 text-sm">
                        View recent Forward Factor signals for your watchlist tickers.
                    </p>
                </div>

                <div className="bg-white shadow rounded-lg p-6">
                    <h3 className="text-lg font-semibold mb-2">History</h3>
                    <p className="text-gray-600 text-sm">
                        Review your signal history and trading decisions.
                    </p>
                </div>
            </div>
        </div>
    );
}
