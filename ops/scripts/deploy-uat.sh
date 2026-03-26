#!/bin/bash
echo "Deploying to UAT..."
export ENV=UAT
python -m pytest agents/agent-2-error-diagnosis/tests/ -v
echo "Deploy UAT done."
