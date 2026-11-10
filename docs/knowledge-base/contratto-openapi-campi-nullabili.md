# KB: Il contratto OpenAPI non dichiarava campi che possono essere null

## Sintomo
Generando i tipi TypeScript dal contratto per l'app mobile (9 novembre 2026), i tipi dicevano cose impossibili: `GET /students/{id}/lessons/` restituiva uno `Student`, `active_package` di uno studente era sempre presente, e un genitore aveva sempre un profilo insegnante.

## Causa radice
Tre errori in `backend/openapi.yaml`, generato da drf-spectacular:
1. l'azione `lessons` restituisce una lista di lezioni, ma senza `@extend_schema` lo schema la descriveva come uno `Student`;
2. `active_package = PackageSerializer(read_only=True)` senza `allow_null=True`: il server manda `null`, il contratto diceva "sempre presente";
3. lo stesso per `teacher` e `parent_account` in `MeSerializer`.
Nessun client generava tipi dal contratto, quindi nessuno se n'era accorto.

## Come l'abbiamo confermata
Lettura dei tipi generati, poi test sul backend: il contratto documenta una lista e i campi `nullable`, e le risposte reali contengono `null` dove previsto.

## Risoluzione
`@extend_schema(responses=LessonSerializer(many=True))` con `pagination_class=None, filter_backends=[]` sull'azione (altrimenti drf-spectacular inventava una risposta paginata); `allow_null=True` sui tre campi. Commit `2e32d55`, `dec5a13`, `f1ee932`.

## Lezione per il futuro
Un contratto che nessuno consuma può essere sbagliato senza che nessuno lo sappia. Generare i tipi di un client è il modo più rapido per metterlo alla prova.

## Riferimenti
- `backend/apps/students/tests/test_contract.py`
- `docs/learning/adr/ADR-024-tipi-del-portale-dal-contratto.md`
