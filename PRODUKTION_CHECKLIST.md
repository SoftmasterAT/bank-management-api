# 🚀 Production Checklist: Softmaster Bank-Management API

Diese Checkliste stellt sicher, dass die API stabil, sicher und performant in der Cloud (Azure) läuft.

## 🔐 Security (JWT & Auth)
- [x] **Passwort-Hashing**: Alle Passwörter sind mit `bcrypt` verschlüsselt.
- [x] **JWT-Security**: Schreibende Endpunkte sind durch Inhaber-Tokens geschützt.
- [x] **RBAC**: Rollenbasierte Zugriffskontrolle (`admin` vs. `viewer`) ist aktiv.
- [ ] **Secret Management**: Alle Keys müssen in Azure KeyVault oder App Settings liegen (nicht im Code).

## 📊 Monitoring & Logging
- [x] **Zentrales Logging**: Alle Events werden in `logs/bank_api.log` gespeichert.
- [x] **Latency Tracking**: Middleware misst die Antwortzeit jedes Requests.
- [ ] **Health Checks**: Dedizierter `/health` Endpunkt für das Azure-Monitoring (geplant).

## 🗄️ Datenhaltung (SQL Migration)
- [ ] **SQLite Provider**: Migration von JSON zu relationaler Datenbank.
- [ ] **Schema Migration**: Automatisierte Erstellung der Tabellen beim Start.
- [ ] **Data Integrity**: Nutzung von `UNIQUE` Constraints für Inhabernamen auf Datenbankebene.

## 🐳 Docker & Cloud (Azure)
- [x] **Dockerignore**: Sensible Daten wie `.env` und `logs/` werden nicht ins Image kopiert.
- [x] **CI/CD Pipeline**: Automatisierte Tests (30/30) vor jedem Deployment.
- [ ] **Always On**: (Optional) Upgrade des Azure Plans zur Vermeidung von Kaltstarts.
