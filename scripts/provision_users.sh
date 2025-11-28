#!/usr/bin/env bash
set -euo pipefail

# User Provisioning Script (Bash)
#
# This script creates users directly in the PostgreSQL database using psql.
# It's simpler and faster than the Python version for basic provisioning.
#
# Usage:
#   ./scripts/provision_users.sh users.json
#   
#   Or with inline data:
#   ./scripts/provision_users.sh --inline '[{"email": "user@example.com", "password": "test123"}]'

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Database connection from environment or defaults (matching docker-compose.yml)
DB_HOST="${DB_HOST:-timescaledb}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ffbot}"
DB_USER="${DB_USER:-ffbot}"
DB_PASSWORD="${DB_PASSWORD}"

# Check if DB_PASSWORD is set
if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}❌ Error: DB_PASSWORD environment variable is not set${NC}"
    echo "Please set it in your .env file or export it:"
    echo "  export DB_PASSWORD='your_password'"
    exit 1
fi

# Export PGPASSWORD for psql
export PGPASSWORD="$DB_PASSWORD"

# Function to execute SQL
execute_sql() {
    local sql="$1"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "$sql"
}

# Function to generate a UUID
generate_uuid() {
    python3 -c "import uuid; print(str(uuid.uuid4()))"
}

# Function to generate link code
generate_link_code() {
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

# Function to hash password (bcrypt)
hash_password() {
    local password="$1"
    python3 -c "import bcrypt; print(bcrypt.hashpw('$password'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))"
}

# Function to provision a single user
provision_user() {
    local email="$1"
    local password="$2"
    local telegram_chat_id="$3"
    local telegram_username="$4"
    local telegram_first_name="$5"
    local telegram_last_name="$6"
    
    echo -e "${BLUE}Processing: $email${NC}"
    
    # Check if user exists
    local existing_user_id=$(execute_sql "SELECT id FROM users WHERE email = '$email';" | tr -d '[:space:]')
    
    if [ ! -z "$existing_user_id" ]; then
        echo -e "${YELLOW}⚠️  User $email already exists (ID: $existing_user_id)${NC}"
        return 1
    fi
    
    # Generate user ID and link code
    local user_id=$(generate_uuid)
    local link_code=$(generate_link_code)
    local password_hash=""
    
    # Hash password if provided
    if [ ! -z "$password" ] && [ "$password" != "null" ]; then
        password_hash=$(hash_password "$password")
    fi
    
    # Create user
    local sql="INSERT INTO users (id, email, password_hash, link_code, status, created_at) 
               VALUES ('$user_id', '$email', "
    
    if [ ! -z "$password_hash" ]; then
        sql+="'$password_hash', "
    else
        sql+="NULL, "
    fi
    
    sql+="'$link_code', 'active', NOW());"
    
    execute_sql "$sql" > /dev/null
    
    # Create default settings
    local settings_sql="INSERT INTO user_settings (
        user_id, ff_threshold, min_open_interest, min_volume, 
        max_bid_ask_pct, sigma_fwd_floor, stability_scans, 
        cooldown_minutes, timezone, scan_priority, discovery_mode, vol_point
    ) VALUES (
        '$user_id', 1.2, 100, 50, 
        0.5, 0.1, 1, 
        60, 'UTC', 'standard', false, 'ATM'
    );"
    
    execute_sql "$settings_sql" > /dev/null
    
    # Create Telegram chat link if provided
    if [ ! -z "$telegram_chat_id" ] && [ "$telegram_chat_id" != "null" ]; then
        if [ -z "$telegram_first_name" ] || [ "$telegram_first_name" == "null" ]; then
            echo -e "${RED}❌ Error: telegram_first_name is required when telegram_chat_id is provided${NC}"
            return 1
        fi
        
        local telegram_sql="INSERT INTO telegram_chats (
            user_id, chat_id, username, first_name, last_name, linked_at
        ) VALUES ("
        
        telegram_sql+="'$user_id', '$telegram_chat_id', "
        
        if [ ! -z "$telegram_username" ] && [ "$telegram_username" != "null" ]; then
            telegram_sql+="'$telegram_username', "
        else
            telegram_sql+="NULL, "
        fi
        
        telegram_sql+="'$telegram_first_name', "
        
        if [ ! -z "$telegram_last_name" ] && [ "$telegram_last_name" != "null" ]; then
            telegram_sql+="'$telegram_last_name', "
        else
            telegram_sql+="NULL, "
        fi
        
        telegram_sql+="NOW());"
        
        execute_sql "$telegram_sql" > /dev/null
    fi
    
    echo -e "${GREEN}✅ Created user: $email${NC}"
    echo -e "   User ID: $user_id"
    echo -e "   Link Code: $link_code"
    if [ ! -z "$telegram_chat_id" ] && [ "$telegram_chat_id" != "null" ]; then
        echo -e "   Telegram: Linked to chat $telegram_chat_id"
    fi
    
    return 0
}

# Main script
main() {
    echo -e "${BLUE}🚀 Starting user provisioning...${NC}"
    echo "$(printf '=%.0s' {1..60})"
    
    # Parse arguments
    local json_data=""
    
    if [ "$#" -eq 0 ]; then
        echo -e "${RED}❌ Error: No arguments provided${NC}"
        echo "Usage: $0 <file.json>"
        echo "   or: $0 --inline '<json>'"
        exit 1
    fi
    
    if [ "$1" == "--inline" ]; then
        if [ "$#" -lt 2 ]; then
            echo -e "${RED}❌ Error: --inline requires JSON data${NC}"
            exit 1
        fi
        json_data="$2"
    else
        if [ ! -f "$1" ]; then
            echo -e "${RED}❌ Error: File not found: $1${NC}"
            exit 1
        fi
        json_data=$(cat "$1")
    fi
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}❌ Error: jq is required but not installed${NC}"
        echo "Install with: sudo apt-get install jq  (or brew install jq on Mac)"
        exit 1
    fi
    
    # Check database connection
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${RED}❌ Error: Cannot connect to database${NC}"
        echo "  Host: $DB_HOST:$DB_PORT"
        echo "  Database: $DB_NAME"
        echo "  User: $DB_USER"
        exit 1
    fi
    
    # Parse JSON and provision users
    local created_count=0
    local skipped_count=0
    local total_count=$(echo "$json_data" | jq '. | length')
    
    for i in $(seq 0 $((total_count - 1))); do
        local email=$(echo "$json_data" | jq -r ".[$i].email // empty")
        
        if [ -z "$email" ]; then
            echo -e "${RED}❌ Skipping user at index $i: email is required${NC}"
            ((skipped_count++))
            continue
        fi
        
        local password=$(echo "$json_data" | jq -r ".[$i].password // empty")
        local telegram_chat_id=$(echo "$json_data" | jq -r ".[$i].telegram_chat_id // empty")
        local telegram_username=$(echo "$json_data" | jq -r ".[$i].telegram_username // empty")
        local telegram_first_name=$(echo "$json_data" | jq -r ".[$i].telegram_first_name // empty")
        local telegram_last_name=$(echo "$json_data" | jq -r ".[$i].telegram_last_name // empty")
        
        if provision_user "$email" "$password" "$telegram_chat_id" "$telegram_username" "$telegram_first_name" "$telegram_last_name"; then
            ((created_count++))
        else
            ((skipped_count++))
        fi
        
        echo ""
    done
    
    # Summary
    echo "$(printf '=%.0s' {1..60})"
    echo -e "${BLUE}Summary:${NC}"
    echo -e "  ${GREEN}✅ Created: $created_count${NC}"
    echo -e "  ${YELLOW}⚠️  Skipped: $skipped_count${NC}"
    echo -e "  ${BLUE}📊 Total: $total_count${NC}"
    echo "$(printf '=%.0s' {1..60})"
}

# Run main
main "$@"
