#!/bin/bash
echo "Deploying to DEV..."
export ENV=DEV
python -m pytest agents/agent-2-error-diagnosis/tests/ -v
echo "Deploy DEV done."
