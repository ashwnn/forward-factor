export interface User {
    id: string;
    email?: string;
    telegram_chat_id?: string;
    telegram_username?: string;
    created_at: string;
    status: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: User;
}

export interface Ticker {
    ticker: string;
    added_at: string;
    active: boolean;
}

export interface DTEPair {
    front: number;
    back: number;
    front_tol: number;
    back_tol: number;
}

export interface QuietHours {
    enabled: boolean;
    start: string;
    end: string;
}

export interface Settings {
    ff_threshold: number;
    dte_pairs: DTEPair[];
    vol_point: string;
    min_open_interest: number;
    min_volume: number;
    max_bid_ask_pct: number;
    sigma_fwd_floor: number;
    stability_scans: number;
    cooldown_minutes: number;
    quiet_hours: QuietHours;
    preferred_structure: string;
    timezone: string;
    scan_priority: string;
}

export interface Signal {
    id: string;
    ticker: string;
    ff_value: number;
    front_iv: number;
    back_iv: number;
    sigma_fwd: number;
    front_expiry: string;
    back_expiry: string;
    front_dte: number;
    back_dte: number;
    as_of_ts: string;
    quality_score: number;
    vol_point: string;
}

export interface Decision {
    id: string;
    signal_id: string;
    decision: string;
    decision_ts: string;
    entry_price?: number;
    exit_price?: number;
    pnl?: number;
    notes?: string;
}

export interface HistoryEntry {
    signal: Signal;
    decision?: Decision;
}
