# Monitoramento do Celery (worker e beat)

Push do app, lembretes, escala fixa e e-mails de confirmação saem pelo Celery. Entre 04/11/2026 e
14/11/2026 o worker ficou em loop de restart e o beat caía a cada tarefa agendada
(`kombu.exceptions.VersionMismatch`): **nenhum push saiu por 10 dias** e ninguém percebeu, porque o
site continuou respondendo 200 e `escalaconnect/push.py` engole o erro de enfileirar (de propósito,
para a ação do usuário não virar erro 500).

Agora há três camadas, todas dentro do próprio projeto (nenhum serviço externo novo):

| Camada | O que detecta | Como aparece |
| --- | --- | --- |
| Healthcheck do Docker | worker não responde ao ping; beat travado | `docker compose ps` mostra `(unhealthy)` |
| Monitor da fila (`escalaconnect/monitor_fila.py`) | fila recusando tarefas; worker ou beat sem batimento | **e-mail aos `ADMINS`** + log `ERROR` |
| `/healthz/celery` | o mesmo, sob demanda | JSON com HTTP 200 ou 503 (e o mesmo e-mail) |
| Monitoramento > **Fila e push** (só superusuário) | tudo acima, mais o conteúdo da fila, a agenda do beat e os últimos pushes | página no site |

## Como funciona

**Batimento.** O beat agenda a tarefa `escalaconnect.batimento` a cada 5 min
(`CELERY_BEAT_SCHEDULE` em `escalaconnect/settings.py`). O worker, ao rodá-la, grava a hora no cache
(Redis, `CACHE_URL`), que o `web` lê. Batimento com mais de `MONITOR_FILA_MINUTOS` (20 min):

- `worker_parado`: nenhum batimento rodou. O worker está parado, ou o beat parou de agendar.
- `beat_parado`: o worker roda tarefas (os testes do `/healthz/celery`), mas nenhum batimento
  vindo do beat.

Logo depois de um deploy (ou com o Redis zerado) não há batimento ainda: o monitor dá a mesma
carência de 20 min antes de reclamar.

**Quem dispara o e-mail.** O `web`, em três momentos:

1. `push.py` ou `escala/fixa.py` não conseguem enfileirar (`fila_indisponivel`, com o erro no
   corpo do e-mail; foi o caso da pane de novembro).
2. Depois de enfileirar com sucesso, no máximo uma vez a cada 5 min por processo, o monitor confere
   o batimento: pega o caso "o Redis aceita, mas ninguém consome".
3. A cada acesso ao `/healthz/celery`.

Cada problema gera **no máximo um e-mail a cada `MONITOR_FILA_AVISO_HORAS`** (6 h), entre todos os
processos (trava no Redis; com o Redis fora, a trava passa a ser por processo, então chegam até 3
e-mails por janela, um por worker do gunicorn). Os e-mails saem pelo
SMTP já configurado (`EMAIL_HOST_USER`), com assunto `[Escala Connect] Celery: ...`, para
jonatasimoes.js@gmail.com (padrão em `settings.py`; `ADMINS` no `.env` troca a lista). Com `ADMINS`
vazio no `.env`, o aviso só vai para o log do `web`.

Os momentos 1 e 2 dependem de alguém usar o site ou o app. Para avisar mesmo sem uso (madrugada,
feriado), alguém precisa consultar o `/healthz/celery` de tempos em tempos: veja o cron abaixo.

## `/healthz/celery`

`GET /healthz/celery` (com ou sem a barra final; nunca redireciona). Sem login. Publica um batimento
de teste (no máximo um a cada 30 s) e responde:

```json
{"ok": true, "problemas": [], "batimento": true, "fila_aceita": true, "worker_seg": 12, "beat_seg": 190}
```

- HTTP **200**: tudo certo. HTTP **503**: `ok: false` e a lista de `problemas`
  (`fila_indisponivel`, `worker_parado`, `beat_parado`), cada um com um `detalhe`.
- `worker_seg` / `beat_seg`: segundos desde o último batimento (`null` = nunca visto).
- `batimento: false`: o cache não é compartilhado (sem `CACHE_URL`, ou Celery em modo eager);
  só a publicação na fila é conferida.

### Consultar pelo cron da VPS (recomendado)

Sem serviço externo: o cron do host chama o endpoint a cada 10 min e o próprio endpoint manda o
e-mail quando há problema.

```cron
*/10 * * * * curl -fsS -o /dev/null --max-time 30 -H 'X-Forwarded-Proto: https' http://localhost:8095/healthz/celery
```

- `localhost` precisa estar em `ALLOWED_HOSTS` (já está no `.env.example`).
- O cabeçalho `X-Forwarded-Proto: https` evita o redirecionamento para HTTPS caso
  `SECURE_SSL_REDIRECT` seja ligado (o `curl -f` trataria o 301 como sucesso).

### Monitor externo (opcional)

Qualquer monitor de uptime que trate HTTP diferente de 200 como falha serve:
`https://<domínio>/healthz/celery`. Ele também pega o caso de o servidor inteiro cair, que o
e-mail (que sai do próprio servidor) não pega.

## Página "Fila e push" (`/monitoramento/fila/`)

No menu Monitoramento, terceira aba, só para superusuário. Mostra:

- **Situação**: o mesmo diagnóstico do `/healthz/celery` (publica um teste a cada 30 s no máximo),
  mais uma pergunta direta ao worker (`inspect`, 1 s de espera): sem resposta, a página já mostra
  "Com problema", antes de o batimento envelhecer. A página não manda e-mail.
- **Tarefas agendadas**: cada item do `CELERY_BEAT_SCHEDULE`, o que faz, quando roda e a próxima
  execução (horário de Brasília). A próxima só acontece com o beat de pé.
- **Na fila**: o que espera no Redis sem worker para pegar (com o worker de pé fica vazia; crescendo
  = worker parado) e o que o worker tem em mãos: rodando, na vez e agendadas para depois (conferência
  de recibos do push 15 min depois do envio, aviso da escala fixa).
- **Últimos pushes**: cada tentativa de envio à Expo (`NotificationAttempt` do canal push), com
  filtro por situação (enviado, erro, pulado pelo intervalo mínimo) e a mensagem de erro. Os cartões
  do topo trazem os envios das últimas 24 h e a hora do último push enviado: "último push há 10
  dias" teria denunciado a pane de novembro.

## Healthcheck do Docker

Em `docker-compose.yml`:

- `celeryworker`: `celery -A escalaconnect inspect ping -d celery@$HOSTNAME` a cada 2 min.
- `celerybeat`: o arquivo de agenda (`/tmp/celerybeat-schedule*`) precisa ter sido regravado nos
  últimos 15 min. O beat o regrava depois de disparar uma tarefa, e o batimento sai a cada 5 min.

O Docker Compose **não reinicia** container `unhealthy` (só o Swarm faz isso) e não avisa ninguém:
serve para o diagnóstico em `docker compose ps`. Container em loop de restart aparece como
`Restarting`, não como `unhealthy`.

## Recebeu o e-mail. E agora?

Na VPS, na pasta do projeto:

```bash
docker compose ps
docker compose logs --tail 100 celeryworker celerybeat
curl -s -H 'X-Forwarded-Proto: https' http://localhost:8095/healthz/celery
```

- `fila_indisponivel`: o `web` não consegue publicar no Redis. Olhe o erro no e-mail (versão de
  biblioteca, Redis fora do ar: `docker compose ps redis`).
- `worker_parado`: veja se o `celeryworker` está `Restarting` ou `unhealthy` e o motivo nos logs.
- `beat_parado`: o mesmo para o `celerybeat`.

Depois de corrigir, o `/healthz/celery` volta a 200 em até 5 min (próximo batimento).

## Configuração (`.env`)

| Variável | Padrão | Para quê |
| --- | --- | --- |
| `ADMINS` | jonatasimoes.js@gmail.com | quem recebe os e-mails, separados por vírgula |
| `MONITOR_FILA_MINUTOS` | 20 | idade máxima do batimento |
| `MONITOR_FILA_AVISO_HORAS` | 6 | intervalo mínimo entre dois e-mails do mesmo problema |
| `MONITOR_FILA_BATIMENTO` | ligado com `CACHE_URL` e sem eager | conferir o batimento |

Para testar o envio do e-mail (SMTP e destinatário) depois do deploy:

```bash
docker compose exec web python manage.py shell -c "from django.core.mail import mail_admins; mail_admins('Celery: teste do monitor', 'E-mail de teste do monitor da fila.', fail_silently=False)"
```

Sem saída = o SMTP aceitou; erro de SMTP aparece na tela. (Os avisos de verdade usam
`fail_silently`, para um SMTP fora do ar não derrubar a página: por isso o teste é direto.)
