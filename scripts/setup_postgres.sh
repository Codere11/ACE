#!/bin/bash
# PostgreSQL Database Setup Script
# Run this to set up your local PostgreSQL database for ACE

set -e

DB_NAME="ace_production"
DB_USER="ace_user"
DB_PASSWORD="ace_dev_password_change_in_production"

echo "🔧 Setting up PostgreSQL for ACE..."
echo ""
echo "This will create:"
echo "  - Database: $DB_NAME"
echo "  - User: $DB_USER"
echo "  - Password: $DB_PASSWORD (CHANGE THIS IN PRODUCTION!)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# Run as postgres user
sudo -u postgres psql <<EOF
-- Create user if not exists
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;

\q
EOF

echo ""
echo "✅ PostgreSQL setup complete!"
echo ""
echo "📝 Add this to your .env file:"
echo ""
echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "🚀 Next steps:"
echo "  1. Add DATABASE_URL to .env"
echo "  2. Run: python scripts/migrate_to_postgres.py"
echo "  3. Run: ./run_backend.sh"
