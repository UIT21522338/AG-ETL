#!/bin/bash
echo "Deploying to DEV..."
export ENV=DEV
python -m pytest agents/agent-1-error-diagnosis/tests/ -v
echo "Deploy DEV done."
