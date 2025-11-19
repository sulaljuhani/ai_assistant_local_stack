#!/bin/bash
# AI Stack - Migration Runner using actual PostgreSQL container credentials
# Uses the credentials from the running PostgreSQL container

set -e

# Use the actual PostgreSQL container credentials
export POSTGRES_USER=aistack_user
export POSTGRES_PASSWORD=evajGtvUPs5XILtujFyPouBB0A5BHeYOji3D9TajoOw2
export POSTGRES_DB=aistack
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5434

echo "✓ Using PostgreSQL container credentials"
echo "  User: $POSTGRES_USER"
echo "  Database: $POSTGRES_DB"
echo "  Host: $POSTGRES_HOST:$POSTGRES_PORT"
echo ""

# Run the main migration script
exec ./run-migrations.sh
