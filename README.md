# Plateforme de surveillance IoT

Application de démonstration composée d'une API FastAPI, d'un simulateur de 500 mesures, d'un worker d'alertes et d'un tableau de bord Streamlit. Redis est le stockage central et le bus de télémétrie.

## Prérequis

- Python 3.9 ou plus récent
- Docker avec le plugin Docker Compose

## Installation et démarrage

Depuis le dossier du projet :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
docker compose up -d redis
```

Ouvrir trois terminaux, activer l'environnement virtuel dans chacun, puis démarrer les processus :

```bash
uvicorn main:app --reload
```

```bash
python alert_worker.py
```

```bash
streamlit run app.py
```

L'API est disponible à `http://localhost:8000` et le tableau à `http://localhost:8501`. Le simulateur envoie ensuite 500 POST :

```bash
python simulator.py
```

Il est aussi possible d'ajuster `API_URL` et `REDIS_URL` via les variables d'environnement.

## Détection d'anomalies

Le simulateur injecte exactement 10 anomalies dans 500 envois : 4 interruptions, 4 surchauffes et 2 températures hors plage physique. Le worker applique une seule catégorie par mesure, dans l'ordre suivant : valeur invalide, équipement hors ligne, température supérieure à 75 °C.

## Données Redis

- `device:{device_id}` : hash de l'état courant, mis à jour à chaque ingestion.
- `telemetry:stream` : Stream Redis auquel chaque mesure est ajoutée avec `XADD`.
- `metrics:count` : compteur incrémenté dans la même transaction Redis que le hash et l'ajout au Stream.
- `alert:{stream_id}` : valeur JSON de l'alerte, expirant après 24 heures.
- `alerts:recent` : sorted set des identifiants d'alertes; le tableau retire les références dont la clé TTL a expiré.
- `alert_worker:last_id` : dernier événement traité, utilisé pour reprendre la consommation après redémarrage.

Pour arrêter Redis : `docker compose down`. Les données restent dans le volume nommé; `docker compose down -v` les supprime.