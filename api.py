
from fastapi import FastAPI, HTTPException, Query, Response, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from auth_handler import create_access_token, verify_password, USERS_DB, SECRET_KEY, ALGORITHM
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import os
from pathlib import Path
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel
# from json_storage import JSONStorage # - FOR OLD VERSION
from main import initialisiere_standard_konten, filtere_konten
from sparkonto import Sparkonto
from girokonto import Girokonto
import time
from logger_config import logger
import inspect
from storage_factory import get_storage


# Globaler Storage-Provider (später einfach durch SQLiteStorage ersetzbar)
# storage = JSONStorage("konten.json") # - FOR OLD VERSION
# NEW:
storage = get_storage()
current_mode = "SQLite (Relational)" if os.getenv("STORAGE_TYPE") == "sql" else "JSON (Dateibasiert)"

# Definiert, wo die API nach dem TOken sucht (im Endpunkt /Login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def stelle_datenbank_sicher():
    """Prüft, ob Daten vorhanden sind, sonst Initialisierung mit Standard-Konten."""
    try:
        aktuelle_konten = storage.laden()
        if not aktuelle_konten:
            logger.info("Speicher ist leer. Initialisiere Standard-Konten...")
            standard = initialisiere_standard_konten()
            # Hier greift jetzt deine neue SQL-Speichermethode!
            storage.speichern(standard)
            logger.info(f"Erfolgreich {len(standard)} Konten initialisiert.")
    except Exception as e:
        logger.error(f"Fehler bei der Datenbank-Sicherstellung: {e}")

# Beim Start der API aufrufen
stelle_datenbank_sicher()

# Hilfsfunktion zur Token-Validierung und Rollen-Prüfung
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Validiert den bereitgestellten JWT-Token und extrahiert die Benutzerinformationen.

    Diese Funktion dient als zentrale Dependency für geschützte Endpunkte. Sie prüft 
    die Signatur des Tokens, das Ablaufdatum sowie das Vorhandensein der Benutzerrolle.

    Args:
        token (str): Der im Authorization-Header übermittelte JWT-Token. 
            Wird automatisch durch FastAPI aus dem OAuth2-Schema extrahiert.

    Raises:
        HTTPException (401): Wird ausgelöst, wenn der Token ungültig, abgelaufen 
            oder die Benutzeridentität (sub) nicht enthalten ist.

    Returns:
        dict: Ein Dictionary mit den Benutzerdaten (z. B. {"username": "admin", "role": "admin"}).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token konnte nicht validiert werden oder ist abgelaufen.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Dekodieren des Tokens mit dem Secret Key
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        
        if username is None or role is None:
            raise credentials_exception
            
        return {"username": username, "role": role}
        
    except JWTError:
        # Tritt auf bei falscher Signatur oder abgelaufenem Token
        raise credentials_exception


description_text = f"""
### 🚀 Professionelle REST-Schnittstelle zur Bankverwaltung
Dieses System ermöglicht die sichere Verwaltung von Bankkonten basierend auf modernsten Sicherheitsstandards (JWT).

### 💾 Status: {current_mode} Aktiv
    Dieses System läuft aktuell im **{current_mode}** Modus. 
    
    *Hinweis: Der Speichermodus wird beim Start über Umgebungsvariablen festgelegt.*
---

### 🔑 Test-Zugangsdaten (Demo-Umgebung)
Nutzen Sie den **Authorize**-Button oben rechts (Schloss-Symbol), um sich anzumelden:

| Rolle | Username | Passwort | Berechtigung |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | *Intern* | Voller Zugriff & Kontoverwaltung |
| **Demo-User** | `DEMO_USER` | `Demo_Softmaster_API_2026` | Nur Transaktionen (Einzahlen/Abheben) |

---

### 🔒 Berechtigungsstufen (RBAC)
- **Öffentlich (Kein Login):** Login-Vorgang (`POST/login`), Abrufen der Kontenübersicht (`GET/konten`) und Zins-Simulationen.
- **Eingeschränkt (Demo-User):** Durchführung von Transaktionen (Einzahlen/Abheben) auf bestehenden Konten.
- **Vollzugriff (Admin):** Erstellen neuer Konten sowie administrative Verwaltungsaufgaben.

*Hinweis: Die Zins-Simulation verändert den dauerhaften Kontostand nicht und ist daher öffentlich zugänglich.*
"""

app = FastAPI(
    title="🏦 Softmaster Bank-Management API",
    description=inspect.cleandoc(description_text), # Entfernt Einrückungs-Fehler
    version="1.4.0"
)

# --- SCHEMATA ---
class KontoErstellenSchema(BaseModel):
    """Schema für die Erstellung eines neuen Kontos."""
    name: str
    typ: str  # "giro" oder "spar"
    start_saldo: float
    extra: float

class TransaktionErgebnis(BaseModel):
    """Rückgabe-Schema für erfolgreiche Transaktionen."""
    nachricht: str
    inhaber: str
    neuer_stand: float

# --- ENDPUNKTE ---

@app.get("/", tags=["Allgemein"], response_class=HTMLResponse)
def home():
    """
    **Willkommens-Endpunkt**  
    Landing-Page mit Firmenlogo und Link zur Dokumentation.
    """
    return """
    <!DOCTYPE html>
    <html lang="de">
        <head>
            <meta charset="UTF-8">
            <title>Softmaster Bank API</title>
            <link rel="icon" href="/favicon.ico" type="image/x-icon">
            <style>
                body { 
                    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
                    text-align: center; 
                    padding-top: 80px; 
                    background-color: #0f111a; /* Sehr dunkles Blau-Schwarz */
                    color: #e0e0e0;
                    margin: 0;
                }
                .container { 
                    background: #1c1f2b; /* Dunkles Anthrazit-Blau */
                    padding: 50px; 
                    border-radius: 20px; 
                    display: inline-block; 
                    box-shadow: 0 15px 35px rgba(0,0,0,0.5); 
                    max-width: 550px;
                    border-top: 4px solid #d32f2f; /* Roter Akzent-Balken oben */
                }
                .logo { 
                    max-width: 180px; 
                    height: auto; 
                    margin-bottom: 30px; 
                    display: block;
                    margin-left: auto;
                    margin-right: auto;
                    filter: drop-shadow(0 0 10px rgba(255,255,255,0.1)); /* Hebt Silber leicht hervor */
                }
                h1 { color: #ffffff; margin-bottom: 15px; font-weight: 300; letter-spacing: 1px; }
                p { color: #b0b3b8; font-size: 1.1em; line-height: 1.6; }
                .btn { 
                    display: inline-block;
                    margin-top: 30px;
                    padding: 14px 28px;
                    background: #d32f2f; /* Dein Rot-Ton */
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 12px rgba(211, 47, 47, 0.3);
                }
                .btn:hover { 
                    background: #b71c1c; 
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(211, 47, 47, 0.4);
                }
                strong { color: #28a745; }
                .security-badge {
                    margin-top: 15px;
                    font-size: 0.9em;
                    color: #f1c40f; /* Gold für Sicherheit */
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <img src="/static/sm_logo.webp" alt="Softmaster Logo" class="logo">
                <h1>Softmaster Bank-Management API</h1>
                <p>Status: <span style="color: #28a745;">● Online</span></p>
                <div class="security-badge">
                    <span>🔒</span> Gesichert mit JWT-Authentifizierung
                </div>
                <p>Nutzen Sie die Dokumentation, um sich zu authentifizieren und Endpunkte zu testen:</p>
                <a href="/docs" class="btn">Zur Swagger Dokumentation</a>
            </div>
        </body>
    </html>
    """

@app.get("/system/info", tags=["System"])
def get_system_info(current_user: dict = Depends(get_current_user)):
    """Gibt Informationen über die aktuelle Speicher-Architektur zurück."""
    return {
        "storage_type": type(storage).__name__,
        "database_connected": True,
        "environment": os.getenv("AZURE_FUNCTIONS_ENVIRONMENT", "Development"),
        "version": "1.6.0"
    }


# --- SECURITY CONFIG ---

@app.post("/login", tags=["Security"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    **Login für API-Zugang**  
    Authentifiziert einen Benutzer und gibt einen JWT-Token zurück, der für den Zugriff 
    auf geschützte (schreibende) Operationen benötigt wird.

    Args:
        form_data (OAuth2PasswordRequestForm): Enthält die vom Benutzer gesendeten 
            Anmeldedaten (Username und Passwort) aus dem HTTP-Form-Body.

    Raises:
        HTTPException: Wird geworfen (401 Unauthorized), wenn der Username falsch ist 
            oder das Passwort nicht mit dem gespeicherten Hash übereinstimmt.

    Returns:
        dict: Ein Dictionary, das den 'access_token' und den 'token_type' (Bearer) enthält.
    """
    # 1. Prüfen, ob der User in unserer kleinen Datenbank existiert
    user_data = USERS_DB.get(form_data.username)

    # 2. Passwort validieren
    if not user_data or not verify_password(form_data.password, user_data["hash"]):
        logger.warning(f"Login-Fehlversuch: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Anmeldedaten",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Token erstellen und Rolle ("role") mit in die Payload packen
    access_token = create_access_token(
        data={"sub": form_data.username, "role": user_data["role"]}
    )
    logger.info(f"Erfolgreicher Login: {form_data.username} (Rolle: {user_data['role']})")
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_favicon_url="/favicon.ico" # Hier verweisen wir auf deinen Endpunkt
    )

@app.get("/konten", tags=["1. Übersicht"])
def alle_konten():
    """
    **Alle Konten auflisten**  
    Gibt alle Konten dynamisch über den Storage-Provider zurück.
    """
    try:
        konten = storage.laden()
        return [k.to_dict() for k in konten] 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transaktion/einzahlen/{name}", response_model=TransaktionErgebnis, tags=["2. Transaktionen"])
def einzahlen_api(
    name: str, 
    betrag: float = Query(description="Betrag, der eingezahlt werden soll"),
    current_user: dict = Depends(get_current_user)
):
    """
    **Einzahlung vornehmen**  
    Erlaubt für Administratoren und Demo-Benutzer.
    - Prüft die Existenz des Kontos.
    - Aktualisiert den Kontostand unter Nutzung der Klassen-Logik.
    - Speichert die Änderungen dauerhaft in der JSON-Datenbank.
    """
    # Security Check
    if current_user["role"] not in ["admin", "viewer"]:
        raise HTTPException(status_code=403, detail="Keine Berechtigung für Transaktionen.")
    
    try:
        # 1. Daten laden
        # konten = storage.laden() - nicht mehr notwendig

        # 2. Konto suchen (DIESE Zeile wirft den ValueError, wenn nichts gefunden wird)
        k = storage.konto_holen(name)

        # 3. Logik ausführen
        nachricht = k.einzahlen(betrag)
        
        # 4. Speichern
        storage.update_kontostand(k) # storage.speichern(konten) - alte version
        
        logger.info(f"Transaktion: {current_user['username']} hat {betrag} EUR auf {name} eingezahlt.")
        return {
            "nachricht": nachricht, 
            "inhaber": k.inhaber,
            "neuer_stand": k.kontostand
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"⚠️ {str(e)}")
        
    except Exception as e:
        # Nur echte Systemfehler landen hier (z.B. Festplatte voll beim Speichern)
        raise HTTPException(status_code=500, detail=f"❌ Systemfehler: {str(e)}")

@app.post("/transaktion/abheben/{name}", response_model=TransaktionErgebnis, tags=["2. Transaktionen"])
def abheben_api(
    name: str, 
    betrag: float = Query(description="Betrag, der abgehoben werden soll"),
    current_user: dict = Depends(get_current_user)
):
    """
    **Geld abheben**  
    Nutzt die Dispo-Logik des Girokontos oder die Sperre des Sparkontos.
    """
    # Security Check
    if current_user["role"] not in ["admin", "viewer"]:
        raise HTTPException(status_code=403, detail="Keine Berechtigung für Transaktionen.")
    
    try:
        # konten = storage.laden()  - nicht mehr notwendig
        k = storage.konto_holen(name)
        # Hier greift eine Logik aus girokonto.py / sparkonto.py
        nachricht = k.abheben(betrag) 
        storage.update_kontostand(k) # storage.speichern(konten) - alte version
        
        logger.info(f"Transaktion: {current_user['username']} hat {betrag} EUR von {name} abgehoben.")
        return {
            "nachricht": nachricht,
            "inhaber": k.inhaber,
            "neuer_stand": k.kontostand
        }
    except ValueError as e:
        # Hier fangen wir z.B. "Dispo überschritten" ab
        raise HTTPException(status_code=400, detail=f"⚠️ {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="❌ Interner Serverfehler")
    

@app.get("/suche", tags=["3. Verwaltung"])
def api_suchen(name: str):
    """
    Sucht alle Konten, die den Suchbegriff im Namen enthalten.
    Gibt eine Liste der Treffer zurück.

    Args:
        name (str): Der Name des gesuchten Kontoinhabers.

    Returns:
        treffer: Gibt die Liste der Treffer zurück.
    """
    konten = storage.laden()
    treffer = filtere_konten(konten, name)
    if not treffer:
        return {"nachricht": "Keine Treffer", "ergebnisse": []}
    return treffer

# --- GESCHÜTZTER ENDPUNKT ---
@app.post("/konten/erstellen", tags=["3. Verwaltung"])
def konto_erstellen(daten: KontoErstellenSchema, current_user: dict = Depends(get_current_user)):
    """
    **Neues Konto erstellen**  
    Erzeugt ein neues Giro- oder Sparkonto-Objekt und speichert es in der Datenbank.
    Erfordert einen gültigen Token.
    """
    # --- ROLLEN-CHECK ---
    if current_user["role"] != "admin":
        logger.warning(f"Zugriff verweigert: User {current_user['username']} hat keine Admin-Rechte.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="⚠️ Zugriff verweigert: Nur Administratoren dürfen Konten erstellen."
        )
    try:
        typ = daten.typ.lower().strip()
        
        # Validierung und Erstellung (wie im interaktiven Menü)
        if typ == "giro":
            neues_k = Girokonto(daten.name, daten.start_saldo, daten.extra)
        elif typ == "spar":
            neues_k = Sparkonto(daten.name, daten.start_saldo, daten.extra)
        else:
            raise ValueError("⚠️ Ungültiger Kontotyp! Erlaubt sind 'giro' oder 'spar'.")
        
        # Hier wird automatisch auf Duplikate geprüf
        storage.konto_hinzufuegen(neues_k)
        
        return {"status": "✅ Erfolg", "admin": current_user["username"], "details": f"Konto für {daten.name} ({typ}) erstellt."}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"⚠️ {str(e)}")
    except Exception as e:
        print(f"DEBUG-ERROR: {type(e).__name__}: {str(e)}") 
        raise HTTPException(status_code=500, detail=f"❌ Systemfehler: {str(e)}")


@app.post("/zinsen/gutschreiben/{name}", tags=["4. Zinsen"])
def zinsen_gutschreiben(name: str, current_user: dict = Depends(get_current_user)):
    """
    **Zinsen fest verbuchen**  
    Berechnet die Zinsen für ein Sparkonto und aktualisiert den Kontostand dauerhaft.
    """
    # Security Check
    if current_user["role"] != "admin":
        logger.warning(f"Sicherheitswarnung: User {current_user['username']} (Rolle: {current_user['role']}) versuchte Zinsgutschrift für {name}.")
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Zinsen gutschreiben.")
    
    try:
        k = storage.konto_holen(name)
        
        # Wir prüfen, ob das Objekt die Methode 'zinsen_berechnen' besitzt
        if not hasattr(k, 'zinsen_berechnen'):
            raise ValueError(f"⚠️ Konto '{name}' ist kein Sparkonto und erhält keine Zinsen.")
            
        nachricht = k.zinsen_berechnen()
        storage.update_kontostand(k) # storage.speichern(konten) - alte version

        logger.info(f"Zinsgutschrift erfolgreich: Admin '{current_user['username']}' hat Zinsen für Konto '{name}' verbucht. {nachricht}")
        return {"status": "✅ Erfolg", "details": nachricht, "neuer_stand": k.kontostand}

    except ValueError as e:
        logger.error(f"Fehler bei Zinsgutschrift für {name}: {e}")
        raise HTTPException(status_code=400, detail=f"⚠️ {str(e)}")



@app.post("/zinsen/simulieren/{name}", tags=["4. Zinsen"])
def zinsen_simulieren(name: str, sonderzins: float = Query(..., gt=0)):
    """
    **Sonderzins-Simulation**  
    Berechnet temporär Zinsen mit einem abweichenden Zinssatz (keine dauerhafte Änderung).
    """
    try:
        k = storage.konto_holen(name)
        
        if not hasattr(k, 'zinsen_berechnen_mit'):
            raise ValueError(f"⚠️ Simulation für '{name}' nicht verfügbar (kein Sparkonto).")
            
        ergebnis = k.zinsen_berechnen_mit(sonderzins)
        return {"status": "✅ Simulation", "ergebnis": ergebnis}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"⚠️ {str(e)}")
    
# --- STATISCHE DATEIEN & BROWSER-FIXES ---

@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools_json():
    """Unterdrückt 404-Fehler durch Chrome DevTools Anfragen."""
    return Response(content="", media_type="application/json")

# Pfad zum Icon
BASE_DIR = Path(__file__).resolve().parent
FAVICON_PATH = BASE_DIR / "static" / "favicon.ico"

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Liefert das Favicon aus oder sendet eine leere Antwort, um 404 zu vermeiden."""
    if os.path.exists(FAVICON_PATH):
        return FileResponse(FAVICON_PATH)
    return Response(content="", media_type="image/x-icon")

# Mounten für alle anderen statischen Dateien (z.B. Bilder für die Doku)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def log_requests(request, call_next):
   start_time = time.time()

   # Die Anfrage wird verarbeitet
   response = await call_next(request)

   duration = time.time() - start_time

   # Monitoring Log-Eintrag
   logger.info(
       f"Inbound: {request.method} {request.url.path} | "
       f"Status: {response.status_code} | "
       f"Duration: {duration:.4f}s"
   ) 

   return response
