import unittest
import random
from fastapi.testclient import TestClient
from api import app

class TestBankAPI(unittest.TestCase):
    def setUp(self):
        from api import stelle_datenbank_sicher
        stelle_datenbank_sicher()
        self.client = TestClient(app)
    # --- TAG: Security ---

    def get_token(self):
        """Hilfsfunktion: Holt einen frischen Token für geschützte Tests."""
        login_data = {"username": "admin", "password": "NodRex_Bank_2026"}
        response = self.client.post("/login", data=login_data) # Senden als Form-Data
        return response.json()["access_token"]
    

    # --- TAG: Allgemein ---
    def test_home(self):
        """Testet den Willkommens-Endpunkt (jetzt als HTML)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        # Prüfe, ob der Content-Type HTML ist
        self.assertIn("text/html", response.headers["content-type"])
        
        # Prüfe, ob wichtige Begriffe im HTML-Text vorkommen
        self.assertIn("Softmaster Bank-Management API", response.text)
        self.assertIn("static/sm_logo.webp", response.text)

    # --- TAG: 1. Übersicht ---
    def test_alle_konten(self):
        """
        Prüft, ob die Konktenliste (Array) zurückgegeben wird.
        """
        response = self.client.get("/konten")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    # --- TAG: 2. Transaktionen ---
    def test_einzahlen_erfolgreich(self):
        """
        Testen Erfolgreiche Einzahlung
        """
        token = self.get_token() # 1. Login
        headers = {"Authorization": f"Bearer {token}"} # 2. Token in Header packen
        response = self.client.post("/transaktion/einzahlen/Tom?betrag=100", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("eingezahlt", response.json()["nachricht"].lower())

    def test_abheben_error(self):
        """
        Testet Fehler bei zu hohen Betrag
        """
        token = self.get_token() # 1. Login
        headers = {"Authorization": f"Bearer {token}"} # 2. Token in Header packen
        response = self.client.post("/transaktion/abheben/Tom?betrag=100000", headers=headers)
        self.assertEqual(response.status_code, 400)

    

    # --- TAG: 3. Verwaltung ---
    def test_suche_ergebnis(self):
        """
        Testet die Suchfunktion mit einem bekannten Namen (z.B. Tom).
        """
        # 'Tom' sollte in Datenbank existieren
        response = self.client.get("/suche?name=Tom")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        if isinstance(data, list):
            self.assertTrue(any("Tom" in k["inhaber"] for k in data))
    
    def test_konto_erstellen(self):
        token = self.get_token() # 1. Login
        headers = {"Authorization": f"Bearer {token}"} # 2. Token in Header packen
        name = "Softmaster"
        payload = {
            "name":name,
            "typ": "giro",
            "start_saldo": 1000,
            "extra": 200
        }
        response = self.client.post("/konten/erstellen", json=payload, headers=headers)

        # Falls der Name bereits existiert (400 Bad Request mit Vorschlägen)
        if response.status_code == 400:
            error_detail = response.json()["detail"]
            if "Vorschläge:" in response.json()["detail"]:
                print(f"⚠️ Name '{name}' belegt. Teste automatischen Vorschlag...")
                
                # Extrahiere Vorschläge aus dem String "Name existiert bereits. Vorschläge: Name1, Name2, Name3"

                suggestions_part = error_detail.split("Vorschläge: ")[1]
                suggestions_list = [s.strip() for s in suggestions_part.split(",")]
                payload["name"] = suggestions_list[0] # Pick the first one
                response = self.client.post("/konten/erstellen", json=payload, headers=headers)
                print(f"✅ Zweiter Versuch erfolgreich mit: {payload['name']}")
        if response.status_code == 500:
            print(f"🔥 API Error Detail: {response.json().get('detail')}")
        # Finaler Check: Jetzt muss es Status 200 sein    
        self.assertEqual(response.status_code, 200)
        self.assertIn("erstellt", response.json().get("details", "").lower())

    def test_konto_erstellen_error(self):
        """
        Testet, ob ungültige Kontotypen angelehnt werden (400 Bad Request).
        """
        token = self.get_token() # 1. Login
        headers = {"Authorization": f"Bearer {token}"} # 2. Token in Header packen
        payload = {
            "name": "TestUser" + str(random.randint(100, 999)), # Verhindert Namenskollision,
            "typ": "falscher_typ",
            "start_saldo": 100,
            "extra": 0
        }
        response = self.client.post("/konten/erstellen", json=payload, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ungültiger Kontotyp", response.json()["detail"])

    # --- TAG: 4. Zinsen ---
    def test_zinsen_gutschreiben(self):
        """
        Testet, ob auf Sparkonto Zinsen richtig gutgeschrieben wird
        """
        token = self.get_token() # 1. Login
        headers = {"Authorization": f"Bearer {token}"} # 2. Token in Header packen
        response = self.client.post("/zinsen/gutschreiben/Jim", headers=headers)
        if response.status_code == 200:
            self.assertIn("Erfolg", response.json()["status"])
        else:
            self.assertEqual(response.status_code, 400)
    

    def test_zinsen_simulation_spar(self):
        """
        testet, Zinsem Simulation mit 'jim' (Sparkonto)
        """
        response = self.client.post("/zinsen/simulieren/Jim?sonderzins=5.0")
        if response.status_code == 200:
            self.assertIn("Simulation", response.json()["status"])
        else:
            self.assertEqual(response.status_code, 400)


    def test_zinsen_simulation_error(self):
        """
        Prüft, ob Simulation bei ungültigen Werten (z.B. Zins <= 0) blokiert
        """
        response = self.client.post("/zinsen/simulieren/Tom?sonderzins=-5.0")
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    unittest.main()