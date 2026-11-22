-- ============================================================================
-- Financas Pessoais - Schema PostgreSQL para Supabase (Multi-usuario + RLS)
-- Execute este arquivo no SQL Editor do painel do Supabase.
-- ============================================================================

-- 1. Categorias
CREATE TABLE IF NOT EXISTS public.categories (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    color TEXT DEFAULT '#6366f1',
    CONSTRAINT uq_categories_user_name UNIQUE (user_id, name)
);
CREATE INDEX IF NOT EXISTS idx_categories_user_id ON public.categories (user_id);

-- 2. Transacoes
CREATE TABLE IF NOT EXISTS public.transactions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    category_id INTEGER REFERENCES public.categories(id) ON DELETE SET NULL,
    date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON public.transactions (user_id, date DESC);

-- 3. Contas Fixas
CREATE TABLE IF NOT EXISTS public.fixed_expenses (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    due_day INTEGER NOT NULL CHECK (due_day BETWEEN 1 AND 31),
    category TEXT DEFAULT 'Outros',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fixed_expenses_user_id ON public.fixed_expenses (user_id);

-- 4. Pagamentos de Contas Fixas
CREATE TABLE IF NOT EXISTS public.fixed_expense_payments (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    expense_id INTEGER NOT NULL REFERENCES public.fixed_expenses(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    paid BOOLEAN DEFAULT FALSE,
    paid_date DATE,
    paid_amount DOUBLE PRECISION,
    CONSTRAINT uq_fixed_payment_period UNIQUE (expense_id, year, month)
);
CREATE INDEX IF NOT EXISTS idx_fixed_expense_payments_user_id ON public.fixed_expense_payments (user_id);

-- 5. Dividas
CREATE TABLE IF NOT EXISTS public.debts (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    creditor TEXT,
    total_amount DOUBLE PRECISION NOT NULL,
    paid_amount DOUBLE PRECISION DEFAULT 0.0,
    installments INTEGER,
    remaining_installments INTEGER,
    monthly_payment DOUBLE PRECISION,
    interest_rate DOUBLE PRECISION,
    due_day INTEGER,
    due_date DATE,
    active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_debts_user_order ON public.debts (user_id, display_order ASC);

-- 6. Pagamentos de Dividas
CREATE TABLE IF NOT EXISTS public.debt_payments (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    debt_id INTEGER NOT NULL REFERENCES public.debts(id) ON DELETE CASCADE,
    amount DOUBLE PRECISION NOT NULL,
    date DATE NOT NULL,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_debt_payments_user_debt ON public.debt_payments (user_id, debt_id);

-- 7. Investimentos
CREATE TABLE IF NOT EXISTS public.investments (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    institution TEXT,
    type TEXT NOT NULL,
    invested_amount DOUBLE PRECISION NOT NULL,
    rate DOUBLE PRECISION NOT NULL,
    rate_type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_investments_user_id ON public.investments (user_id);

-- 8. Configuracoes por Usuario
CREATE TABLE IF NOT EXISTS public.app_settings (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT,
    CONSTRAINT uq_app_settings_user_key UNIQUE (user_id, key)
);
CREATE INDEX IF NOT EXISTS idx_app_settings_user_key ON public.app_settings (user_id, key);

-- ============================================================================
-- Row Level Security (RLS) - Defesa em profundidade no Supabase
-- ============================================================================
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fixed_expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fixed_expense_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.debts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.debt_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'categories',
        'transactions',
        'fixed_expenses',
        'fixed_expense_payments',
        'debts',
        'debt_payments',
        'investments',
        'app_settings'
    ]
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS "Users manage own %s" ON public.%I;', tbl, tbl);
        EXECUTE format(
            'CREATE POLICY "Users manage own %s" ON public.%I FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);',
            tbl,
            tbl
        );
    END LOOP;
END $$;
