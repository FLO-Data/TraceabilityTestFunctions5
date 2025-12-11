# Azure Functions Auth Level - Vysvetlenie
# Azure Functions Auth Level - Explanation

## Čo je auth_level? / What is auth_level?

`auth_level` v Azure Functions určuje, aká autentifikácia je potrebná na volanie HTTP endpointu.

`auth_level` in Azure Functions determines what authentication is required to call an HTTP endpoint.

---

## Typy auth_level / Auth Level Types

### 1. **ANONYMOUS** (Anonymný)
- **Bezpečnosť:** Žiadna autentifikácia
- **Použitie:** Ktokoľvek môže volať endpoint bez akýchkoľvek kľúčov
- **Príklad volania:**
  ```bash
  curl https://your-function.azurewebsites.net/api/endpoint
  ```
- **Kedy použiť:**
  - Verejné API endpointy
  - Testovacie endpointy
  - Endpointy, ktoré majú vlastnú autentifikáciu (napr. v aplikácii)

### 2. **FUNCTION** (Function Key)
- **Bezpečnosť:** Vyžaduje sa function key
- **Použitie:** Endpoint môže volať len ten, kto má function key
- **Príklad volania:**
  ```bash
  # S function key v URL
  curl https://your-function.azurewebsites.net/api/endpoint?code=YOUR_FUNCTION_KEY
  
  # Alebo v headeri
  curl -H "x-functions-key: YOUR_FUNCTION_KEY" https://your-function.azurewebsites.net/api/endpoint
  ```
- **Kedy použiť:**
  - Interné API endpointy
  - Endpointy, ktoré by nemali byť verejne dostupné
  - Produkčné endpointy

### 3. **ADMIN** (Master Key)
- **Bezpečnosť:** Vyžaduje sa master key (najvyššia úroveň)
- **Použitie:** Len pre administrátorské operácie
- **Kedy použiť:**
  - Administrátorské funkcie
  - Veľmi citlivé operácie

---

## Váš prípad / Your Case

### AuthenticateCard - ANONYMOUS
```python
@bp.route(route="authenticatecard", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
```

**Prečo som to zmenil:**
- Pôvodne som to mal bez `auth_level` (default = FUNCTION)
- Endpoint vracal 401 (Unauthorized), lebo chýbal function key
- Zmenil som na ANONYMOUS pre **testovanie**
- Teraz funguje bez function key

**Bezpečnosť:**
- ✅ Pre **testovacie prostredie** je to OK
- ⚠️ Pre **produkciu** by to malo byť `FUNCTION` pre lepšiu bezpečnosť
- Autentifikácia sa deje v aplikácii (kontrola karty v databáze), takže nie je úplne otvorené

### Iné funkcie v projekte / Other Functions in Project

**ANONYMOUS (verejné):**
- `InfoStatus` - GET endpoint, verejné informácie
- `ReadStatus` - GET endpoint, verejné informácie  
- `GetInfoGitter` - GET endpoint, verejné informácie
- `TestFunction` - testovací endpoint

**FUNCTION (chránené):**
- `ChangeStatus` - POST, mení stav (citlivé)
- `KovaciLinkaScan` - POST, skenovanie (citlivé)
- `KovaciLinkaCheck` - POST, kontrola (citlivé)
- `ProtocolPartInsert` - POST, vkladanie protokolov (citlivé)

---

## Porovnanie / Comparison

| Auth Level | Bezpečnosť | Príklad použitia | Volanie |
|------------|------------|------------------|---------|
| **ANONYMOUS** | Nízka | Verejné API, testovanie | `curl https://.../api/endpoint` |
| **FUNCTION** | Stredná | Interné API | `curl https://.../api/endpoint?code=KEY` |
| **ADMIN** | Vysoká | Admin funkcie | `curl https://.../api/endpoint?code=MASTER_KEY` |

---

## Pre AuthenticateCard / For AuthenticateCard

### Aktuálne nastavenie (TEST):
```python
auth_level=func.AuthLevel.ANONYMOUS
```

**Výhody:**
- ✅ Jednoduché testovanie (bez function key)
- ✅ Frontend môže volať bez špeciálnych nastavení
- ✅ Rýchlejšie vývoj a testovanie

**Nevýhody:**
- ⚠️ Menej bezpečné (každý môže volať endpoint)
- ⚠️ Môže byť zneužité (DDoS, spam)

### Pre produkciu by malo byť:
```python
auth_level=func.AuthLevel.FUNCTION
```

**Výhody:**
- ✅ Bezpečnejšie (len s function key)
- ✅ Ochrana pred neoprávneným prístupom

**Nevýhody:**
- ⚠️ Frontend musí posielať function key
- ⚠️ Function key musí byť v environment variables

---

## Ako to funguje v praxi / How it works in practice

### S ANONYMOUS:
```javascript
// Frontend môže volať priamo
fetch('/api/auth/card', {
  method: 'POST',
  body: JSON.stringify({ card_id: '...' })
})
```

### S FUNCTION:
```javascript
// Frontend musí poslať function key
fetch('/api/auth/card?code=FUNCTION_KEY', {
  method: 'POST',
  body: JSON.stringify({ card_id: '...' })
})

// Alebo v headeri (lepšie)
fetch('/api/auth/card', {
  method: 'POST',
  headers: {
    'x-functions-key': 'FUNCTION_KEY'
  },
  body: JSON.stringify({ card_id: '...' })
})
```

---

## Odporúčanie / Recommendation

**Pre testovacie prostredie (TraceabilityTestFunctions5):**
- ✅ ANONYMOUS je OK (jednoduchšie testovanie)

**Pre produkčné prostredie:**
- ✅ FUNCTION (bezpečnejšie)
- Function key sa uloží do environment variables
- Frontend ho pošle v headeri alebo URL

---

## Zhrnutie / Summary

**ANONYMOUS** = Ktokoľvek môže volať bez kľúča (menej bezpečné, jednoduchšie)
**FUNCTION** = Potrebný function key (bezpečnejšie, ale komplikovanejšie)

V našom prípade som zmenil na ANONYMOUS pre testovanie, ale pre produkciu by to malo byť FUNCTION.

