# Nexora Operations — Django

Panou intern conectat la backendul Node/Express Nexora. Datele marketplace, ticketele și retragerile rămân în backendul Node; Django gestionează sesiunea internă și interfața.

## Pornire

Configurați variabilele din `.env.example` în `.env`, apoi:

```powershell
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Deschideți `/admin/login/` și folosiți emailul/parola contului staff Nexora. Introduceți codul TOTP în câmpul 2FA dacă este activat. Conturile Django locale nu pot înlocui autentificarea Nexora.

```powershell
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py test accounts --settings=config.test_settings
```

## Acces

- `admin`: dashboard, utilizatori, creare agenți, notificări, retrageri și tickete.
- `support_agent`, `support_manager`, `it_agent`, `logistics_agent`, `moderator`: dashboard și tickete permise de backend pentru departamentul lor.
- `finance_agent`: dashboard și tickete; retragerile necesită departamentul `payments`.
- Call center este departamentul `call_center`, nu un rol separat. Creați un `support_agent` în acest departament.

Identitatea este verificată la fiecare cerere autentificată către admin prin `/auth/me`. Revocarea rolului, blocarea sau expirarea tokenului închid accesul; indisponibilitatea backendului produce HTTP 503. Agenții nu primesc privilegii Django superuser. Navigarea ascunde modulele fără acces, iar middleware-ul protejează și URL-urile directe.

## Fluxuri conectate

- Tickete: informații staff, statistici, filtre pe stare/departament/prioritate/agent, preluare/eliberare, răspunsuri, schimbare status și prioritate.
- Finance: filtrare și paginare retrageri, finalizare după confirmarea transferului, respingere prin API-ul existent.
- Admin: profiluri/securitate/moderare existente, notificări existente și creare conturi staff cu rol și departament.
- Dashboard: statistici reale și acces la module conform rolului.
- Istoric local: ultimele 100 de operațiuni confirmate prin panou, operator și oră; fără mesaje, parole sau tokenuri în jurnal.

## Limitele contractului backend verificat

Contractele au fost verificate în `C:\VSCode\store\backend` pe 11 octombrie 2026. Backendul trebuie publicat separat; testele Django folosesc răspunsuri simulate și nu efectuează plăți sau modificări în producție.

1. `POST /admin/withdrawals/:id/approve` schimbă statusul în `completed`; NU execută transfer bancar. Panoul solicită confirmarea transferului efectuat separat.
2. Respingerea schimbă statusul și apoi restituie soldul prin două operațiuni MongoDB. Backendul trebuie să folosească o tranzacție pentru consistență în caz de eroare între operațiuni.
3. Rutele `/admin/notifications` și `/admin/broadcast` nu au `auth`/`adminOnly` în routerul Node citit. Django le restricționează administratorilor, dar API-ul public necesită aceeași protecție înainte de lansare.
4. Lista staff returnează implicit maximum 50 de tickete. Controllerul nu transmite `page`/`limit` către serviciu, deși serviciul le suportă. Pentru o coadă completă trebuie extins controllerul; panoul afișează explicit numărul încărcat și totalul.
5. Nu există API staff global pentru comenzi, tranzacții, rambursări ale plăților, apeluri telefonice, note interne, transfer între departamente sau istoric de audit global al backendului. Aceste funcționalități necesită extensii Node cu permisiuni și contracte dedicate. Call center din acest panou lucrează pe tickete; nu include telefonie.
6. `PATCH /admin/users/:id/role` acceptă doar `user` și `admin`; modificarea rolului/departamentului unui agent existent necesită extinderea backendului. Crearea agenților este suportată acum.

Nu utilizați DEBUG sau cheia de dezvoltare în producție. Configurați HTTPS, o cheie Django unică și baza de date persistentă. Nu adăugați `.env` în Git.


