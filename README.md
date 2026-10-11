# Nexora Operations — Django

Panou intern conectat la backendul Node/Express Nexora. Datele marketplace, ticketele și retragerile rămân în backendul Node; Django gestionează sesiunea internă și interfața.

## Pornire

Configurați variabilele din `.env.example` în `.env`, apoi:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Deschideți `/admin/login/` și folosiți emailul/parola contului staff Nexora. Introduceți codul TOTP în câmpul 2FA dacă este activat. Conturile Django locale nu înlocuiesc autentificarea Nexora.

## Traduceri și verificări

Româna este limba implicită (`DJANGO_LANGUAGE_CODE=ro`). Meniul de limbă permite alegerea englezei; valorile trimise API-ului rămân aceleași indiferent de limbă. Șabloanele și catalogul sunt salvate în UTF-8.

Catalogul românesc se află în `locale/ro/LC_MESSAGES/django.po`. După editare, recompilați:

```powershell
.venv\Scripts\python.exe manage.py compile_catalogs
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py test accounts --settings=config.test_settings
```

`compile_catalogs` generează `django.mo` cu `polib`, inclusiv pe Windows fără GNU gettext. Dacă gettext este instalat, se poate folosi și `manage.py compilemessages -l ro`. Reporniți procesele Django după actualizarea `.mo`, deoarece traducerile sunt păstrate în memorie. La publicare, includeți atât `.po`, cât și `.mo`.

Testele folosesc SQLite în memorie și API simulat; nu modifică marketplace-ul sau soldurile din producție.

## Acces

- `admin`: dashboard, utilizatori, creare agenți, notificări, retrageri, tickete și jurnalul local al operațiunilor.
- `support_agent`, `support_manager`, `it_agent`, `logistics_agent`, `moderator`: dashboard și ticketele permise de backend pentru departamentul lor.
- `finance_agent`: dashboard și tickete; retragerile necesită departamentul `payments`.
- Call center este departamentul `call_center`. Creați un `support_agent` în acest departament.

Identitatea este verificată la fiecare cerere autentificată către admin prin `/auth/me`. Revocarea rolului, blocarea sau expirarea tokenului închid accesul; indisponibilitatea backendului produce HTTP 503. Agenții nu primesc privilegii Django superuser. Middleware-ul protejează și accesul direct prin URL.

## Fluxuri conectate

- Tickete: informații staff, statistici, filtre pe stare/departament/prioritate/agent, preluare/eliberare, răspunsuri, status și prioritate.
- Pagina Support afișează implicit toate ticketele permise contului, inclusiv cele închise sau atribuite. Filtrul „Neatribuite” se aplică numai dacă este selectat. O eroare la statistici nu ascunde lista de tickete.
- Financiar: filtrare și paginare retrageri, finalizare după confirmarea transferului, respingere prin API-ul existent.
- Admin: profiluri/securitate/moderare, notificări și creare conturi staff cu rol și departament.
- Dashboard: statistici reale și acces la module conform rolului.
- Istoric local: ultimele 100 de operațiuni confirmate prin panou, operator și oră; fără mesaje, parole sau tokenuri în jurnal.
- Câmpurile și opțiunile dropdown au culori explicite pentru temele deschisă și închisă.

## Limitele contractului backend

Contractele au fost verificate în `C:\VSCode\store\backend` pe 11 octombrie 2026. Backendul se publică separat.

1. `POST /admin/withdrawals/:id/approve` schimbă statusul în `completed`; nu execută transfer bancar. Panoul solicită confirmarea transferului efectuat separat.
2. Respingerea schimbă statusul și apoi restituie soldul prin două operațiuni MongoDB. Backendul necesită o tranzacție pentru consistență în caz de eroare între operațiuni.
3. Rutele `/admin/notifications` și `/admin/broadcast` nu au `auth`/`adminOnly` în routerul Node verificat. Django le restricționează administratorilor; API-ul public necesită aceeași protecție înainte de lansare.
4. Lista staff returnează implicit maximum 50 de tickete. Controllerul nu transmite `page`/`limit` către serviciu. Când totalul depășește lotul primit, panoul afișează limita și recomandă restrângerea filtrelor.
5. Nu există API staff global pentru comenzi, tranzacții, rambursări ale plăților, apeluri telefonice, note interne, transfer între departamente sau audit global al backendului. Call center din acest panou lucrează pe tickete; telefonia necesită integrare separată.
6. `PATCH /admin/users/:id/role` acceptă doar `user` și `admin`; modificarea rolului/departamentului unui agent existent necesită extinderea backendului. Crearea agenților este suportată.

În producție configurați HTTPS, o cheie Django unică, `DEBUG=False` și baza de date persistentă. Nu adăugați `.env` în Git.
