# Audit iniziale dell'app mobile

## TL;DR

L'app mobile del branch `app` è un buon punto di partenza per l'interfaccia: Expo SDK 57, Expo Router, React Query, tema chiaro e scuro, italiano e inglese. Ma è stata scritta per un backend che non usiamo più, le API Next.js del branch `web`. Il problema più grave è quindi lo strato dati: login, token, endpoint e forma dei dati vanno tutti riscritti per il backend Django. Mancano anche test, CI e la gestione della sessione scaduta. Questo documento fotografa lo stato del 9 novembre 2026 ed è storico: non si aggiorna.

## Da dove partiamo

Il branch `refactor/mobile` nasce dal commit `3fb9be8` del branch `app`. Il branch `app` resta intatto, come il vecchio backend.

Numeri misurati all'inizio:

- circa 20 file sorgente in `src/`, 11 schermate e layout;
- TypeScript in modalità `strict`: nessun errore;
- ESLint: 1 errore (`react-hooks/set-state-in-effect` in `src/hooks/use-color-scheme.web.ts`);
- test automatici: nessuno, e nessuno strumento di test installato;
- CI: nessuna.

## Cosa va bene e si tiene

- **Expo SDK 57 con Expo Router.** Le rotte sono file, con due gruppi: `(teacher)` con tre tab e `(parent)` con il portale.
- **React Query** per i dati dal server, con invalidazione dopo le scritture.
- **Il token in `expo-secure-store`**, cioè nel Keychain di iOS e nel Keystore di Android. Sul web c'è un ripiego su `localStorage`, dichiarato e solo per lo sviluppo.
- **Il tema** (`src/constants/theme.ts`), preso dai token di design, con modalità chiara e scura.
- **L'i18n** italiano e inglese, piccolo e tipizzato: una chiave mancante è un errore di compilazione.
- **I componenti** `Button`, `Card`, `TextField` e la modale per completare una lezione.

## Problemi trovati, in ordine di gravità

### Gravi

1. **Backend sbagliato.** `src/lib/api.ts` punta a `https://musicstudio-web.vercel.app/api/v1`, le API Next.js. Il login chiama `POST /auth/login` e si aspetta un solo `token` più l'utente. Il backend Django ha `POST /auth/token/`, che restituisce un token di accesso di 15 minuti e un refresh token con rotazione. Nessuna chiamata dell'app funziona contro Django così com'è.
2. **Nessuna gestione della sessione scaduta.** Non c'è il rinnovo del token, e un 401 non riporta al login. Contro Django, dopo 15 minuti ogni chiamata fallirebbe e l'app resterebbe su schermate vuote.
3. **Il logout è solo locale.** Cancella il token dal telefono, ma il server non lo sa. Dalla fase 4 il backend ha `POST /auth/logout/`, che rende inutilizzabile il refresh token: va chiamato.
4. **Gli insegnanti non possono fare logout.** Il pulsante esiste solo nel portale dei genitori.

### Medi

5. **Tipi scritti a mano.** Le interfacce in `src/lib/queries.ts` sono in camelCase, mentre Django risponde in snake_case (`student_name`, `lessons_remaining`, `is_low`). Scritti a mano, i tipi divergono dal server senza che nessuno se ne accorga. Il backend ha un contratto OpenAPI versionato: i tipi vanno generati da lì.
6. **L'utente non viene mai riverificato.** All'avvio l'app si fida dell'utente salvato al login. Se il ruolo cambia sul server, l'app non lo sa. Django ha `GET /auth/me/`.
7. **Data del pagamento in UTC.** La schermata pagamenti usa `new Date().toISOString().slice(0, 10)`. Dopo la mezzanotte in Italia quella stringa è ancora la data di ieri, perché è calcolata in UTC. Lo stesso tipo di errore che nel backend faceva durare due ore una lezione la notte del cambio d'ora.
8. **Solo la prima pagina di allievi.** Django pagina a 25 elementi. L'elenco e la scelta dell'allievo nei pagamenti mostrano solo i primi 25.
9. **Errori invisibili.** Se la registrazione di un pagamento o il completamento di una lezione falliscono, l'utente non vede niente. Un 409 o un 400 del server andrebbe mostrato.
10. **Retry inutili.** React Query riprova tre volte ogni richiesta fallita, anche un 401 o un 403, che non cambieranno.

### Minori

11. **Testi non tradotti.** Il metodo di pagamento appare come `bank_transfer`, lo stato del pacchetto come stringa grezza.
12. **Titolo fuorviante.** Il dettaglio allievo intitola "Prossime lezioni" una lista che contiene tutte le lezioni, anche passate.
13. **Accessibilità.** Le icone delle tab sono caratteri di testo senza etichetta, e i `Pressable` non dichiarano il loro ruolo. Un lettore di schermo li legge male.
14. **Documentazione stantia.** `README.md` e la constitution descrivono l'app web Next.js su Vercel, non l'app mobile.
15. **L'errore di lint** sul tema per il web.

## Cosa non è stato possibile verificare

Non ci sono emulatori iOS o Android nell'ambiente di lavoro. Le verifiche si fanno con TypeScript, ESLint, test automatici e la build web di Expo, provata contro il backend Django avviato in locale.

## Piano

Il refactor segue spec-kit, come il backend: constitution del mobile, poi `specs/002-django-api-refactor` con spec, piano e task. In ordine: client API generato dal contratto, sessione con rinnovo e logout vero, porting delle schermate a parità di funzioni, correzione dei problemi medi e minori, test e CI, documentazione di studio.
