WorkDo — Мульти-арендная SaaS-платформа для автоматизации бизнеса

WorkDo — это многофункциональная SaaS-платформа, построенная по принципу мульти-арендности (multi-tenant), которая предоставляет инструменты для управления бизнесом в трёх вертикалях:

Beauty & Wellness — салоны красоты, спа, wellness-центры
Security Services (ЧОП) — охранные предприятия, частные охранные организации
Yacht Club — яхт-клубы, марины, стоянки для судов
Платформа работает на workdo.ru и ориентирована на рынок РФ и СНГ.

Содержание

Концепция
Технологический стек
Архитектура
Мульти-арендность
Вертикали
Beauty & Wellness
Security Services
Yacht Club
Система налогообложения (taxation)
Управление доступом (RBAC)
Аутентификация и регистрация
Работа с базой данных
Производительность
Архитектура папок
UI / Дизайн-система
Команды и скрипты
Окружение и переменные
Разработка
Лицензия
Концепция

WorkDo решает проблему фрагментации бизнес-инструментов для малого и среднего бизнеса. Вместо того чтобы использовать отдельные системы для учёта сотрудников, финансов, клиентов, инцидентов и планирования, платформа предоставляет единое рабочее пространство для каждой вертикали.

Ключевые принципы:

Изоляция данных клиентов — каждый бизнес (арендатор) работает в своей изолированной схеме PostgreSQL. Данные разных клиентов физически разделены.
Единая кодовая база — одна кодовая база обслуживает все три вертикали, что снижает стоимость разработки и поддержки.
Server Actions first — вся бизнес-логика мутаций реализована через Next.js Server Actions, без традиционного REST API (кроме OAuth и вебхуков).
React Server Components — там, где не требуется интерактивность, используются серверные компоненты для минимального JS на клиенте.
Технологический стек

Слой	Технология
Framework	Next.js 16 (App Router)
Язык	TypeScript 5.7
UI-библиотека	React 19 + shadcn/ui (Radix Primitives, стиль radix-nova)
Стилизация	Tailwind CSS 4
Анимации	Framer Motion 12
Иконки	lucide-react
Чарты	recharts
База данных	PostgreSQL (через pg)
ORM (public schema)	Prisma 6
Query Builder (tenant schemas)	Kysely 0.28
Генерация Kysely-типов	kysely-codegen
Аутентификация	NextAuth.js v5 (beta)
Формы	react-hook-form + zod
Уведомления	sonner (toast)
Email	Resend + Nodemailer (SMTP)
Геокодирование	Geoapify (с кэшированием)
Блог	MDX + next-mdx-remote
Миграции (public)	кастомный SQL-раннер через tsx (scripts/public/)
Миграции (tenant)	кастомные SQL-скрипты через tsx
Развёртывание	Vercel
Аналитика	Google Analytics + Vercel Speed Insights
Капча	Cloudflare Turnstile
Архитектура

Слои Clean Architecture (на каждую вертикаль)

┌─────────────────────────────────────────────────┐
│  actions/   (Next.js Server Actions)            │ ← публичный API вертикали
├─────────────────────────────────────────────────┤
│  services/  (бизнес-логика, оркестрация)         │
├─────────────────────────────────────────────────┤
│  repositories/  (доступ к данным через Kysely)   │
├─────────────────────────────────────────────────┤
│  domain/entities/  (чистые TypeScript-типы)      │
└─────────────────────────────────────────────────┘
Два уровня базы данных

Shared pg.Pool
├── Public schema (Prisma ORM)
│   └── Users, Businesses, Roles, Sessions, Invitations, GeocodedAddress, блог
└── Tenant schemas (Kysely)
    ├── tenant_beauty_1
    │   └── Client, Master, Service, Appointment, Schedule, Review
    ├── tenant_security_27
    │   └── Employee, Client, Object, Post, Shift, Incident, Contract, Salary, ...
    └── tenant_yacht_3
        └── Client, Yacht, Berth, Booking, SeasonPass, Crew, ...
Public schema содержит глобальные сущности (пользователи, организации, роли). Tenant schemas создаются по одной на каждый зарегистрированный бизнес и содержат все операционные данные.

Мульти-арендность

Модель: Schema-per-Tenant

Каждый арендатор (business) получает отдельную схему PostgreSQL:

Формат имени: tenant_{vertical}_{businessId} (например, tenant_security_27)
Структура схемы определяется вертикалью бизнеса (шаблон в migrations/templates/{vertical}/up.sql)
При регистрации нового бизнеса схема создаётся из шаблона и прогоняются все миграции
Разрешение арендатора (resolveTenant)

Функция resolveTenant() в src/tenants/resolver.ts определяет текущего арендатора только по сессии залогиненного пользователя:

Сессия пользователя — выбор из memberships (BusinessUser), по вертикали из URL: /(security|yacht|beauty) → x-tenant-vertical; иначе первый BusinessUser
Локальная разработка — DEFAULT_TENANT_ID из env (только localhost)
Клиентские заголовки x-tenant-id / x-tenant-schema и поддомен {slug}.workdo.ru не учитываются — у запроса нет возможности переключиться в чужой тенант.

Middleware (прокси)

Middleware (src/proxy.ts) на каждый запрос страницы срезает клиентские заголовки x-tenant-id / x-tenant-schema / x-tenant-vertical и устанавливает только:

x-tenant-vertical (из URL: /(security|yacht|beauty))
x-request-path / x-request-method — для трейса (в Node-рантайме headers() не отдаёт URL)
Трейс запросов (observability, PII-safe)

src/platform/services/request-trace.ts пишет одну JSON-строку в console.log на каждый запрос, в котором резолвится тенант (uid-hash, businessId, tenantSchema, vertical, method, санитизированный path, source, rpc, resolveMs). Dedup через React.cache — одна строка на HTTP-запрос даже при N резолвах.

PII policy: в логи НЕ попадают email, имя, телефон, IP, тело запроса, сырой userId. uid = sha256(userId)[0..16] (необратимо), path — UUID→{uuid}, цифры→{n}. businessId/tenantSchema — это тенант (юрлицо), хранится в открытом виде. Отключить: TRACE_LOGGING=false.

Валидация схем

Имена схем проверяются регулярным выражением /^tenant_(beauty|security|yacht)_\d+$/ для предотвращения SQL-инъекций.

Вертикали

Beauty & Wellness

Управление салоном красоты, спа или wellness-центром.

Сущности:

Сущность	Описание
Client	Клиент салона (имя, телефон, email, заметки, теги)
Master	Мастер (привязка к пользователю, специализация, фото)
Service	Услуга (название, описание, длительность, цена, категория)
Appointment	Запись (клиент, мастер, услуга, время, статус)
Schedule	Расписание мастера (день недели, часы работы)
Review	Отзыв (рейтинг, комментарий, публичность)
Функционал: запись клиентов, расписание мастеров, склад (Inventory), финансы, аналитика, настройки.

Security Services

Полный комплекс учёта для охранного предприятия (ЧОП).

Сущности (16+):

Сущность	Описание
Employee	Сотрудник (ФИО, удостоверение, должность, зарплата, бригада)
Client (B2B)	Организация-заказчик (компания, контактное лицо, телефон, теги)
Object	Охраняемый объект (название, адрес, координаты, клиент)
Post	Пост охраны (название, тип, номер, привязка к объекту)
Shift	Смена (охранник, пост, время, статус, тип смены)
Brigade	Бригада / отдел (название, объект)
Contract	Договор (клиент, объект, ставка, срок, автопродление)
Incident	Инцидент (заголовок, описание, severity, статус, категория, план действий, фин. потери)
Patrol	Патруль (маршрут с контрольными точками, статус)
Equipment	Оборудование (тип, серийный номер, закрепление)
TimeRecord	Табель (отметки прихода/ухода, часы: ночные, сверхурочные, праздничные)
Salary	Зарплата (период, оклад, почасовая, доплаты, налоги, статус)
Estimate	Смета (статьи, план/факт, прибыль, НДС)
Budget	Бюджет (годовой/месячный, доходы/расходы, план/факт)
InstructionLog	Журнал инструктажей (тема, дата, подпись, сотрудники)
Функционал: полный HR-учёт, планирование смен, маршрутизация патрулей, учёт рабочего времени, расчёт зарплаты (с налогами), управление инцидентами, сметы и бюджеты, договоры с автопродлением.

Yacht Club

Управление яхт-клубом, мариной, стоянкой для судов.

Сущности (12+):

Сущность	Описание
Client	Владелец яхты / клиент клуба
Yacht	Судно (название, модель, тип, регистрация, длина, ширина, осадка, мотор)
Berth	Причал (номер, пирс, секция, габариты, глубина, тип, удобства, цены)
Booking	Бронирование (клиент, яхта, причал, даты, статус, оплата)
SeasonPass	Сезонный абонемент (клиент, яхта, причал, сезон, статус)
Service	Услуги марины
Crew	Экипаж (назначения на судно)
Функционал: учёт судов, управление причалами и бронированием, сезонные абонементы, экипаж, инциденты.

Система налогообложения (taxation)

Гибкая модель налогов, общая для всех вертикалей и расширяемая на страны СНГ. Три универсальных уровня + настраиваемые параметры:

Страна → ОПФ (ООО/ИП/Самозанятый) → Система (ОСНО/УСН/ПСН/НПД/АУСН/ЕСХН) → Параметры (ставки/лимиты/взносы)
Справочник — статический TS-модуль src/lib/taxation/catalog.ts (сейчас РФ 2026), описывает, какие параметры собирать для каждого режима (ставки, лимиты, фикс. взносы, особенности). Параметры schema-driven (percent/number/currency/boolean/enum/scale).
Конфиг бизнеса — Business.settings.taxation (public schema JSONB), значения каждый клиент задаёт сам.
UI — src/components/settings/taxation-panel.tsx, вкладка «Финансы» на странице настроек каждой вертикали.
Зарплатные налоги (НДФЛ/соцвзнос/страховые) — секция payroll этой же конфигурации; читается страницей /security/finance.
Добавление страны — новая запись в TAXATION_CATALOG (ключ — значение из Business.country, src/lib/countries.ts).

Управление доступом (RBAC)

Роли хранятся в таблице Role (public schema) и связаны с пользователем через BusinessUser.

Основные роли:

Роль	Ранг	Описание
owner	100	Владелец (все права)
admin	90	Администратор
security_chief	80	Начальник охраны
shift_lead	50	Старший смены
guard	30	Охранник
member	10	Участник
Права задаются в формате строковых идентификаторов: "employees:read", "finance:write", "dashboard:view" и проверяются функциями can(), canAny(), canAll() из src/lib/permissions.ts.

Аутентификация и регистрация

Провайдеры NextAuth

Credentials — email + пароль (bcryptjs), основной метод
Google OAuth — опционально
GitHub OAuth — опционально
Регистрация по email + пароль

Пользователь заполняет форму на /register
Создаётся RegistrationPending с 6-значным OTP-кодом
Код отправляется на email (через Resend / Nodemailer)
После подтверждения создаются User, Business, BusinessUser
Создаётся tenant-schema из шаблона
Пользователь перенаправляется в дашборд
Регистрация / вход через Google

При Google-входе NextAuth создаёт User (без пароля и бизнеса) ещё до завершения регистрации.
/api/auth/redirect-dashboard оценивает наличие бизнеса: если его нет — ведёт на /register?error=no_business, чтобы завершить регистрацию (выбрать вертикаль, задать пароль).
Если данные с тем же email уже зарегистрированы по паролю, а пользователь входит через Google — в signIn callback (src/lib/auth/config.ts) OAuth-аккаунт привязывается к существующему User вместо ошибки OAuthAccountNotLinked.
Если User создан Google-ом, но регистрация не завершена, по email+паролю можно задать пароль и дособрать бизнес (startEmailRegistration / verifyRegistrationAndComplete обновляют существующего User вместо создания дубликата).
Сессии

JWT-сессии (без хранения в БД)
При каждом обновлении токена проверяется, что пользователь всё ещё имеет доступ к бизнесу
Работа с базой данных

Public schema (Prisma)

Файл: prisma/schema.prisma (15 моделей)
Миграции: SQL-файлы в migrations/public/, применяются кастомным раннером scripts/public/run-public-migrations.ts (таблица schema_migrations для трекинга)
Команды: npm run db:push, npm run db:migrate, npm run public:migrate
Tenant schemas (Kysely)

Миграции: SQL-файлы в migrations/tenant/{vertical}/
Security: 55 миграций (001–055)
Beauty и Yacht: аналогичная структура
Шаблоны для новых схем: migrations/templates/{vertical}/up.sql
Важно: все Kysely-экземпляры кэшируются по схеме + вертикали и работают через единый pg.Pool.

Kysely-типы (сгенерированные vs рукописные)

Источник правды для табличных типов — сгенерированные security.ts / beauty.ts / yacht.ts (kysely-codegen), экспортируют interface DB. Импортируются как DB as SecurityDatabase / BeautyDatabase / YachtDatabase (реэкспорт из src/lib/db/kysely/client.ts).
Рукописные {vertical}.types.ts — только enum-like union'ы (AppointmentStatus, PostType, YachtType, ...), которые codegen не знает. Табличных интерфейсов там больше нет.
Конверсии raw-типов (Numeric→number, Json→массив, Date) — src/lib/db/kysely/row-casts.ts.
Перегенерировать после изменения схемы: npm run generate:kysely (все), npm run generate:kysely:<vertical> (одна вертикаль).
Производительность (оптимизации списков)

Страницы-списки дашбордов оптимизированы по паттерну серверная пагинация + поиск (employees, clients, objects, posts, equipment):

Серверная пагинация и поиск — limit/offset + ILIKE выполняются в SQL (репозиторий), клиенту отдаётся только страница; нет выгрузки всех записей в RSC.
Один агрегатный запрос вместо нескольких — countByActivity() (GROUP BY isActive) для карточек счётчиков вместо двух отдельных count-запросов.
Кэширование справочников — unstable_cache для позиций (employee-positions) и списка бригад (brigades), ключ по tenant-схеме.
Инвалидация на мутациях — updateTag(tag) из next/cache на каждый create/update/delete/import соответствующих сущностей. revalidateTag(tag) в этой версии Next (16.2.1) требует второй аргумент (profile), поэтому используется одноаргументный updateTag.
Индексы под поиск/сортировку — миграция 045_add_employee_indexes.sql (ФИО, телефон, createdAt DESC, композит isActive + createdAt).
Измерение после оптимизации: RSC-запрос /security/employees 1.52s → 401ms.

Архитектура папок

├── prisma/                     # Prisma-схема (public schema)
├── migrations/
│   ├── public/                 # Миграции public schema (SQL)
│   ├── tenant/                 # Миграции tenant-схем по вертикалям
│   └── templates/              # Шаблоны для создания новых схем
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/             # Страницы аутентификации
│   │   ├── (dashboard)/        # Дашборд (beauty/, security/, yacht/)
│   │   ├── (landing)/          # Лендинг
│   │   ├── (marketing)/        # Маркетинговые страницы
│   │   ├── admin/              # Админ-панель
│   │   └── api/                # API-роуты
│   ├── components/
│   │   ├── ui/                 # shadcn/ui примитивы (21 компонент)
│   │   ├── dashboard/          # Сайдбар
│   │   ├── providers/          # SessionProvider
│   │   └── ...                 # Переиспользуемые компоненты
│   ├── config/navigation/      # Конфиги навигации по вертикалям
│   ├── content/blog/           # MDX-посты блога
│   ├── lib/
│   │   ├── auth/               # NextAuth v5 config
│   │   ├── db/                 # Prisma клиент, pg Pool, Kysely клиенты
│   │   ├── email/              # Email-сервис (Resend + Nodemailer)
│   │   └── ...                 # Утилиты, permissions, валидация
│   ├── platform/               # Бизнес-логика public schema
│   ├── tenants/                # Мульти-арендное ядро
│   ├── types/                  # Глобальные типы
│   └── verticals/              # Бизнес-логика каждой вертикали
│       ├── beauty/
│       ├── security/
│       └── yacht/
├── scripts/                    # Утилитарные скрипты
│   ├── db/                     # Скрипты БД
│   ├── dev/                    # Dev-скрипты
│   ├── public/                 # Мигратор public schema
│   └── tenant/                 # Tenant-скрипты
└── tests/
    └── e2e/                    # Playwright e2e тесты
Ключевые файлы

Файл	Назначение
src/proxy.ts	Middleware для проброса tenant-заголовков
src/tenants/resolver.ts	Разрешение арендатора
src/tenants/registry.ts	Реестр вертикалей
src/lib/auth/config.ts	Конфигурация NextAuth
src/lib/db/kysely/client.ts	Фабрика Kysely-клиентов
src/lib/db/pool.ts	Единый pg Pool
src/lib/email/index.ts	Email-сервис
migrations/templates/security/up.sql	Полный шаблон схемы Security
UI / Дизайн-система

Проект использует Apple-inspired дизайн-систему (описана в DESIGN_SYSTEM.md):

Минималистичные макеты с большим количеством whitespace
Нейтральная палитра (neutral-950 → neutral-50)
Шрифт Inter / Geist Variable
Скругления: rounded-full (кнопки), rounded-xl (поля), rounded-2xl (карточки)
Анимации: Framer Motion с spring-физикой
Пресс-эффект: active:scale-[0.98]
shadcn/ui

21 UI-компонент на базе Radix Primitives
Стиль: radix-nova
Цветовая схема: neutral
Команды и скрипты

Разработка

npm run dev              # Запуск dev-сервера
npm run build            # Production-сборка
npm run start            # Запуск production-сервера
npm run lint             # Линтинг
База данных (public schema)

npm run db:push          # Prisma db push
npm run db:migrate       # Prisma migrate deploy
npm run db:studio        # Prisma Studio
npm run db:generate      # Prisma generate
npm run db:seed          # Сидирование
npm run public:migrate   # Миграция public schema (кастомный SQL-раннер)
Kysely (tenant schemas)

npm run generate:kysely:beauty    # Генерация типов для beauty (сверка схемы)
npm run generate:kysely:security  # Генерация типов для security
npm run generate:kysely:yacht     # Генерация типов для yacht
npm run generate:kysely           # Генерация для всех вертикалей
npm run db:generate-client        # Генерация Prisma/DB-клиентов (tsx)
npm run db:generate-kysely-types  # Генерация Kysely-типов (tsx)
Tenant-операции

npm run tenant:create     # Создание нового арендатора
npm run tenant:migrate    # Прогон миграций для tenant-схем
npm run tenant:baseline   # Пометить все миграции как применённые (для свежих тенантов из шаблона)
npm run tenant:seed       # Сидирование tenant-схемы
Окружение и переменные

Основные переменные среды (см. .env.example):

База данных:

DATABASE_URL — PostgreSQL connection string
Аутентификация:

AUTH_SECRET — секрет для JWT
AUTH_GOOGLE_ID, AUTH_GOOGLE_SECRET — Google OAuth
AUTH_GITHUB_ID, AUTH_GITHUB_SECRET — GitHub OAuth
Email:

RESEND_API_KEY — ключ Resend
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS — SMTP (Gmail)
EMAIL_FROM — адрес отправителя
DEBUG_EMAIL — режим отладки (логирование без отправки)
Вертикали (feature-флаги):

NEXT_PUBLIC_FEATURE_BEAUTY (Салон красоты) — включение вертикали
NEXT_PUBLIC_FEATURE_SECURITY (Охранное предприятие) — включение вертикали
NEXT_PUBLIC_FEATURE_YACHT (Яхт-клуб) — включение вертикали
true (по умолчанию) — вертикаль отображается в навигации лендинга и в форме регистрации
false — вертикаль полностью скрывается: пилюля не показывается в шапке лендинга, пункт отсутствует при регистрации, а страницы /verticals/{vertical} (включая тарифы) возвращают 404. Запись в выключенную вертикаль блокируется на сервере (registration.service.ts)
Флаги публичные: NEXT_PUBLIC_ встраиваются в клиентский бандл при сборке. На Vercel задавайте тип Config, а не Secret — это не секреты. После смены значения нужен передеплой (env читается на этапе сборки)
Прочее:

GEOAPIFY_API_KEY — ключ геокодирования
NEXT_PUBLIC_TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY — Cloudflare Turnstile
TELEGRAM_ERROR_BOT_TOKEN — токен Telegram-бота для критических ошибок
ADMIN_EMAIL, ADMIN_PASSWORD — доступ к /admin
Разработка

Требования

Node.js >= 18
PostgreSQL 14+
Быстрый старт

# 1. Установка зависимостей
npm install

# 2. Настройка окружения
cp .env.example .env

# 3. Заполните .env — обязательно указать DATABASE_URL

# 4. Инициализация public schema
npm run db:push

# 5. Миграция public schema
npm run public:migrate

# 6. Генерация Kysely-типов для tenant-схем
npm run generate:kysely

# 7. Dev-сервер
npm run dev
Создание нового арендатора

npm run tenant:create
Прогон tenant-миграций

npm run tenant:migrate
Добавление новой миграции

Создать SQL-файл в migrations/tenant/{vertical}/NNN_description.sql
Запустить npm run tenant:migrate
Сгенерировать новые Kysely-типы: npm run generate:kysely
Лицензия

Private. All rights reserved.

