# Deployment Guide — TraceabilityTestFunctions5

> Tento súbor je **povinné čítanie** pred prvým deployom. Linux Consumption
> Python má jednu zradnú vlastnosť (popísaná nižšie), ktorá ti dokáže
> "ticho" pochovať deploy. Workflow ju vie vyriešiť — ak rozumieš ako.

---

## TL;DR — Ako deployovať

**Stačí jedno:**

```bash
git push origin main
```

GitHub Actions automaticky spustí workflow `Deploy Azure Function App - TraceabilityTestFunctions5`,
ktorý:
1. Zbuilduje Python závislosti na Azure (Oryx remote build)
2. Nasadí do Function App `TraceabilityTestFunctions5`
3. **Spustí sanity check** — pingne `/api/test`. Ak vráti 404 (známy bug, viď nižšie),
   automaticky vyčistí `WEBSITE_RUN_FROM_PACKAGE` + reštartuje Function App + skúsi znova.
4. Ak ani auto-recovery nepomôže, **workflow fail-ne nahlas** (červené ✗ v Actions).

Beh trvá ~2 minúty. Sleduj v reálnom čase:

```bash
gh run watch --repo FLO-Data/TraceabilityTestFunctions5
```

alebo cez UI: https://github.com/FLO-Data/TraceabilityTestFunctions5/actions

---

## ⚠️ Čo NEROBIŤ

### ❌ Nepoužívaj `./deploy.sh` (Azure Functions Core Tools)

Súbor `deploy.sh` v repe používa `func azure functionapp publish ...`. To je
**iný deployment mechanizmus** ako GitHub Actions a:

- Obíde CI/CD a sanity check
- Môže pretransformovať `WEBSITE_RUN_FROM_PACKAGE` na inú URL → konflikt s GitHub deployom
- Nikto ti to neauditne (žiadny záznam v Actions)
- Po reštarte runtime môže načítať nesprávny balík

**Ak naozaj potrebuješ deployovať z lokálu** (napr. neprístupný internet do GitHubu),
použi rovnaké zdroje ako CI:

```bash
az functionapp deployment source config-zip \
  --name TraceabilityTestFunctions5 \
  --resource-group TraceabilityByFLO \
  --src deploy.zip
# Potom: vyčisti run-from-package a reštartuj
az functionapp config appsettings delete \
  --name TraceabilityTestFunctions5 --resource-group TraceabilityByFLO \
  --setting-names WEBSITE_RUN_FROM_PACKAGE
az functionapp restart --name TraceabilityTestFunctions5 --resource-group TraceabilityByFLO
```

### ❌ Nepushuj kód, ktorý padá pri `import`

`function_app.py` na riadku 6-17 importuje **VŠETKY** moduly s funkciami:

```python
from InfoStatus import bp as info_status_bp
from GetInfoGitter import bp as get_info_gitter_bp
# ... ďalších 10 importov
```

Ak ktorýkoľvek modul má **syntax error**, **chýbajúci symbol** alebo **ImportError**,
**celá Function App padne pri štarte** a žiadne endpointy nebudú zaregistrované
(všetky vrátia 404 — vyzerá to presne ako Linux Consumption bug, ale nie je to ono).

**Pred pushom otestuj lokálne:**

```bash
python -c "import function_app"  # musí prejsť bez chyby
```

### ❌ Pozor na T-SQL string literály

V SQL queries používaj **jednoduché úvodzovky** pre stringy:

```sql
'12345' AS part_type    -- ✅ string literál
"12345" AS part_type    -- ❌ identifier (hľadá stĺpec menom 12345)
[part_type] AS part_type -- ✅ existujúci stĺpec
```

Endpoint pravdepodobne neuvidíš padnúť (vráti 200), ale dáta budú zlé.

---

## 🐛 Známy bug: Linux Consumption Python + WEBSITE_RUN_FROM_PACKAGE

### Symptómy
- GitHub Actions deploy ukončí so zeleným ✓
- Všetkých 12 endpointov vracia **404**
- `az functionapp function list` vracia prázdny zoznam
- V Azure Portal → Function App → Functions je tiež prázdno

### Príčina
Azure Functions Action po Oryx buildu nahrá balík do storage blobu a nastaví
app setting `WEBSITE_RUN_FROM_PACKAGE=<blob-url>`. Runtime občas tento setting
"prilepí" k starej (zlomenej) URL a nový kód nikdy nepoužije.

### Automatické riešenie
Workflow má **post-deploy sanity check** ktorý toto detekuje a vyrieši
(`.github/workflows/deploy-functions-test5.yml` → step
*"Post-deploy sanity check + auto-recovery"*).

### Manuálne riešenie (ak by to nestačilo)

```bash
# 1. Zmaž zaseknutý setting
az functionapp config appsettings delete \
  --name TraceabilityTestFunctions5 \
  --resource-group TraceabilityByFLO \
  --setting-names WEBSITE_RUN_FROM_PACKAGE

# 2. Restart
az functionapp restart \
  --name TraceabilityTestFunctions5 \
  --resource-group TraceabilityByFLO

# 3. Počkaj 30s a otestuj
sleep 30
curl https://traceabilitytestfunctions5.azurewebsites.net/api/test
# Očakávaná odpoveď: "Test function works with Python 3.11!"
```

---

## 🛠️ Lokálny setup (prvý raz)

### 1. Clone + venv

```bash
git clone https://github.com/FLO-Data/TraceabilityTestFunctions5.git
cd TraceabilityTestFunctions5

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. `local.settings.json`

Pre lokálny beh potrebuješ tajomstvá (DB heslo, App Insights, atď.) — sú v
súbore `local.settings.json`, ktorý je **git-ignored** (a aj má byť).

Skopíruj template a vyplň hodnoty:

```bash
cp local.settings.json.example local.settings.json
```

Hodnoty získaš:
- Od kolegu cez **bezpečný kanál** (Bitwarden/Signal, NIE e-mail)
- Alebo z Azure Portal → `TraceabilityTestFunctions5` → Configuration → Application settings

### 3. Lokálny beh funkcií

```bash
func start
```

Funkcie počúvajú na `http://localhost:7071/api/...`.

### 4. Cursor / VS Code

Workspace má v `.vscode/` nastavenia pre Azure Functions extension. Doinštaluj:
- **Azure Functions** (ms-azuretools.vscode-azurefunctions)
- **Python** (ms-python.python)

---

## 🔍 Debug failed deployu

### Pozri logy posledného behu

```bash
gh run view --repo FLO-Data/TraceabilityTestFunctions5 --log
# alebo konkrétny run:
gh run view <run-id> --repo FLO-Data/TraceabilityTestFunctions5 --log
```

### Live logy z Function App (po deploye)

```bash
az functionapp log tail \
  --name TraceabilityTestFunctions5 \
  --resource-group TraceabilityByFLO
```

(Stream zastavíš `Ctrl+C`.)

### Application Insights query (Azure Portal)

Function App → Application Insights → Logs:

```kusto
traces
| where timestamp > ago(1h)
| order by timestamp desc
| take 100
```

### Lokálna kontrola pred pushom

```bash
# 1. Importy musia prejsť
python -c "import function_app"

# 2. Skús lokálne spustiť
func start
# Otvor v inom termináli:
curl http://localhost:7071/api/test
# Očakávaná odpoveď: "Test function works with Python 3.11!"
```

---

## 📋 Workflow file: čo robí krok po kroku

`.github/workflows/deploy-functions-test5.yml`:

| Step | Účel |
|---|---|
| `Checkout repository` | `git clone` na runner |
| `Set up Python 3.11` | inštalácia interpretra |
| `Login to Azure (OIDC)` | autentifikácia cez federovaný credential MSI `github-TraceabilityTestFunctions5` (žiadne tajomstvá v secrets — len Client/Tenant/Subscription ID) |
| `Deploy Azure Functions (remote Oryx build)` | nahrá zip + Azure si sám buildne závislosti |
| **`Post-deploy sanity check + auto-recovery`** | pingne `/api/test`, ak 404 → vyčistí `WEBSITE_RUN_FROM_PACKAGE` + restart + retry; ak stále 404 → fail |
| `Logout from Azure` | bezpečnostné cleanup |

---

## 🔐 Azure setup (pre referenciu, netreba meniť)

| Vec | Hodnota |
|---|---|
| **Function App** | `TraceabilityTestFunctions5` (Linux Consumption Y1, Python 3.11, Sweden Central) |
| **Resource Group** | `TraceabilityByFLO` |
| **Subscription** | `MTX Group` (`6ef216eb-043c-4e4d-8171-44adc34de7a9`) |
| **Tenant** | `1a3b752d-0130-49e3-98d1-8122975db518` |
| **MSI** | `github-TraceabilityTestFunctions5` (clientId `d7b3275e-34ff-4d33-bc8e-55b6c5829abe`) |
| **MSI rola** | Contributor **scoped LEN** na túto Function App |
| **Federated credential subjects** | `repo:FLO-Data/TraceabilityTestFunctions5:ref:refs/heads/main` a `repo:FLO-Data/TraceabilityTestFunctions5:environment:Test` |
| **GitHub secrets** | `AZURE_CLIENT_ID_FUNC_TEST5`, `AZURE_TENANT_ID_FUNC_TEST5`, `AZURE_SUBSCRIPTION_ID_FUNC_TEST5` |

### Get function key

```bash
az functionapp keys list \
  --name TraceabilityTestFunctions5 \
  --resource-group TraceabilityByFLO \
  --query "functionKeys.default" -o tsv
```

---

## 🚦 Workflow tabuľka rozhodovania

| Situácia | Čo spraviť |
|---|---|
| Bežná zmena kódu | `git push origin main` → hotovo (~2 min) |
| Manuálne spustiť deploy bez commitu | GitHub Actions → workflow → **Run workflow** |
| Workflow je červený, sanity zlyhalo | Pozri `gh run view <id> --log`, najčastejšie ImportError v `function_app.py` alebo nejakom blueprinte |
| Workflow zelený, ale `/api/test` vracia 404 | Niečo prelomilo runtime po sanity (zriedkavé). Manual recovery (viď vyššie). |
| Potrebujem rollback | `git revert <commit>` + push, alebo redeploy starého commitu cez workflow_dispatch |
| Potrebujem otestovať lokálne | `func start`, otvor `http://localhost:7071/api/test` |

---

## 📝 Code conventions

- **Blueprints:** každá funkcia má vlastný `*.py` súbor, exportuje `bp = func.Blueprint()`
- **Registrácia:** vždy v `function_app.py` cez `app.register_functions(bp)`
- **Auth levels:**
  - `ANONYMOUS` — verejné (read-only data)
  - `FUNCTION` — vyžaduje `?code=<function-key>` (write operácie)
- **Logging:** `logging.info(...)` ide do Application Insights
- **DB connection:** používaj `get_connection_string()` helper, nie hardcoded
- **Async:** ak chceš `await`, deklaruj funkciu ako `async def http_function(req)`

---

## ❓ Otázky / problémy

Píš na: **maros.machaj@weareflo.com** alebo cez Teams.
