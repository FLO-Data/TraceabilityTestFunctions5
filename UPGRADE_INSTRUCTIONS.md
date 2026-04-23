# 🚀 Upgrade na Python 3.11 - Instrukce
# 🚀 Upgrade to Python 3.11 - Instructions

## 📋 Prerekvizity / Prerequisites

### 1. Nainstaluj Azure CLI
```bash
brew install azure-cli
```

### 2. Nainstaluj Azure Functions Core Tools
```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
```

### 3. Přihlaš se do Azure
```bash
az login
```

---

## 🎯 Rychlý upgrade (doporučeno)
## 🎯 Quick upgrade (recommended)

Spusť připravený skript:
```bash
./upgrade_to_python311.sh
```

Tento skript automaticky:
- ✅ Najde tvou Function App a Resource Group
- ✅ Zobrazí aktuální konfiguraci
- ✅ Upgraduje runtime na Python 3.11
- ✅ Restartuje aplikaci
- ✅ Ověří změny

---

## 📦 Po upgrade - Redeploy aplikace
## 📦 After upgrade - Redeploy application

Po úspěšném upgrade spusť deployment:
```bash
./deploy.sh
```

---

## 🔧 Manuální příkazy (pokud chceš kontrolu nad každým krokem)
## 🔧 Manual commands (if you want control over each step)

### 1. Najdi Resource Group
```bash
az functionapp show --name TraceabilityTestFunctions5 --query resourceGroup -o tsv
```

### 2. Změň Python verzi
```bash
# Nahraď <RESOURCE_GROUP> skutečným názvem
az functionapp config set \
    --name TraceabilityTestFunctions5 \
    --resource-group <RESOURCE_GROUP> \
    --linux-fx-version "Python|3.11"
```

### 3. Restart Function App
```bash
az functionapp restart \
    --name TraceabilityTestFunctions5 \
    --resource-group <RESOURCE_GROUP>
```

### 4. Ověř změnu
```bash
az functionapp config show \
    --name TraceabilityTestFunctions5 \
    --resource-group <RESOURCE_GROUP> \
    --query linuxFxVersion
```

### 5. Deploy aplikaci
```bash
func azure functionapp publish TraceabilityTestFunctions5 --python
```

---

## ✅ Ověření / Verification

Po deployment otestuj endpointy:

### Test endpoint:
```bash
curl https://traceabilitytestfunctions5.azurewebsites.net/api/test
```

### InfoStatus endpoint:
```bash
curl "https://traceabilitytestfunctions5.azurewebsites.net/api/infostatus?part_id=TEST123"
```

---

## 🐛 Troubleshooting

### Chyba: "Function App not found"
```bash
# Zobraz všechny Function Apps
az functionapp list --query "[].{Name:name, ResourceGroup:resourceGroup}" -o table
```

### Chyba: "Authentication required"
```bash
# Přihlaš se znovu
az login
```

### Chyba při deployment
```bash
# Zkontroluj logy
az functionapp log tail --name TraceabilityTestFunctions5 --resource-group <RESOURCE_GROUP>
```

### Lokální testování s Python 3.11
```bash
# Vytvoř virtuální prostředí s Python 3.11
python3.11 -m venv venv
source venv/bin/activate

# Nainstaluj závislosti
pip install -r requirements.txt

# Spusť lokálně
func start
```

---

## 📝 Co bylo změněno / What was changed

1. ✅ Vytvořen `.python_version` soubor → specifikuje Python 3.11
2. ✅ Vytvořen `.funcignore` → ignoruje zbytečné soubory při deployment
3. ✅ Vytvořen `upgrade_to_python311.sh` → automatický upgrade skript
4. ✅ Vytvořen `deploy.sh` → automatický deployment skript

---

## 🔗 Užitečné odkazy / Useful links

- [Azure Functions Python support](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Azure CLI Function App commands](https://learn.microsoft.com/en-us/cli/azure/functionapp)
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)

---

## 📞 Support

Pokud narazíš na problém, zkontroluj:
1. Azure Portal → Function App → Logs
2. Azure Portal → Function App → Configuration → Application settings
3. Lokální test: `func start` a zkontroluj chybové hlášky


