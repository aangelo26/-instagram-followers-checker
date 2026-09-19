import os
import re
import csv
import json
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_FOLLOWERS = os.path.join(CARTELLA, "followers_1.html")
FILE_FOLLOWING = os.path.join(CARTELLA, "following.html")
FILE_CSV = os.path.join(CARTELLA, "gestione_profili.csv")

def estrai_utenti(file_path):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, "r", encoding="utf-8") as f:
        contenuto = f.read()
    pattern = r'href=["\']https://www\.instagram\.com/(?:_u/)?([a-zA-Z0-9._]+)["\']'
    return set(re.findall(pattern, contenuto))

def carica_dati():
    dati = {}
    csv_esiste = os.path.exists(FILE_CSV)

    if csv_esiste:
        with open(FILE_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dati[row["Username"]] = row

    followers = estrai_utenti(FILE_FOLLOWERS)
    following = estrai_utenti(FILE_FOLLOWING)
    non_ti_seguono = following - followers


    for u in non_ti_seguono:
        if u not in dati:
            e_nuovo = "SI" if csv_esiste else "NO"
            dati[u] = {"Username": u, "Stato": "DA_GESTIRE", "Nuovo": e_nuovo, "Note": ""}

    salva_dati(dati)
    return dati

def salva_dati(dati):
    fieldnames = ["Username", "Stato", "Nuovo", "Note"]
    with open(FILE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for u in sorted(dati.keys()):
            # Fallback
            if "Nuovo" not in dati[u]:
                dati[u]["Nuovo"] = "NO"
            writer.writerow(dati[u])

def reset_totale():
    followers = estrai_utenti(FILE_FOLLOWERS)
    following = estrai_utenti(FILE_FOLLOWING)
    non_ti_seguono = following - followers
    dati = {u: {"Username": u, "Stato": "DA_GESTIRE", "Nuovo": "NO", "Note": ""} for u in non_ti_seguono}
    salva_dati(dati)
    return dati

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Instagram Unfollow Manager</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; margin: 0; padding: 25px; }
  .container { max-width: 750px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
  h1 { font-size: 22px; margin: 0; color: #1c1e21; }
  .counters { color: #65676b; font-size: 14px; margin-bottom: 20px; }
  .user-card { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid #e4e6eb; }
  .user-card:last-child { border-bottom: none; }
  .user-info { display: flex; align-items: center; gap: 8px; }
  .username { font-weight: 600; color: #050505; font-size: 15px; }
  .badge-new { background: #e7f3ff; color: #1877f2; font-size: 11px; font-weight: 700; padding: 3px 7px; border-radius: 6px; border: 1px solid #bedbff; }
  .actions { display: flex; gap: 8px; }
  button, a.btn { border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; }
  .btn-open { background: #e4e6eb; color: #050505; }
  .btn-open:hover { background: #d8dadf; }
  .btn-unfollow { background: #1877f2; color: #fff; }
  .btn-unfollow:hover { background: #166fe5; }
  .btn-ignore { background: #65676b; color: #fff; }
  .btn-ignore:hover { background: #4b4d50; }
  .btn-reset { background: #e41e3f; color: #fff; font-size: 12px; padding: 6px 12px; }
  .btn-reset:hover { background: #c51633; }
  .empty-msg { text-align: center; padding: 40px 0; color: #65676b; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Controllo Profili Instagram</h1>
    <button class="btn btn-reset" onclick="confermaReset()">⚠️ Ripristina Tutto</button>
  </div>
  <div class="counters" id="stats">Caricamento...</div>
  <div id="user-list"></div>
</div>

<script>
async function caricaLista() {
  const res = await fetch('/api/utenti');
  const data = await res.json();
  const listDiv = document.getElementById('user-list');
  const statsDiv = document.getElementById('stats');

  const daGestire = data.filter(x => x.Stato === 'DA_GESTIRE');
  const nuovi = daGestire.filter(x => x.Nuovo === 'SI').length;
  const unfollowati = data.filter(x => x.Stato === 'UNFOLLOWATO').length;
  const ignorati = data.filter(x => x.Stato === 'IGNORA').length;

  statsDiv.innerText = `Da gestire: ${daGestire.length} (Nuovi: ${nuovi}) | Unfollowati: ${unfollowati} | Ignorati: ${ignorati}`;

  if (daGestire.length === 0) {
    listDiv.innerHTML = '<div class="empty-msg">🎉 Nessun profilo da verificare rimasto!</div>';
    return;
  }

  listDiv.innerHTML = daGestire.map(u => `
    <div class="user-card" id="card-${u.Username}">
      <div class="user-info">
        <span class="username">@${u.Username}</span>
        ${u.Nuovo === 'SI' ? '<span class="badge-new">🆕 NEW</span>' : ''}
      </div>
      <div class="actions">
        <a class="btn btn-open" href="https://www.instagram.com/${u.Username}/" target="_blank">🌐 Apri</a>
        <button class="btn btn-unfollow" onclick="aggiorna('${u.Username}', 'UNFOLLOWATO')">✅ Fatto</button>
        <button class="btn btn-ignore" onclick="aggiorna('${u.Username}', 'IGNORA')">🚫 Ignora</button>
      </div>
    </div>
  `).join('');
}

async function aggiorna(username, nuovoStato) {
  await fetch('/api/stato', {
    method: 'POST',
    body: JSON.stringify({ username: username, stato: nuovoStato })
  });
  caricaLista();
}

async function confermaReset() {
  if (confirm("Vuoi davvero azzerare il CSV e riportare tutti i profili su 'DA_GESTIRE'?")) {
    await fetch('/api/reset', { method: 'POST' });
    caricaLista();
  }
}

caricaLista();
</script>
</body>
</html>
"""

class WebHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/utenti":
            dati = carica_dati()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(list(dati.values())).encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/stato":
            length = int(self.headers.get('content-length', 0))
            payload = json.loads(self.rfile.read(length))
            user = payload.get("username")
            stato = payload.get("stato")

            dati = carica_dati()
            if user in dati:
                dati[user]["Stato"] = stato
                salva_dati(dati)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        elif self.path == "/api/reset":
            reset_totale()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "reset_completato"}')

def run():
    porto = 8080
    server = HTTPServer(("127.0.0.1", porto), WebHandler)
    url = f"http://127.0.0.1:{porto}"
    print(f"Interfaccia attiva su {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nChiusura programma...")

if __name__ == "__main__":
    run()