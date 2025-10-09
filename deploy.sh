#!/bin/bash

# Script pro deployment Azure Function App
# Script for deploying Azure Function App

set -e  # Ukončit při chybě / Exit on error

echo "🚀 Začínám deployment TraceabilityTestFunctions5"
echo "🚀 Starting deployment of TraceabilityTestFunctions5"
echo ""

FUNCTION_APP_NAME="TraceabilityTestFunctions5"

# Zkontroluj Azure Functions Core Tools / Check Azure Functions Core Tools
if ! command -v func &> /dev/null; then
    echo "❌ Azure Functions Core Tools nejsou nainstalované!"
    echo "❌ Azure Functions Core Tools are not installed!"
    echo "Nainstaluj je: brew tap azure/functions && brew install azure-functions-core-tools@4"
    echo "Install them: brew tap azure/functions && brew install azure-functions-core-tools@4"
    exit 1
fi

echo "✅ Azure Functions Core Tools jsou nainstalované"
echo "✅ Azure Functions Core Tools are installed"
echo ""

# Zkontroluj, jestli existuje requirements.txt / Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt nenalezen!"
    echo "❌ requirements.txt not found!"
    exit 1
fi

echo "✅ requirements.txt nalezen"
echo "✅ requirements.txt found"
echo ""

# Deploy aplikace / Deploy application
echo "📦 Nasazuji aplikaci do Azure..."
echo "📦 Deploying application to Azure..."
func azure functionapp publish $FUNCTION_APP_NAME --python

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Deployment HOTOV!"
echo "🎉 Deployment COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
echo "📝 Test endpoints:"
echo "   - https://$FUNCTION_APP_NAME.azurewebsites.net/api/test"
echo "   - https://$FUNCTION_APP_NAME.azurewebsites.net/api/infostatus?part_id=TEST123"
echo ""

