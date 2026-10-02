# Эталонный сетап: запуск self-hosted Hermes

Конкретный путь запуска Hermes Agent для одного человека на домашнем сервере или небольшом VPS на Docker image, закреплённом по digest. Это сетап, на котором основана эта коллекция, без приватных частей. Он написан для оператора, который делает это впервые, и для coding agent, который ему помогает.

Дальше описано то, что это развёртывание запускает и закрепляет в своих скриптах. Оно работает на сборке форка Hermes; там, где поведение специфично для этой сборки, текст говорит «в используемой здесь сборке форка». На стоковом upstream сверь каждый раздел один раз с [официальной документацией](https://hermes-agent.nousresearch.com/docs/) для своей версии. Руководство предполагает, что ты прочитал [hardening guide](hermes-hardening.md) или прочитаешь его следующим.

## 1. Что ты строишь

```text
phone / laptop --(private network, e.g. a tailnet)--> host
host:
  private ingress (e.g. Tailscale Serve, HTTPS + identity) --> 127.0.0.1:<port>
  SSH: private network only
  ops repo (git): compose.yaml, scripts/, hermes/identity/ --apply--> data dir
  docker: hermes container (pinned image, s6) = gateway + cron for every profile
          bind mount: ./data/hermes (gitignored) --> $HERMES_HOME
  optional sidecars (loopback only): web UI (chat proxied through the gateway),
          log viewer, isolated browser containers
  host cron: identity publish (runtime -> git), encrypted backup --> off-site
          repository (keys host-only)
```

Один контейнер, одна директория данных, один gateway: всё изменяемое состояние живёт в смонтированной директории, и два gateway никогда не должны её делить. В текущих сборках этот один gateway обслуживает каждый profile (мультиплексирование, §8). Чат — основной интерфейс; на публичном порту ничего не слушает. Git хранит определение системы; директория данных — то, что агент меняет в runtime.

**Установка из исходников (git) вместо Docker.** `hermes setup`, затем `hermes gateway install` регистрирует systemd user service (launchd на macOS), а состояние живёт в `~/.hermes`. Строки ниже про uid remap, capabilities и cgroup к ней не относятся; отдельный непривилегированный пользователь ОС, stop timeout, достаточный для drain, а также правила экспозиции, секретов и бэкапов — относятся. Source-установки обновляются через `hermes update`; image-установки от него отказываются и обновляются переносом pin.

## 2. Что нужно заранее

- [ ] Linux-хост, который всегда включён. 4+ GB RAM для работы только с чатом; если агент будет управлять браузерами, закладывай 16+ GB.
- [ ] Docker Engine с compose plugin, установленный из собственных пакетов Docker.
- [ ] Приватная сеть для админского доступа: Tailscale, WireGuard или уже работающий у тебя VPN.
- [ ] Аккаунт у провайдера моделей. Ограничь расходы на стороне провайдера.
- [ ] Бот чат-платформы (Telegram, Discord, Slack…) и **твой собственный** user ID, который попадает в его allowlist.
- [ ] Приватный git remote для ops-репозитория и отдельный deploy key для хоста (read-write — только для job, которая публикует правки агента).
- [ ] Off-site хранилище для зашифрованных бэкапов и менеджер паролей для passphrase бэкапа.
- [ ] Базовая гигиена хоста: автоматические security updates, вход по SSH только по ключам, firewall default-deny для входящих.

## 3. Структура репозитория

Веди **приватный ops-репозиторий**, который описывает машину:

```text
ops-repo/
├── compose.yaml            # from templates/compose.example.yaml
├── .env.example            # variable names only; the real .env stays on the host
├── scripts/                # deploy, apply/publish identity, backup, health sweep
├── hermes/identity/        # git-tracked identity: SOUL.md, ARCHITECTURE.md,
│                           #   config.yaml, skills/, hooks/, plugins/,
│                           #   scripts/ (cron adapters), services/ (launchers),
│                           #   cron/jobs.json (seed only)
├── hermes/release.yaml     # operator-only release manifest (tag, digest)
├── supply-chain/           # watch policy and one SBOM per pinned image
├── docs/                   # why each decision was made; maintenance checklist
├── .scratch/               # gitignored: one-off helpers, worktrees, logs
└── data/                   # gitignored: data/hermes is the live $HERMES_HOME
```

Правила, которые снимают большую часть путаницы:

- **Checkout на ноутбуке — dev clone, а не runtime.** Пустой `docker ps` на ноутбуке ничего не говорит о сервере. «Deploy» означает запуск deploy-скрипта **на хосте** через приватный SSH.
- **`data/` на ноутбуке устарела.** Никогда не читай её как живое состояние и не деплой из неё.
- **Деплой через скрипт**, никогда не ручной `docker compose up` / `restart` gateway. Скрипт применяет identity, делает git pull, при необходимости пересоздаёт контейнер, заново подключает supervised services, проверяет policy и пробует результат. Он также отказывается деплоить commit, у которого CI красный или не завершён (кроме skip-CI commits от собственной publish job хоста).

## 4. Главное в compose

Начни с [`templates/compose.example.yaml`](../templates/compose.example.yaml). У каждой неочевидной строки в нём есть однострочное обоснование. Важнее всего:

| Настройка | Зачем |
| --- | --- |
| `image: <registry>/hermes-agent:<tag>@sha256:<digest>` | Digest — точка ревью. Без него `docker compose pull` может незаметно перевести тебя на новый релиз. Переноси pin отревьюенным commit вместе с его SBOM. |
| `user: "0:0"`, без переопределения `entrypoint`, `HERMES_UID/GID` = владелец директории данных на хосте | Init образа работает от root, чтобы переназначить uid пользователя `hermes` и исправить владельца файлов, затем сбрасывает привилегии. Свежие images по умолчанию используют uid 10000; совпадение с uid хоста держит файлы агента и хостовых скриптов (backup, git) у одного владельца. |
| Без `no-new-privileges`; `cap_drop: ALL` + семь возвращённых | `no-new-privileges` ломает setuid remap. Сбросить все capabilities и вернуть только те семь, что нужны для remap и остановки сервисов, — более безопасный компромисс. Если после bump image контейнер перестал загружаться, первым подозревай этот блок. |
| `command: ["gateway", "run"]` | Запускает gateway под supervision. Из-за этого разовому `docker compose run hermes` нужен явный бинарник (`/opt/hermes/.venv/bin/hermes …`). |
| `working_dir` | Здесь разрешаются относительные пути и поиск project context. Если это vault или репозиторий со своими правилами для агентов, защити его непустым `.hermes.md` ([руководство по identity, §5](identity-memory-context.ru.md)). |
| `HERMES_WRITE_SAFE_ROOT` | Инструменты записи файлов по умолчанию ограничены `$HERMES_HOME`. Перечисли каждый root, куда агенту можно писать (workspace, `/tmp`). Задавай это в compose: собственный ENV образа побеждает `$HERMES_HOME/.env`. |
| `PATH` | Сначала бинарники image, затем overlay-директория `bin` в data home для инструментов, которых нет в image, затем системные пути — как в login-shell profile образа. Overlay-копия системного инструмента всё равно побеждает; находи такие затенения проверкой, а не перестановкой порядка. |
| Порты только `127.0.0.1:…` | Порты, опубликованные Docker, обходят ufw (см. §5). |
| `shm_size`, `ulimits.nofile`, `deploy…pids`, memory + `memswap_limit` | Браузеры и MCP servers исчерпывают значения по умолчанию. Лимит pids останавливает fork storm, не душа обычную работу. Работающий контейнер сохраняет лимиты, с которыми был создан, до следующего пересоздания. |
| `S6_*_GRACETIME` и `stop_grace_period` | Gateways работают как динамические s6-сервисы, а s6-overlay по умолчанию добивает оставшееся через SIGKILL через 3 с после SIGTERM. 150 с на каждый покрывают drain с запасом; grace period (здесь 360 с) должен превышать оба. SIGKILL посреди записи — именно так повреждается SQLite session store. |
| Seccomp + AppArmor для sandbox | При `cap_drop: ALL` Bubblewrap нужен seccomp profile, добавляющий только syscalls для namespaces; на Ubuntu 24.04 ещё `apparmor:unconfined` плюс sysctl хоста для непривилегированных userns. Никогда не `seccomp=unconfined` и не `privileged`. |
| `healthcheck` | Только для наблюдаемости: Docker никогда не перезапускает unhealthy-контейнер. Дай ему длинный `start_period` (здесь 30 мин), чтобы миграции первой загрузки оставались в `starting`. |
| Без volume на `/opt/hermes` | Код принадлежит image. Долговечные исправления поставляются новым digest image, а не файлами, скопированными в работающий контейнер. |
| Один gateway на директорию данных | Второй контейнер из того же image (например, dashboard sidecar) запускает второй gateway на том же bot token; потерянные сообщения тогда выглядят как «сломался голос». |
| Web UI sidecar без `depends_on` | Из-за `depends_on: hermes` каждый `compose up webui` попутно пересоздавал gateway. UI проксирует чат через gateway и просто выдаёт ошибки, пока тот не ответит. |
| Инструменты с доступом к Docker socket | Монтирование socket с `:ro` ничего не защищает: API за ним read-write, то есть root на хосте. Отключи actions, включи auth, оставь loopback или поставь read-only socket proxy. |

Запускай браузеры в отдельных контейнерах, а не в cgroup gateway, в сети, которую браузерные контейнеры делят только со своим контроллером. Утёкшая вкладка не должна быть способна убить gateway, а у прорыва из renderer не должно быть маршрута к API gateway.

## 5. Сетевая экспозиция

1. **Привязывай каждый опубликованный порт к `127.0.0.1`.** Docker вставляет свои NAT-правила до того, как пакет увидит ufw, поэтому `ufw deny` не защищает порт, опубликованный на `0.0.0.0`.
2. **Открывай admin UI через приватный ingress с аутентификацией.** Tailscale Serve — один из вариантов: HTTPS, доступ только из приватной сети, к запросу привязана identity. Собственный пароль приложения добавь вторым слоем.
3. **SSH только через приватную сеть**, только по ключам, без входа под root. В sshd побеждает первое совпадение: cloud-init drop-in с `PasswordAuthentication yes` перебивает файл, прочитанный позже, поэтому называй свой `00-…`. sshd с socket activation держит старый config, пока не перезапустится `ssh.service`.
4. **API server** выключен, пока он не нужен клиенту. Web UI sidecar он нужен: тогда он слушает `0.0.0.0` внутри контейнера (чтобы до него доходили compose network и опубликованный порт), требует ключ, а хост публикует его только на loopback. Остаточный риск: любой контейнер в этой compose network, у которого есть ключ, может управлять агентом.
5. Проверяй **снаружи**: просканируй порты публичного и LAN-адреса хоста с другой машины. Bind-адрес в compose — не доказательство ([hardening §10](hermes-hardening.md#10-secure-gateway-access-and-exposed-services)).

## 6. Где живут секреты

| Секрет | Где хранится | Никогда |
| --- | --- | --- |
| Ключи провайдеров, bot tokens | `$HERMES_HOME/.env` на хосте, mode 600 | в git, чате или `config.yaml` |
| Секреты, нужные subprocess или skill | `.env` ops-репозитория на хосте → passthrough через `environment:` в compose | `hermes config set my.custom_key <secret>`: в `.env` направляются только распознанные ключи; custom key попадает в `config.yaml` **открытым текстом**, а publish identity затем зеркалирует этот файл в git |
| Секреты webhook в config | интерполяция `${ENV}` в ключе config | литеральное значение |
| Пароль и ключи репозитория бэкапов | файл только на хосте, mode 600, **не смонтирован ни в один контейнер** | доступен агенту на чтение: агент, который может прочитать ключи, может и удалить (prune) твои бэкапы |

Заметки:

- **Удаление env vars — не граница.** Shells агента работают от того же пользователя ОС, который может читать `.env`. Реальным ограничением считай scoping на стороне провайдера (read-only токены, токены на отдельный ресурс, лимиты расходов) и проверяй любое утверждение «агент не может добраться до X».
- **Если используешь secret manager, учитывай бюджет его чтений.** Каждый pull читает каждый привязанный секрет, и каждый home делает pull сам: default home, каждый именованный profile, каждый CLI-процесс (включая те, что агент запускает из своего терминала). Когда бюджет исчерпан, каждое чтение падает, и загрузка поднимается без messaging tokens при зелёном health. Схема, которая держится: длинный cache TTL (здесь 6 ч, в каждом home); при throttled re-pull сохраняй последние хорошие значения и делай backoff, никогда не опустошай scope; один общий для аккаунта маркер backoff при первом ответе rate-limit; дочерние shells читают только cache gateway; обновление отказывает, пока бюджет исчерпан; health sweep сообщает оставшийся бюджет. Ротированному секрету тогда нужно удалить файл cache перед перезапуском.
- Запускай secret scanner, например gitleaks, на **каждый** push, включая автоматические commits, которые пропускают CI (сканируй их на хосте до push).
- Никогда не вставляй секрет в чат ни с каким агентом. Если вставил — ротируй.

## 7. Запуск по шагам

```bash
# On the host, inside the ops repo checkout
mkdir -p data/hermes && chmod 700 data/hermes
cp .env.example .env && chmod 600 .env           # fill in compose-level values
./scripts/apply-identity.sh                      # SOUL, ARCHITECTURE, config, skills… BEFORE first start
docker compose run --rm hermes \
  /opt/hermes/.venv/bin/hermes setup             # wizard: provider, keys, chat platform
./scripts/deploy.sh                              # first start and every later one
./scripts/hermes-cli.sh config get approvals.cron_mode
```

- Сначала примени identity, чтобы засеянные defaults образа не победили.
- Wizard нужен, только пока нет `$HERMES_HOME/.env`; запускай его, пока ни один gateway не работает. Ему нужен явный бинарник, потому что команда сервиса — `gateway run`.
- Сервис стартует от root, поэтому обычный `docker exec hermes …` выполняется от **root** и оставляет в директории данных файлы с владельцем root, которые ломают хостовые jobs (publish, backup). Используй маленькую обёртку (`hermes-cli.sh` выше), которая запускает `docker exec -u hermes <container> /opt/hermes/.venv/bin/hermes "$@"`.

## 8. Начальный baseline конфигурации

Примени baseline approvals из [hardening §8](hermes-hardening.md#8-configure-approvals-as-guardrails-not-theatre), затем **трио install policy** и ключи, которые это развёртывание закрепляет рядом с ним:

```bash
# hermes = your CLI wrapper (runs as the runtime user)
hermes config set skills.write_approval true     # skill edits stage for your review
hermes config set memory.write_approval false    # memory writes apply directly
hermes config set approvals.cron_mode deny       # cron never self-approves dangerous shell
hermes config set browser.auto_local_for_private_urls false
hermes config set security.allow_private_urls false
hermes config set cron.catch_up_missed false     # a gateway that was down does not replay missed runs
```

Gateway читает `config.yaml` только при загрузке. После изменения перезапусти gateway service на месте (`docker exec <container> s6-svc -r /run/service/gateway-default`). Не пересоздавай ради этого контейнер: пересоздание опустошает `/run/service`, и сервисы нужно подключать заново.

Зачем каждый ключ:

- **`memory.write_approval: false`**: `true` ставит каждую запись в `pending/` для оператора. У cron job нет оператора, поэтому её записи в память никогда не завершаются. Чтобы конкретная job не писала в память, не включай toolset `memory` **для этой job**.
- **`skills.write_approval: true`**: skills — это процедуры, которые позже исполняются с полномочиями, поэтому для них — более медленный путь через ревью.
- **`approvals.cron_mode: deny`**: опасная команда в unattended job блокируется и попадает в отчёт, а не одобряется автоматически. Это переключатель, отдельный от очереди на одобрение.
- **`browser.auto_local_for_private_urls: false`**: при `true` (значение по умолчанию в seed образа) приватный URL *направляется* в локальный браузер, а не отклоняется, и `security.allow_private_urls` этот путь не покрывает.

**Именованные profiles** (`hermes profile create <name>`) разрежены: отсутствующий листовой ключ заполняется из **upstream defaults, а не из твоего default profile**. Upstream по умолчанию ставит `cron.catch_up_missed` и `gateway.auto_multiplex_migration` в true, а seed ставит fallback браузера в true. Закрепи каждый защитный ключ в каждом profile («seed shield»), вставляй их скриптом, который проставляет значения в живые файлы, а не ручными правками, и проверяй их все при каждом деплое и обновлении:

```bash
for p in default work; do
  for k in skills.write_approval memory.write_approval approvals.cron_mode \
           browser.auto_local_for_private_urls cron.catch_up_missed \
           gateway.auto_multiplex_migration; do
    printf '%s %s = ' "$p" "$k"; hermes -p "$p" config get "$k"
  done
done
```

**Один gateway обслуживает каждый profile.** Текущие сборки убрали `gateway.multiplex_profiles: false`: gateway при загрузке переписывает его в `true`, per-profile gateway slots остаются выключенными, а закрепление `false` в git лишь заставляет зеркалируемый config расходиться. Что меняется: секреты каждого profile разрешаются строго в его собственном scope, без fallback на окружение процесса; один cron scheduler выполняет jobs всех profiles; а краш, перезапуск или лимит cgroup на default gateway роняет cron всех profiles вместе. Profile, которому нужен собственный gateway, задаёт `gateway.standalone: true` в своём config.

Policy **проверяется, а не заблокирована**: uid агента может писать в `config.yaml`, а publish job зеркалирует его в git, так что self-edit способен переключить ключ. Пусть deploy-скрипт после каждого старта читает действующие значения обратно и падает при расхождении. Ключи-списки: стоковый `hermes config set` сохранил JSON-список как YAML-строку, и deny list, прочитанный как строка, совпадал с каждой командой (deny-all). Для ключей-списков используй `hermes config edit` или YAML-список и читай их обратно.

В используемой здесь сборке форка image вшивает managed config seed для трио. Он заполняет только ключи, которых нет в пользовательском config: `config set` побеждает, `config unset` позволяет seed проявиться. Upstream документирует свой managed scope как lock; проверь, что у твоей сборки, и в любом случае сохраняй проверку при деплое.

## 9. Identity в git

Напиши `SOUL.md` и `ARCHITECTURE.md` по шаблонам [`templates/SOUL.template.md`](../templates/SOUL.template.md) и [`templates/ARCHITECTURE.template.md`](../templates/ARCHITECTURE.template.md). Храни их в `hermes/identity/` и применяй к директории данных аддитивно. `SOUL.md` загружается из `$HERMES_HOME` в любой сборке; слот `ARCHITECTURE.md` — особенность используемой здесь сборки форка, так что проверь, что твоя версия его загружает. Порядок слотов, лимиты размера, двусторонняя синхронизация с агентом, который сам себя редактирует, и перехват через project context: [Identity, память и контекст](identity-memory-context.ru.md). Cron jobs и память — runtime state, поэтому они **не** деплоятся через git.

## 10. Бэкапы

1. Запускай бэкап из **cron хоста**, а не из cron Hermes, чтобы он работал и тогда, когда Hermes лежит.
2. Используй инструмент с шифрованием и дедупликацией, например restic. Его ключи храни только на хосте (§6). Пусть ночная job печатает только `forget --prune --dry-run`; настоящий prune ждёт оператора. Запрети агенту команды prune (`approvals.deny`, например `*restic*forget*`). Настрой lifecycle bucket так, чтобы хранилась только последняя версия объекта.
3. **Никогда не копируй живой SQLite-файл напрямую и никогда не открывай живой WAL через `sqlite3` хоста** (SQLite хоста из окна бага со сбросом WAL может его повредить; исправлено в 3.51.3+, backports 3.50.7 / 3.44.6). Копируй базу через SQLite самого image в одноразовом вспомогательном контейнере из того же digest: `--network none`, read-only, `--cap-drop ALL` и явный `--entrypoint` (entrypoint образа по умолчанию — supervisor, который запустил бы второй gateway). Размести копию вне bind mount данных, выполни на ней `PRAGMA quick_check` и только потом продвигай её как хорошую копию. Проваленная проверка всё равно выгружает остальное дерево, но никогда не добавляет новый tag «хорошей базы».
4. Исключай то, что можно скачать заново или пересобрать (кэши пакетов, логи, snapshots, scratch, worktrees, установленные зависимости); сохраняй то, что содержит историю или секреты. Помечай одноразовые cache-директории `CACHEDIR.TAG` и делай бэкап с `--exclude-caches`; исключённая директория с именем `cache` всё равно может содержать единственную копию чего-то, так что исключение — не разрешение удалять. Тестовые fixtures и экспериментальные базы держи **вне** директории данных вообще. Volumes, смонтированные через loop (например, постоянные профили браузера), нужно указать как отдельные корни бэкапа.
5. Перед каждым обновлением делай полный консистентный snapshot отдельным шагом ([эксплуатация, §4](operations.ru.md)).
6. **«Бэкап прошёл» — ещё не «восстанавливается».** Раз в неделю запускай структурную проверку репозитория, а раз в квартал восстанавливай в scratch-директорию. Повседневная периодичность — в [эксплуатации](operations.ru.md).

## 11. Чеклист приёмки первой недели

Проверяй поведение, а не статус. Зелёный `/health` уже сосуществовал с мёртвым MCP server, с config-файлом, который не распарсился и откатился к defaults, с отсутствующим bot token и с исчерпанным балансом провайдера.

- [ ] **Авторизованный чат**: ты пишешь боту и получаешь осмысленный ответ.
- [ ] **Неавторизованный чат**: второй аккаунт пишет боту и не получает ничего или получает отказ pairing, а попытка видна в логах.
- [ ] **Экспозиция**: внешний скан портов не показывает ничего нового, а admin UI отвечают только через приватную сеть.
- [ ] **Cron canary**: одна безобидная job (например, «ответь текущей датой») срабатывает по расписанию, доставляет в нужный чат и показывает ожидаемый toolset. Scheduler добавляет к job каждый глобально включённый MCP server, если job не несёт литеральный sentinel `no_mcp`; проверяй действующий список инструментов, а не сохранённый.
- [ ] **Policy**: цикл из §8 печатает ожидаемые значения для каждого profile.
- [ ] **Загрузка config**: в логе этой загрузки нет предупреждения «failed to process config.yaml, falling back».
- [ ] **MCP**: `hermes mcp list` / `hermes mcp test <name>`, запущенные через обёртку, проходят для каждого включённого server.
- [ ] **Секреты**: в `git log -p` и в image нет секретов, а файлы `.env` имеют mode 600.
- [ ] **Чистая остановка**: `docker compose stop hermes` завершается в пределах grace period, без SIGKILL в логах.
- [ ] **Восстановление бэкапа**: первый snapshot восстанавливается в scratch, а его база проходит `quick_check`.
- [ ] **Путь алертов**: один намеренный сбой доходит до тебя end to end. Канал алертов, который ни разу не срабатывал, не доказан.

Записывай результаты в ops-репозиторий. Более широкий список приёмки — [hardening §16](hermes-hardening.md#16-acceptance-tests).

## 12. Сбой → симптом → исправление

| Сбой | Симптом | Исправление |
| --- | --- | --- |
| Порт опубликован на `0.0.0.0` | UI доступен из LAN или интернета, несмотря на ufw | Привязать к `127.0.0.1`, использовать приватный ingress |
| Второй gateway на том же token | Ошибки polling «Conflict», потерянные аудио или сообщения | Один gateway на директорию данных; убрать sidecar |
| `no-new-privileges` или non-root `user:` | Контейнер падает на init, ошибки владельца файлов | Стартовать от root, полагаться на сброс привилегий в image |
| `docker exec` от root | Файлы с владельцем root в директории данных; publish или backup на хосте падают | `chown` обратно на runtime uid; используй обёртку |
| `config.yaml` починен во время работы | Агент всё ещё молчит или всё ещё на fallback-значениях | Перезапусти gateway service на месте; не пересоздавай |
| SIGKILL при остановке | Ошибки БД «malformed», долгая перестройка полнотекстового индекса при следующей загрузке | Увеличить grace; остановить, скопировать, чинить **копию** |
| Достигнут лимит процессов | «can't start new thread» | Пересоздать контейнер через deploy-скрипт (перезапуск service не освобождает оставшиеся процессы); вынести браузеры |

## 13. Передача сетапа другому человеку

Если поднимаешь такое для члена семьи или друга:

**Передай:** *структуру* ops-репозитория, пример compose, скрипты, обобщённые шаблоны, это руководство и [руководство оператора для coding agent](coding-agent-operator.ru.md) — для агента, который будет всё это сопровождать.

**Своим они должны владеть сами:**

- хостом, приватной сетью, аккаунтом провайдера и лимитом расходов;
- ботом и allowlist, а также каждым секретом — созданным ими заново и никогда не пересылаемым через твой чат;
- `SOUL.md`, написанным про *их* ассистента, а не копией твоего;
- репозиторием бэкапов и passphrase;
- решениями: что агенту можно делать без присмотра и о чём он обязан спрашивать.

**Никогда не переносить:** твои `memories/`, сессии или `state.db`, `.env`, файлы auth- или OAuth-токенов, cron jobs, упоминающие твои аккаунты, или skills, в которых закодированы твои приватные workflows. Обобщённые skills копируй только после прочтения. Их агент начинает с нуля и изучает *их*.

Повседневная эксплуатация (обновления, health checks, дисциплина cron, инциденты) — в [эксплуатации](operations.ru.md).
