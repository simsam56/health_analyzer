# ChatGPT Atlas ↔ Bord (planning pilotable par IA)

## Ce qui est possible

Oui: ChatGPT Atlas peut ajouter/éditer des tâches dans Bord **si** on connecte un outil côté ChatGPT vers l'API planner.

Dans Bord, les endpoints utiles sont:

- `GET /api/planner/agent/capabilities`
- `POST /api/planner/tasks/batch`
- `POST /api/planner/tasks`
- `PATCH /api/planner/tasks/{id}`
- `DELETE /api/planner/tasks/{id}`

Tous les endpoints d'écriture exigent le header:

- `X-Bord-Token: <token>`

## Limite importante (OpenAI docs)

- ChatGPT custom apps / MCP se connectent à des **serveurs distants**.
- Les MCP **locaux** (`localhost`) ne sont pas directement supportés.
- Le mode `Deep Research` peut lire des apps, mais pas exécuter les actions d'écriture comme un chat normal connecté à l'app.

Conséquence: pour piloter ton planning local depuis Atlas, il faut exposer ton serveur local via un tunnel sécurisé (ou héberger une passerelle distante).

## Setup recommandé (rapide)

1. Lancer Bord:

```bash
cd ~/Documents/health_analyzer
BORD_API_TOKEN="ton-token-fort" python3 main.py --garmin --days 90 --serve --serve-port 8791
```

2. Exposer `8791` avec un tunnel HTTPS (Cloudflare Tunnel ou ngrok).

3. Dans ChatGPT Atlas / custom app, connecter l'outil HTTP vers l'URL publique du tunnel.

4. Utiliser le tool batch:

`POST /api/planner/tasks/batch`

Payload exemple:

```json
{
  "defaults": { "sync_apple": true },
  "tasks": [
    {
      "title": "Run endurance 8km",
      "type": "cardio",
      "week_ref": "next_week",
      "weekday": "mardi",
      "time": "07:00",
      "duration_min": 55
    },
    {
      "title": "Session full body",
      "type": "musculation",
      "week_ref": "week_plus_2",
      "weekday": "jeudi",
      "time": "18:30",
      "duration_min": 70
    }
  ]
}
```

## Valeurs supportées par le batch

- `week_ref`: `this_week`, `next_week`, `week_plus_2`
- `weekday`: `lundi` ... `dimanche` (ou anglais)
- `type`: `cardio`, `musculation`, `mobilite`, `sport_libre`, `travail`, `apprentissage`, `relationnel`, `autre`

## Recommandation sécurité

- Utiliser un token API fort.
- Ne pas exposer le tunnel sans token.
- Faire tourner le tunnel uniquement quand tu en as besoin.
