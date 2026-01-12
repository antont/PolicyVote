#!/bin/bash
# Run the PolicyVote election simulation

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Load AWS credentials from ~/.aws/credentials if not already set
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    if [ -f ~/.aws/credentials ]; then
        export AWS_ACCESS_KEY_ID=$(grep aws_access_key_id ~/.aws/credentials | head -1 | cut -d= -f2 | tr -d ' ')
        export AWS_SECRET_ACCESS_KEY=$(grep aws_secret_access_key ~/.aws/credentials | head -1 | cut -d= -f2 | tr -d ' ')
        export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
    fi
fi

# Run the simulation (saves reports to outputs/)
python3 election_minimal.py "$@"
