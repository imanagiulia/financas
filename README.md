# 💰 Finanças Pessoais

Aplicação web multi-usuário para acompanhar **dívidas, entradas/saídas, contas fixas e investimentos em renda fixa**, pronta para hospedagem na **Vercel** com banco de dados **PostgreSQL** e autenticação via **Supabase**.

## 🧱 Stack

- **Backend:** FastAPI (Python 3.12+) com SQLAlchemy 2.0
- **Banco de Dados:** Supabase PostgreSQL (com suporte a Row Level Security e isolamento por `user_id`)
- **Autenticação:** Supabase Auth (Login, Cadastro, Recuperação e Alteração de senha com validação JWT via JWKS)
- **Frontend:** HTML + Tailwind CSS + Alpine.js + Chart.js + `@supabase/supabase-js`
- **Hospedagem & Agendamentos:** Vercel Functions + Vercel Schedules (`vercel.json`)

---

## 1️⃣ Configurar o Supabase

1. Crie um projeto gratuito em [supabase.com](https://supabase.com).
2. No menu lateral, acesse **SQL Editor** → **New query**, cole o conteúdo de [`supabase/schema.sql`](supabase/schema.sql) e execute (**Run**).
   - Isso cria todas as tabelas com `user_id` (`UUID` referenciando `auth.users`), índices e políticas de **Row Level Security (RLS)**.
3. Obtenha suas chaves no painel do Supabase:
   - **Project Settings → Data API / API Keys:**
     - `SUPABASE_URL` (Project URL)
     - `SUPABASE_ANON_KEY` (Publishable / `anon` public key)
   - **Connect (botão no topo) → Transaction pooler (porta `6543`):**
     - Copie a URI PostgreSQL para `DATABASE_URL` (use o **Transaction Pooler** na Vercel, pois oferece compatibilidade IPv4 e pooling otimizado para serverless).
     - Exemplo: `postgresql://postgres.<PROJECT_REF>:<SENHA>@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require`
4. Em **Authentication → URL Configuration**:
   - Defina **Site URL** com a URL da sua aplicação na Vercel (ex.: `https://seu-projeto.vercel.app`).
   - Adicione também `http://localhost:8000` em **Redirect URLs** se for testar localmente.
5. *(Opcional — uso pessoal exclusivo)*: se quiser impedir que outras pessoas criem conta no seu deploy público, vá em **Authentication → Sign In / Providers → Email** e desative **"Allow new users to sign up"** depois de criar a sua própria conta.

---

## 2️⃣ Migrar dados locais do `financas.db` (Opcional)

Se você já usava a versão local em SQLite (`financas.db`), siga estes passos após criar sua conta no Supabase Auth:

1. Preencha seu arquivo `.env` local (copiando de `.env.example`) com a `DATABASE_URL` do Supabase.
2. Faça primeiro uma simulação (`--dry-run`) para conferir a contagem de registros:
   ```bash
   python scripts/migrate_sqlite_to_supabase.py --dry-run
   ```
3. Execute a migração informando o e-mail da conta criada no Supabase Auth (ou `--user-id <UUID>`):
   ```bash
   python scripts/migrate_sqlite_to_supabase.py --email seu-email@exemplo.com
   ```
   *(Se precisar reimportar do zero para o mesmo usuário, adicione `--replace`.)*

---

## 3️⃣ Subir o projeto para o GitHub

O arquivo [`.gitignore`](.gitignore) já bloqueia `.env` e `financas.db` para que suas senhas e dados financeiros nunca sejam enviados ao repositório.

```bash
git init
git add .
git status   # Confirme que .env e financas.db NAO aparecem na lista
git commit -m "chore: prepara projeto para GitHub, Vercel e Supabase"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
git push -u origin main
```

---

## 4️⃣ Hospedar na Vercel

1. Acesse [vercel.com](https://vercel.com) → **Add New → Project** e importe o repositório do GitHub.
2. A Vercel detecta automaticamente o `main.py` (FastAPI) e o `requirements.txt` sem configuração extra.
3. Em **Settings → Environment Variables**, adicione:

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | Sim | URI PostgreSQL do **Transaction Pooler** (porta `6543`) do Supabase |
| `SUPABASE_URL` | Sim | URL do projeto Supabase (`https://xxx.supabase.co`) |
| `SUPABASE_ANON_KEY` | Sim | Chave pública (`anon` / `publishable`) do Supabase |
| `CRON_SECRET` | Sim (p/ alertas/Selic) | Segredo aleatório (mín. 16 chars) usado pela Vercel nos agendamentos `/api/cron/*` |
| `SUPABASE_JWT_SECRET` | Opcional | Apenas se seu projeto Supabase usar assinatura JWT legada `HS256` |
| `AUTO_CREATE_TABLES` | Opcional | Pode definir `false` após rodar `supabase/schema.sql` para cold starts ainda mais rápidos |
| `CORS_ORIGINS` | Opcional | Ex.: `https://seu-projeto.vercel.app` (padrão: `*`) |

4. Clique em **Deploy**.

### ⏰ Tarefas Agendadas (Vercel Schedules)

O arquivo [`vercel.json`](vercel.json) configura automaticamente 3 agendamentos no fuso `America/Sao_Paulo`:
- **`daily-selic`** (`30 6 * * *`) → `POST /api/cron/daily-selic` — atualiza a taxa Selic oficial via Banco Central.
- **`daily-alerts`** (`0 8 * * *`) → `POST /api/cron/daily-alerts` — envia e-mails de contas/dívidas a vencer (próximos 7 dias) e investimentos vencendo em 30 dias.
- **`monthly-summary`** (`0 8 1 * *`) → `POST /api/cron/monthly-summary` — envia resumo consolidado no 1º dia de cada mês.

Todos os endpoints `/api/cron/*` exigem o cabeçalho `Authorization: Bearer <CRON_SECRET>`.

---

## 5️⃣ Executar localmente

```bash
# 1. Instale as dependencias
pip install -r requirements.txt

# 2. Copie o .env.example para .env e preencha SUPABASE_URL, SUPABASE_ANON_KEY e DATABASE_URL
copy .env.example .env

# 3. Inicie o servidor local
uvicorn main:app --reload
```

Acesse `http://localhost:8000`.

### Rodar testes automatizados

```bash
python -m unittest discover -s tests -v
```

---

## 📁 Estrutura de Arquivos

```text
financas/
├── app/
│   ├── api/
│   │   ├── router.py        # Agregador central (/api) + /api/health
│   │   └── v1/              # auth, dashboard, transactions, debts, investments, cron, etc.
│   ├── core/                # config, database (PG/NullPool + SQLite), security (JWT/JWKS)
│   └── services/            # regras de negocio (juros, impostos, dashboard, selic, notificacoes, seed)
├── scripts/
│   └── migrate_sqlite_to_supabase.py  # Migracao segura de financas.db -> Supabase Postgres
├── static/                  # Frontend (HTML + Tailwind + Alpine.js + Supabase JS)
├── supabase/
│   └── schema.sql           # DDL PostgreSQL + politicas RLS multi-usuario
├── tests/                   # Testes unitarios (seguranca, isolamento, juros, dividas)
├── main.py                  # Entrypoint FastAPI (auto-detectado pela Vercel)
├── models.py                # Modelos ORM SQLAlchemy (com user_id UUID)
├── schemas.py               # Schemas Pydantic
├── vercel.json              # Configuracao de Vercel Schedules
├── requirements.txt         # Dependencias Python
├── .env.example             # Modelo de variaveis de ambiente
└── .gitignore               # Protege .env e financas.db de irem ao GitHub
```
