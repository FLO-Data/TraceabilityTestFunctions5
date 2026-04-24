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
1. **Lokálne** zbuilduje Python závislosti do `.python_packages/lib/site-packages/`
   (oficiálny layout pre Python Functions — runtime to automaticky pridá do `sys.path`)
2. Zip-ne celé repo (vrátane `.python_packages`) a nahodí do Function App
   `TraceabilityTestFunctions5` (cez `WEBSITE_RUN_FROM_PACKAGE` blob URL)
3. **Spustí post-deploy sanity check** — pingne `/api/test` v 5 pokusoch s exponential
   backoff (20/30/45/60/90s). Ak ani po nich nie 200, urobí soft restart + jeden retry.
4. Ak sanity nakoniec zlyhá, **workflow fail-ne nahlas** (červené ✗ v Actions) — ale
   **NIKDY nemení app settings** (žiadne mazanie RUN_FROM_PACKAGE, žiadne mutácie konfigurácie).

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
- Môže prepísať `WEBSITE_RUN_FROM_PACKAGE` na inú URL → konflikt s GitHub deployom
- Nikto ti to neauditne (žiadny záznam v Actions)
- Po reštarte runtime môže načítať nesprávny balík

**Ak naozaj potrebuješ deployovať z lokálu** (napr. neprístupný internet do GitHubu),
napodobni to čo robí workflow:

```bash
# 1. Lokálne nainštaluj deps do .python_packages
rm -rf .python_packages
pip install --target=".python_packages/lib/site-packages" -r requirements.txt

# 2. Zip + deploy (functions-action ekvivalent)
zip -r deploy.zip . -x "*.git*" "*.venv*" "venv/*" "__pycache__/*" "*.zip"
az functionapp deployment source config-zip \
  --name TraceabilityTestFunctions5 \
  --resource-group TraceabilityByFLO \
  --src deploy.zip
# 3. Počkaj 30s a otestuj
sleep 30 && curl -s -o /dev/null -w "%{http_code}\n" \
  https://traceabilitytestfunctions5.azurewebsites.net/api/test
```

> ⚠️ **NIKDY nezmazávaj `WEBSITE_RUN_FROM_PACKAGE`!** Tento app setting drží URL
> na blob s práve nasadeným kódom — vymazaním odpojíš app od deployu a spadne do
> 503 alebo do starého filesystem fallback-u.

### ❌ Neprepisuj `WEBSITE_RUN_FROM_PACKAGE` ručne

Tento setting spravuje **GitHub Actions deploy** (alebo `az functionapp deployment
source config-zip`). Manuálne `az functionapp config appsettings set
WEBSITE_RUN_FROM_PACKAGE=...` je takmer vždy chyba:

- `=1` → runtime hľadá zip v `/home/data/SitePackages/` ktorý tam pri RBAC deploye
  nie je → **503 Service Unavailable**
- `=<vlastná URL>` → runtime sa pokúsi stiahnuť tvoju URL → ak je nedostupná, app spadne
- Vymazanie → app nemá kde nájsť kód, ide do filesystem fallback-u (často so starou verziou)

**Ak chceš vrátiť app k živote, znovu spusti workflow** (push prázdny commit alebo
GitHub Actions → workflow → Run workflow). Workflow nastaví `WEBSITE_RUN_FROM_PACKAGE`
správne sám.

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

## 🐛 Najčastejšie failure módy a ako ich rozpoznať

### Mód A — Deploy "úspešný", ale 0 funkcií registrovaných (404 na všetkom)

**Symptómy:**
- GitHub Actions deploy ukončí so zeleným ✓ (deploy step)
- Sanity check zlyhá (5x retry + soft restart = stále 404)
- `az functionapp function list` vracia **prázdny zoznam** alebo má len `TestFunction`
- V Azure Portal → Function App → Functions je tiež prázdno

**Príčina:** Zip nahodený do Function App **neobsahuje Python dependencies**
(`pyodbc`, `azure-functions`, ...). Runtime nemôže importovať blueprints
v `function_app.py` a žiadne endpointy sa nezaregistrujú.

**Prečo to nastáva:** Zabudli sme krok `pip install --target=".python_packages/lib/site-packages"`
v workflow-e, alebo niekto použil `Azure/functions-action@v1` s `enable-oryx-build:
true` (ktorý sa pri RBAC RUN_FROM_PACKAGE deploye vie zachovať tak, že platforma
build neurobí, ale action to nahlási ako úspech).

**Riešenie:** Skontroluj že workflow má krok *"Install dependencies into .python_packages"*
**pred** deploy stepom. Pozri `.github/workflows/deploy-functions-test5.yml`.

### Mód B — `function_app.py` padá pri importe

**Symptómy:**
- Identické s módom A (404 na všetkom, 0 funkcií)
- V Application Insights → traces vidíš `ImportError`, `ModuleNotFoundError`,
  `SyntaxError` zhruba pri štarte workera

**Príčina:** Niektorý blueprint má syntax error / chýbajúci symbol / chybný import,
takže `function_app.py` (ktorý ich všetky importuje na riadkoch 6–17) padne.

**Riešenie:** Pred pushom **VŽDY** spusti:
```bash
python -c "import function_app"
```
Musí prejsť bez chyby. Ak nie, oprav v lokáli, **nepushuj** rozbité.

### Mód C — Endpoint vráti 200, ale dáta sú nezmyselné

**Príklad z reality (apr 2026):** Niekto zmenil v SQL `ps.[part_type] AS part_type`
na `"12345" AS part_type`. T-SQL interpretuje `"..."` ako **identifier** (názov stĺpca),
nie ako string literál. Query vrátila zlé dáta bez SQL erroru → endpoint hlásil 200,
ale `part_type` v JSON-e bol celkom mimo.

**Riešenie:** Viď ďalšiu sekciu o T-SQL string literáloch (vyššie). Test endpoint
nie len curl-om na 200, ale skontroluj aj **obsah** odpovede.

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
| **`Install dependencies into .python_packages`** | `pip install --target=".python_packages/lib/site-packages" -r requirements.txt` — bez tohto by zip neobsahoval `pyodbc/azure-functions/...` a app by nezaregistroval žiadne funkcie |
| `Login to Azure (OIDC)` | autentifikácia cez federovaný credential MSI `github-TraceabilityTestFunctions5` (žiadne tajomstvá v secrets — len Client/Tenant/Subscription ID) |
| `Deploy Azure Functions (zip with bundled deps)` | zip-ne celé repo (vrátane `.python_packages`) a nahodí cez RBAC do blob storage; nastaví `WEBSITE_RUN_FROM_PACKAGE` |
| **`Post-deploy sanity check + retry`** | 5× pingne `/api/test` s exp. backoff (20/30/45/60/90s); ak stále nie 200, soft restart + 1 retry; **NIKDY nemení app settings**; ak stále nie 200 → workflow fail-ne |
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
| Workflow je červený na sanity step | Pozri `gh run view <id> --log` + `az functionapp function list -n TraceabilityTestFunctions5 -g TraceabilityByFLO --query "length(@)"`. Ak vracia 0 → mód A/B. Pozri logy v App Insights pre ImportError. |
| Endpoint vráti 200 ale dáta sú zlé | Mód C — over T-SQL queries (single quotes pre stringy!) |
| App vráti 503 | Pravdepodobne niekto mu zmenil `WEBSITE_RUN_FROM_PACKAGE` ručne. Re-run workflow, **nemaž** ten setting. |
| Potrebujem rollback | `git revert <commit>` + push, alebo Actions → vyber starší úspešný run → **Re-run all jobs** |
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

---

## 📜 Changelog workflow-u

| Dátum | Commit | Zmena | Prečo |
|---|---|---|---|
| 2026-04-24 | `0f22ca6` | **Bundling deps cez `.python_packages`** + vypnutý Oryx remote build | `Azure/functions-action@v1` s `enable-oryx-build: true` pri RBAC RUN_FROM_PACKAGE deploye reálne `pip install` neurobil → 0 funkcií zaregistrovaných (404 na všetkom). Lokálny `pip install --target` je deterministický a oficiálne odporúčaný layout. |
| 2026-04-24 | `12269e4` | **Auto-recovery už NEzmazáva `WEBSITE_RUN_FROM_PACKAGE`** | Pôvodná logika (zmaž setting + restart) síce vyriešila 404, ale **odpojila app od práve nasadeného zip-u** → app spadol do filesystem fallback-u so starou verziou kódu. Nová logika robí len 5x retry s exp. backoff + soft restart, žiadne mutácie konfigurácie. |
| 2026-04-21 | (predošlé) | Pôvodný workflow s Oryx remote build + auto-recovery cez mazanie RUN_FROM_PACKAGE | Funkčné len za špecifických okolností (ak wwwroot už mal staré deps z predchádzajúceho `func azure functionapp publish`). Po čistom deploy-i to nefungovalo. |
