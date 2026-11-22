function app() {
  const today = () => new Date().toISOString().split('T')[0];
  return {
    supabase: null,
    supabaseReady: false,
    authReady: false,
    authenticated: false,
    token: '',
    userEmail: '',
    section: 'dashboard',
    authMode: 'login',
    loginForm: { email: '', password: '' },
    signupForm: { email: '', password: '', confirm: '' },
    forgotEmail: '',
    recoveryForm: { password: '', confirm: '' },
    loginLoading: false,
    loginError: '',
    authMessage: '',
    toasts: [],
    delConfirm: { show: false, label: '', cb: null },
    loading: { dashboard: false, transactions: false, fixed: false, debts: false, investments: false },
    dash: {},
    transactions: [],
    txYear: new Date().getFullYear(),
    txMonth: new Date().getMonth() + 1,
    txFilter: 'all',
    txModal: false,
    txEdit: null,
    txForm: { description: '', amount: '', type: 'expense', category_id: '', date: today(), notes: '' },
    categories: [],
    fixedExpenses: [],
    fixedYear: new Date().getFullYear(),
    fixedMonth: new Date().getMonth() + 1,
    fixedModal: false,
    fixedEdit: null,
    fixedForm: { name: '', amount: '', due_day: '', category: 'Outros' },
    debts: [],
    debtModal: false,
    debtEdit: null,
    showInactive: false,
    debtForm: {
      name: '',
      creditor: '',
      total_amount: '',
      paid_amount: 0,
      installments: '',
      remaining_installments: '',
      monthly_payment: '',
      interest_rate: '',
      due_day: '',
      due_date: '',
      notes: ''
    },
    payModal: false,
    payTarget: null,
    payForm: { amount: '', date: today(), notes: '' },
    investments: [],
    invModal: false,
    invEdit: null,
    invSearch: '',
    invFilter: 'all',
    invStatus: 'all',
    invSort: 'net_desc',
    invViewMode: 'cards',
    invForm: {
      name: '',
      institution: '',
      type: 'CDB',
      invested_amount: '',
      rate: '',
      rate_type: 'prefixado',
      start_date: today(),
      end_date: '',
      notes: ''
    },
    syncingSelic: false,
    settings: {},
    cpForm: { cur: '', nw: '', cf: '' },
    monthNames: [
      'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ],

    get txFiltered() {
      return this.txFilter === 'all'
        ? this.transactions
        : this.transactions.filter(t => t.type === this.txFilter);
    },
    get txStats() {
      const inc = this.transactions.filter(t => t.type === 'income').reduce((a, t) => a + t.amount, 0);
      const exp = this.transactions.filter(t => t.type === 'expense').reduce((a, t) => a + t.amount, 0);
      return { income: inc, expense: exp, balance: inc - exp };
    },
    get fixedStats() {
      const total = this.fixedExpenses.reduce((a, f) => a + f.amount, 0);
      const paidItems = this.fixedExpenses.filter(f => f.paid);
      const paid = paidItems.reduce((a, f) => a + (f.paid_amount || f.amount), 0);
      const pct = total > 0 ? Math.round(paid / total * 100) : 0;
      return { total, paid, pending: total - paid, pct, paidCount: paidItems.length, totalCount: this.fixedExpenses.length };
    },
    get activeDebts() {
      return this.debts.filter(d => d.active);
    },
    get inactiveDebts() {
      return this.debts.filter(d => !d.active);
    },
    get debtStats() {
      const a = this.activeDebts;
      return {
        remaining: a.reduce((s, d) => s + d.total_amount - d.paid_amount, 0),
        paid: a.reduce((s, d) => s + d.paid_amount, 0),
        monthly: a.reduce((s, d) => s + (d.monthly_payment || 0), 0)
      };
    },
    get invStats() {
      const a = this.invFiltered;
      const invested = a.reduce((s, i) => s + (i.invested_amount || 0), 0);
      const current = a.reduce((s, i) => s + (i.current_value !== undefined ? i.current_value : (i.invested_amount || 0)), 0);
      const net = a.reduce((s, i) => s + (i.net_value !== undefined ? i.net_value : (i.current_value || i.invested_amount || 0)), 0);
      const totalTax = a.reduce((s, i) => s + (i.total_tax || 0), 0);
      const totalIof = a.reduce((s, i) => s + (i.iof_amount || 0), 0);
      const totalIr = a.reduce((s, i) => s + (i.ir_amount || 0), 0);
      const gain = current - invested;
      const netGain = net - invested;
      const isFiltered = this.invFilter !== 'all' || (this.invSearch && this.invSearch.trim().length > 0) || this.invStatus !== 'all';

      let filterDescription = '';
      if (this.invFilter !== 'all') {
        filterDescription = this.invFilter;
      }
      if (this.invSearch && this.invSearch.trim()) {
        filterDescription = filterDescription ? `${filterDescription} + busca "${this.invSearch.trim()}"` : `Busca "${this.invSearch.trim()}"`;
      }
      if (this.invStatus !== 'all') {
        const stLabel = this.invStatus === 'active' ? 'Ativos' : 'Encerrados';
        filterDescription = filterDescription ? `${filterDescription} (${stLabel})` : `Status: ${stLabel}`;
      }

      return {
        invested,
        current,
        net,
        totalTax,
        totalIof,
        totalIr,
        gain,
        gainPct: invested > 0 ? (gain / invested) * 100 : 0,
        netGain,
        netGainPct: invested > 0 ? (netGain / invested) * 100 : 0,
        count: a.length,
        isFiltered,
        filterDescription
      };
    },

    get invFiltered() {
      let list = this.investments || [];
      if (this.invStatus === 'active') list = list.filter(i => i.active);
      if (this.invStatus === 'ended') list = list.filter(i => !i.active);
      if (this.invFilter !== 'all') list = list.filter(i => i.type === this.invFilter);
      if (this.invSearch && this.invSearch.trim()) {
        const q = this.invSearch.trim().toLowerCase();
        list = list.filter(i =>
          (i.name && i.name.toLowerCase().includes(q)) ||
          (i.institution && i.institution.toLowerCase().includes(q)) ||
          (i.type && i.type.toLowerCase().includes(q))
        );
      }
      return list.slice().sort((a, b) => {
        const aNet = a.net_value !== undefined ? a.net_value : (a.current_value || a.invested_amount || 0);
        const bNet = b.net_value !== undefined ? b.net_value : (b.current_value || b.invested_amount || 0);
        if (this.invSort === 'net_desc') return bNet - aNet;
        if (this.invSort === 'net_asc') return aNet - bNet;
        if (this.invSort === 'gain_desc') return (b.net_gain || 0) - (a.net_gain || 0);
        if (this.invSort === 'invested_desc') return (b.invested_amount || 0) - (a.invested_amount || 0);
        if (this.invSort === 'date_desc') return new Date(b.start_date || 0) - new Date(a.start_date || 0);
        if (this.invSort === 'name_asc') return (a.name || '').localeCompare(b.name || '');
        return 0;
      });
    },

    get invAvailableTypes() {
      const counts = {};
      (this.investments || []).forEach(i => {
        if (i.type) counts[i.type] = (counts[i.type] || 0) + 1;
      });
      return Object.entries(counts).map(([type, count]) => ({ type, count }));
    },

    async init() {
      this.$watch('invFilter', () => {
        if (this.section === 'investments') this.renderInvChart();
      });
      this.$watch('invStatus', () => {
        if (this.section === 'investments') this.renderInvChart();
      });
      await this.initSupabase();
    },

    translateAuthError(msg) {
      if (!msg) return 'Erro de autenticação. Tente novamente.';
      const m = msg.toLowerCase();
      if (m.includes('invalid login credentials')) return 'E-mail ou senha incorretos.';
      if (m.includes('email not confirmed')) return 'Confirme seu e-mail antes de fazer login.';
      if (m.includes('user already registered')) return 'Este e-mail já está cadastrado.';
      if (m.includes('password should be at least')) return 'A senha deve ter pelo menos 6 caracteres.';
      if (m.includes('rate limit') || m.includes('too many requests')) return 'Muitas tentativas. Aguarde alguns instantes e tente novamente.';
      if (m.includes('signups not allowed')) return 'Novos cadastros estão desativados neste projeto.';
      return msg;
    },

    setAuthMode(mode) {
      this.authMode = mode;
      this.loginError = '';
      this.authMessage = '';
    },

    async initSupabase() {
      try {
        const res = await fetch('/api/auth/config');
        const cfg = await res.json();
        if (!cfg.configured || !cfg.supabase_url || !cfg.supabase_anon_key) {
          this.loginError = 'Supabase não configurado no servidor. Defina SUPABASE_URL e SUPABASE_ANON_KEY nas variáveis de ambiente.';
          this.authReady = true;
          return;
        }
        if (!window.supabase || !window.supabase.createClient) {
          this.loginError = 'Falha ao carregar o SDK do Supabase Auth.';
          this.authReady = true;
          return;
        }

        if (!window._supabaseClient) {
          window._supabaseClient = window.supabase.createClient(cfg.supabase_url, cfg.supabase_anon_key, {
            auth: {
              persistSession: true,
              autoRefreshToken: true,
              detectSessionInUrl: true
            }
          });
        }
        this.supabase = window._supabaseClient;
        this.supabaseReady = true;

        const hashParams = new URLSearchParams((window.location.hash || '').replace(/^#/, ''));
        const queryParams = new URLSearchParams(window.location.search || '');
        const urlErrorCode = hashParams.get('error_code') || queryParams.get('error_code');
        const urlErrorDesc = hashParams.get('error_description') || queryParams.get('error_description');
        if (urlErrorCode || urlErrorDesc) {
          if (urlErrorCode === 'otp_expired') {
            this.loginError = 'O link de confirmação expirou ou já foi utilizado. Tente entrar com sua conta ou solicite um novo link.';
          } else {
            this.loginError = this.translateAuthError((urlErrorDesc || urlErrorCode).replace(/\+/g, ' '));
          }
          window.history.replaceState({}, document.title, window.location.pathname);
        }

        const isRecoveryUrl = hashParams.get('type') === 'recovery' ||
          queryParams.get('type') === 'recovery';

        this.supabase.auth.onAuthStateChange(async (event, session) => {
          if (event === 'PASSWORD_RECOVERY') {
            this.token = session?.access_token || '';
            this.userEmail = session?.user?.email || '';
            this.authenticated = false;
            this.authMode = 'recovery';
            this.loginError = '';
            this.authMessage = '';
            return;
          }

          if (event === 'SIGNED_OUT') {
            this.token = '';
            this.userEmail = '';
            this.authenticated = false;
            this.authMode = 'login';
            return;
          }

          if (session?.access_token) {
            this.token = session.access_token;
            this.userEmail = session.user?.email || '';
            if (!this.authenticated && this.authMode !== 'recovery' && !isRecoveryUrl) {
              this.authenticated = true;
              await this.navigate('dashboard');
            }
          }
        });

        const { data: { session } } = await this.supabase.auth.getSession();
        if (isRecoveryUrl) {
          this.authMode = 'recovery';
          this.authenticated = false;
          if (session?.access_token) {
            this.token = session.access_token;
            this.userEmail = session.user?.email || '';
          }
        } else if (session?.access_token) {
          this.token = session.access_token;
          this.userEmail = session.user?.email || '';
          this.authenticated = true;
          await this.navigate('dashboard');
        }
      } catch (e) {
        this.loginError = 'Erro ao inicializar autenticação: ' + (e.message || e);
      } finally {
        this.authReady = true;
      }
    },

    sectionLabel() {
      const m = {
        dashboard: 'Dashboard',
        transactions: 'Transações',
        fixed: 'Contas Fixas',
        debts: 'Dívidas',
        investments: 'Investimentos',
        settings: 'Configurações'
      };
      return m[this.section] || 'Finanças';
    },

    async navigate(sec) {
      this.section = sec;
      const map = {
        dashboard: async () => { await this.loadDash(); },
        transactions: async () => { await this.loadCats(); await this.loadTx(); },
        fixed: async () => { await this.loadFixed(); },
        debts: async () => { await this.loadDebts(); },
        investments: async () => { await this.loadInv(); },
        settings: async () => { await this.loadSettings(); },
      };
      if (map[sec]) await map[sec]();
    },

    async api(method, path, body) {
      if (this.supabase) {
        const { data: { session } } = await this.supabase.auth.getSession();
        if (session?.access_token) {
          this.token = session.access_token;
        }
      }
      const h = { 'Authorization': 'Bearer ' + this.token };
      const opts = { method, headers: h };
      if (body) {
        h['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
      }
      const r = await fetch('/api' + path, opts);
      if (r.status === 401) {
        await this.logout();
        return null;
      }
      let d;
      try {
        d = await r.json();
      } catch (e) {
        d = {};
      }
      if (!r.ok) throw new Error(d.detail || 'Erro inesperado');
      return d;
    },

    async login() {
      if (!this.supabase) return;
      this.loginLoading = true;
      this.loginError = '';
      this.authMessage = '';
      try {
        const { data, error } = await this.supabase.auth.signInWithPassword({
          email: this.loginForm.email.trim(),
          password: this.loginForm.password
        });
        if (error) throw new Error(this.translateAuthError(error.message));
        this.token = data.session.access_token;
        this.userEmail = data.user?.email || this.loginForm.email.trim();
        this.loginForm.password = '';
        this.authenticated = true;
        await this.navigate('dashboard');
      } catch (e) {
        this.loginError = e.message;
      } finally {
        this.loginLoading = false;
      }
    },

    async signup() {
      if (!this.supabase) return;
      this.loginError = '';
      this.authMessage = '';
      if (this.signupForm.password !== this.signupForm.confirm) {
        this.loginError = 'As senhas não coincidem.';
        return;
      }
      if (this.signupForm.password.length < 6) {
        this.loginError = 'A senha deve ter pelo menos 6 caracteres.';
        return;
      }
      this.loginLoading = true;
      try {
        const { data, error } = await this.supabase.auth.signUp({
          email: this.signupForm.email.trim(),
          password: this.signupForm.password,
          options: { emailRedirectTo: window.location.origin }
        });
        if (error) throw new Error(this.translateAuthError(error.message));

        if (data.session?.access_token) {
          this.token = data.session.access_token;
          this.userEmail = data.user?.email || this.signupForm.email.trim();
          this.signupForm = { email: '', password: '', confirm: '' };
          this.authenticated = true;
          await this.navigate('dashboard');
          this.toast('Conta criada com sucesso!');
        } else {
          this.authMessage = 'Conta criada! Verifique sua caixa de entrada para confirmar o e-mail antes de entrar.';
          this.signupForm = { email: '', password: '', confirm: '' };
        }
      } catch (e) {
        this.loginError = e.message;
      } finally {
        this.loginLoading = false;
      }
    },

    async requestPasswordReset() {
      if (!this.supabase) return;
      this.loginLoading = true;
      this.loginError = '';
      this.authMessage = '';
      try {
        const { error } = await this.supabase.auth.resetPasswordForEmail(
          this.forgotEmail.trim(),
          { redirectTo: window.location.origin }
        );
        if (error) throw new Error(this.translateAuthError(error.message));
        this.authMessage = 'Se este e-mail estiver cadastrado, enviamos um link para redefinir sua senha.';
      } catch (e) {
        this.loginError = e.message;
      } finally {
        this.loginLoading = false;
      }
    },

    async completePasswordRecovery() {
      if (!this.supabase) return;
      this.loginError = '';
      this.authMessage = '';
      if (this.recoveryForm.password !== this.recoveryForm.confirm) {
        this.loginError = 'As senhas não coincidem.';
        return;
      }
      if (this.recoveryForm.password.length < 6) {
        this.loginError = 'A senha deve ter pelo menos 6 caracteres.';
        return;
      }
      this.loginLoading = true;
      try {
        const { error } = await this.supabase.auth.updateUser({
          password: this.recoveryForm.password
        });
        if (error) throw new Error(this.translateAuthError(error.message));
        this.recoveryForm = { password: '', confirm: '' };
        window.history.replaceState({}, document.title, window.location.pathname);
        this.authMode = 'login';
        const { data: { session } } = await this.supabase.auth.getSession();
        if (session?.access_token) {
          this.token = session.access_token;
          this.userEmail = session.user?.email || '';
          this.authenticated = true;
          await this.navigate('dashboard');
          this.toast('Senha redefinida com sucesso!');
        } else {
          this.authMessage = 'Senha redefinida! Agora faça login com sua nova senha.';
        }
      } catch (e) {
        this.loginError = e.message;
      } finally {
        this.loginLoading = false;
      }
    },

    async logout() {
      if (this.supabase) {
        try {
          await this.supabase.auth.signOut();
        } catch (e) {}
      }
      this.token = '';
      this.userEmail = '';
      this.authenticated = false;
      this.authMode = 'login';
    },

    async loadDash() {
      this.loading.dashboard = true;
      try {
        this.dash = await this.api('GET', '/dashboard');
        this.$nextTick(() => this.renderCfChart());
      } catch (e) {
        this.toast(e.message, 'error');
      } finally {
        this.loading.dashboard = false;
      }
    },

    renderCfChart() {
      const el = document.getElementById('cashflowChart');
      if (!el || !this.dash.cashflow) return;
      if (window._cf) window._cf.destroy();
      window._cf = new Chart(el, {
        type: 'bar',
        data: {
          labels: this.dash.cashflow.map(c => c.label),
          datasets: [
            {
              label: 'Entradas',
              data: this.dash.cashflow.map(c => c.income),
              backgroundColor: '#0f766e',
              borderRadius: 6,
              borderSkipped: false
            },
            {
              label: 'Saídas',
              data: this.dash.cashflow.map(c => c.expense),
              backgroundColor: '#94a3b8',
              borderRadius: 6,
              borderSkipped: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                usePointStyle: true,
                padding: 16,
                font: { family: 'Inter', size: 11 }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: '#f8fafc' },
              ticks: { callback: v => 'R$' + v.toLocaleString('pt-BR') }
            },
            x: {
              grid: { display: false }
            }
          }
        }
      });
    },

    async loadCats() {
      try {
        this.categories = await this.api('GET', '/categories');
      } catch (e) {}
    },

    async loadTx() {
      this.loading.transactions = true;
      try {
        this.transactions = await this.api('GET', '/transactions?year=' + this.txYear + '&month=' + this.txMonth);
      } catch (e) {
        this.toast(e.message, 'error');
      } finally {
        this.loading.transactions = false;
      }
    },

    async prevTxMonth() {
      if (this.txMonth === 1) {
        this.txMonth = 12;
        this.txYear--;
      } else {
        this.txMonth--;
      }
      await this.loadTx();
    },

    async nextTxMonth() {
      if (this.txMonth === 12) {
        this.txMonth = 1;
        this.txYear++;
      } else {
        this.txMonth++;
      }
      await this.loadTx();
    },

    openTxModal(tx = null) {
      this.txEdit = tx;
      this.txForm = tx
        ? {
            description: tx.description,
            amount: tx.amount,
            type: tx.type,
            category_id: tx.category_id || '',
            date: tx.date,
            notes: tx.notes || ''
          }
        : {
            description: '',
            amount: '',
            type: 'expense',
            category_id: '',
            date: today(),
            notes: ''
          };
      this.txModal = true;
    },

    async saveTx() {
      try {
        const b = {
          ...this.txForm,
          amount: parseFloat(this.txForm.amount),
          category_id: this.txForm.category_id || null
        };
        if (this.txEdit) {
          await this.api('PUT', '/transactions/' + this.txEdit.id, b);
          this.toast('Transação atualizada!');
        } else {
          await this.api('POST', '/transactions', b);
          this.toast('Transação criada!');
        }
        this.txModal = false;
        await this.loadTx();
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    deleteTx(id) {
      this.delConfirm = {
        show: true,
        label: 'esta transação',
        cb: async () => {
          try {
            await this.api('DELETE', '/transactions/' + id);
            this.toast('Excluída!');
            await this.loadTx();
          } catch (e) {
            this.toast(e.message, 'error');
          }
        }
      };
    },

    async loadFixed() {
      this.loading.fixed = true;
      try {
        this.fixedExpenses = await this.api('GET', '/fixed-expenses?year=' + this.fixedYear + '&month=' + this.fixedMonth);
      } catch (e) {
        this.toast(e.message, 'error');
      } finally {
        this.loading.fixed = false;
      }
    },

    async prevFixedMonth() {
      if (this.fixedMonth === 1) {
        this.fixedMonth = 12;
        this.fixedYear--;
      } else {
        this.fixedMonth--;
      }
      await this.loadFixed();
    },

    async nextFixedMonth() {
      if (this.fixedMonth === 12) {
        this.fixedMonth = 1;
        this.fixedYear++;
      } else {
        this.fixedMonth++;
      }
      await this.loadFixed();
    },

    openFixedModal(fe = null) {
      this.fixedEdit = fe;
      this.fixedForm = fe
        ? { name: fe.name, amount: fe.amount, due_day: fe.due_day, category: fe.category }
        : { name: '', amount: '', due_day: '', category: 'Outros' };
      this.fixedModal = true;
    },

    async saveFixed() {
      try {
        const b = {
          ...this.fixedForm,
          amount: parseFloat(this.fixedForm.amount),
          due_day: parseInt(this.fixedForm.due_day)
        };
        if (this.fixedEdit) {
          await this.api('PUT', '/fixed-expenses/' + this.fixedEdit.id, b);
          this.toast('Conta fixa atualizada!');
        } else {
          await this.api('POST', '/fixed-expenses', b);
          this.toast('Conta fixa criada!');
        }
        this.fixedModal = false;
        await this.loadFixed();
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    async toggleFixedPaid(fe) {
      try {
        const paid = !fe.paid;
        await this.api('PUT', '/fixed-expenses/' + fe.id + '/payment/' + this.fixedYear + '/' + this.fixedMonth, {
          paid,
          paid_date: paid ? today() : null,
          paid_amount: paid ? fe.amount : null
        });
        this.toast(paid ? '✓ Marcada como paga!' : 'Desmarcada');
        await this.loadFixed();
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    deleteFixed(id) {
      this.delConfirm = {
        show: true,
        label: 'esta conta fixa',
        cb: async () => {
          try {
            await this.api('DELETE', '/fixed-expenses/' + id);
            this.toast('Excluída!');
            await this.loadFixed();
          } catch (e) {
            this.toast(e.message, 'error');
          }
        }
      };
    },

    async loadDebts() {
      this.loading.debts = true;
      try {
        const data = await this.api('GET', '/debts');
        if (Array.isArray(data)) {
          const cachedOrder = this.getSavedDebtOrder();
          const hasDistinctServerOrder = data.some(d => d.display_order && d.display_order > 0);
          if (!hasDistinctServerOrder && cachedOrder && Array.isArray(cachedOrder) && cachedOrder.length > 0) {
            const orderMap = new Map();
            cachedOrder.forEach((id, idx) => orderMap.set(id, idx));
            data.sort((a, b) => {
              const ordA = orderMap.has(a.id) ? orderMap.get(a.id) : 9999;
              const ordB = orderMap.has(b.id) ? orderMap.get(b.id) : 9999;
              return ordA - ordB;
            });
          }
          this.debts = data;
        }
        this.$nextTick(() => {
          this.initDebtsSortable();
        });
      } catch (e) {
        this.toast(e.message, 'error');
      } finally {
        this.loading.debts = false;
      }
    },

    openDebtModal(d = null) {
      this.debtEdit = d;
      this.debtForm = d
        ? {
            name: d.name,
            creditor: d.creditor || '',
            total_amount: d.total_amount,
            paid_amount: d.paid_amount,
            installments: d.installments || '',
            remaining_installments: d.remaining_installments || '',
            monthly_payment: d.monthly_payment || '',
            interest_rate: d.interest_rate || '',
            due_day: d.due_day || '',
            due_date: d.due_date || '',
            notes: d.notes || ''
          }
        : {
            name: '',
            creditor: '',
            total_amount: '',
            paid_amount: 0,
            installments: '',
            remaining_installments: '',
            monthly_payment: '',
            interest_rate: '',
            due_day: '',
            due_date: '',
            notes: ''
          };
      this.debtModal = true;
    },

    async saveDebt() {
      try {
        const b = {
          ...this.debtForm,
          total_amount: parseFloat(this.debtForm.total_amount),
          paid_amount: parseFloat(this.debtForm.paid_amount) || 0,
          installments: this.debtForm.installments ? parseInt(this.debtForm.installments) : null,
          remaining_installments: this.debtForm.remaining_installments ? parseInt(this.debtForm.remaining_installments) : null,
          monthly_payment: this.debtForm.monthly_payment ? parseFloat(this.debtForm.monthly_payment) : null,
          interest_rate: this.debtForm.interest_rate ? parseFloat(this.debtForm.interest_rate) : null,
          due_day: this.debtForm.due_day ? parseInt(this.debtForm.due_day) : null,
          due_date: this.debtForm.due_date || null
        };
        if (this.debtEdit) {
          await this.api('PUT', '/debts/' + this.debtEdit.id, b);
          this.toast('Dívida atualizada!');
        } else {
          await this.api('POST', '/debts', b);
          this.toast('Dívida cadastrada!');
        }
        this.debtModal = false;
        await this.loadDebts();
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    deleteDebt(id) {
      this.delConfirm = {
        show: true,
        label: 'esta dívida',
        cb: async () => {
          try {
            await this.api('DELETE', '/debts/' + id);
            this.toast('Excluída!');
            await this.loadDebts();
          } catch (e) {
            this.toast(e.message, 'error');
          }
        }
      };
    },

    openPayModal(d) {
      this.payTarget = d;
      this.payForm = { amount: d.monthly_payment || '', date: today(), notes: '' };
      this.payModal = true;
    },

    async savePay() {
      try {
        await this.api('POST', '/debts/' + this.payTarget.id + '/payments', {
          amount: parseFloat(this.payForm.amount),
          date: this.payForm.date,
          notes: this.payForm.notes || null
        });
        this.toast('Pagamento registrado!');
        this.payModal = false;
        await this.loadDebts();
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    debtColor(pct) {
      return pct >= 75 ? '#047857' : pct >= 40 ? '#b45309' : '#b91c1c';
    },

    getSavedDebtOrder() {
      try {
        const val = localStorage.getItem('debts_custom_order');
        return val ? JSON.parse(val) : null;
      } catch (e) {
        return null;
      }
    },

    initDebtsSortable() {
      const el = document.getElementById('debtsList');
      if (!el) return;
      if (typeof Sortable === 'undefined') {
        console.warn('SortableJS não foi carregado.');
        return;
      }
      if (this._debtsSortable) {
        this._debtsSortable.destroy();
        this._debtsSortable = null;
      }
      this._debtsSortable = new Sortable(el, {
        animation: 200,
        handle: '.debt-drag-handle',
        draggable: '.debt-card',
        ghostClass: 'debt-sortable-ghost',
        chosenClass: 'debt-sortable-chosen',
        dragClass: 'debt-sortable-drag',
        delay: 50,
        delayOnTouchOnly: true,
        touchStartThreshold: 5,
        filter: 'button:not(.debt-drag-handle), .btn, .btn-sm, a, input, select, textarea',
        preventOnFilter: false,
        onEnd: async (evt) => {
          if (evt.oldDraggableIndex === evt.newDraggableIndex) return;
          await this.handleDebtReorder();
        }
      });
    },

    async handleDebtReorder() {
      const el = document.getElementById('debtsList');
      if (!el) return;
      const cardEls = el.querySelectorAll('.debt-card');
      const orderedIds = Array.from(cardEls)
        .map(card => parseInt(card.getAttribute('data-id')))
        .filter(id => !isNaN(id));

      if (orderedIds.length === 0) return;

      // Atualiza display_order nos objetos locais e reordena a lista
      const orderMap = new Map();
      orderedIds.forEach((id, idx) => orderMap.set(id, idx));

      this.debts.forEach(d => {
        if (orderMap.has(d.id)) {
          d.display_order = orderMap.get(d.id);
        }
      });

      this.debts.sort((a, b) => {
        const ordA = orderMap.has(a.id) ? orderMap.get(a.id) : (a.display_order ?? 9999);
        const ordB = orderMap.has(b.id) ? orderMap.get(b.id) : (b.display_order ?? 9999);
        return ordA - ordB;
      });

      // Persistência local (funciona mesmo sem servidor recarregado)
      try {
        localStorage.setItem('debts_custom_order', JSON.stringify(orderedIds));
      } catch (e) {}

      // Persistência no servidor
      try {
        await this.api('PUT', '/debts/reorder', { debt_ids: orderedIds });
      } catch (err) {
        try {
          await this.api('POST', '/debts/reorder', { debt_ids: orderedIds });
        } catch (err2) {
          console.warn('Servidor offline ou endpoint pendente de reload:', err2);
        }
      }
    },

    async loadInv() {
      this.loading.investments = true;
      try {
        await this.loadSettings();
        this.investments = await this.api('GET', '/investments');
        this.$nextTick(() => this.renderInvChart());
      } catch (e) {
        this.toast(e.message, 'error');
      } finally {
        this.loading.investments = false;
      }
    },

    filterByChartType(type) {
      if (this.invFilter === type) {
        this.invFilter = 'all';
      } else {
        this.invFilter = type;
      }
      this.renderInvChart();
    },

    clearInvFilters() {
      this.invFilter = 'all';
      this.invSearch = '';
      this.invStatus = 'all';
      this.renderInvChart();
    },

    renderInvChart() {
      const el = document.getElementById('invChart');
      if (!el) return;
      let a = this.investments || [];
      if (this.invStatus === 'active') a = a.filter(i => i.active);
      else if (this.invStatus === 'ended') a = a.filter(i => !i.active);
      else a = a.filter(i => i.active);

      if (!a.length) {
        if (window._iv) {
          window._iv.destroy();
          window._iv = null;
        }
        return;
      }

      const byType = {};
      a.forEach(i => {
        byType[i.type] = (byType[i.type] || 0) + (i.invested_amount || 0);
      });

      const labels = Object.keys(byType);
      const values = Object.values(byType);

      const baseColors = [
        '#0f172a', '#0f766e', '#2563eb', '#475569', '#d97706',
        '#0284c7', '#64748b', '#4f46e5', '#94a3b8'
      ];

      const hexToRgba = (hex, alpha) => {
        let c = hex.replace('#', '');
        if (c.length === 3) c = c.split('').map(x => x + x).join('');
        const num = parseInt(c, 16);
        return `rgba(${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}, ${alpha})`;
      };

      const isSegmentSelected = this.invFilter !== 'all' && labels.includes(this.invFilter);

      const backgroundColors = labels.map((lbl, idx) => {
        const col = baseColors[idx % baseColors.length];
        if (!isSegmentSelected) return col;
        return lbl === this.invFilter ? col : hexToRgba(col, 0.22);
      });

      const offsets = labels.map(lbl => (isSegmentSelected && lbl === this.invFilter ? 10 : 0));
      const borderWidths = labels.map(lbl => (isSegmentSelected && lbl === this.invFilter ? 3 : 2));
      const borderColors = labels.map(lbl => (isSegmentSelected && lbl === this.invFilter ? '#0f172a' : '#ffffff'));

      if (window._iv) window._iv.destroy();

      window._iv = new Chart(el, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: backgroundColors,
            borderWidth: borderWidths,
            borderColor: borderColors,
            offset: offsets,
            hoverOffset: 12
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '70%',
          onClick: (event, elements, chart) => {
            if (elements && elements.length > 0) {
              const index = elements[0].index;
              const clickedType = chart.data.labels[index];
              this.filterByChartType(clickedType);
            } else {
              if (this.invFilter !== 'all') {
                this.filterByChartType('all');
              }
            }
          },
          onHover: (event, elements) => {
            if (event && event.native && event.native.target) {
              event.native.target.style.cursor = (elements && elements.length > 0) ? 'pointer' : 'default';
            }
          },
          plugins: {
            legend: {
              position: 'bottom',
              onClick: (event, legendItem) => {
                const clickedType = legendItem.text;
                this.filterByChartType(clickedType);
              },
              labels: {
                usePointStyle: true,
                padding: 12,
                color: '#475569',
                font: { family: 'Inter', size: 11, weight: '500' }
              }
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const label = context.label || '';
                  const val = context.raw || 0;
                  const total = context.dataset.data.reduce((x, y) => x + y, 0);
                  const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0';
                  return ` ${label}: R$ ${val.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} (${pct}%)`;
                }
              }
            }
          }
        }
      });
    },

    openInvModal(inv = null) {
      this.invEdit = inv;
      this.invForm = inv
        ? {
            name: inv.name,
            institution: inv.institution || '',
            type: inv.type,
            invested_amount: inv.invested_amount,
            rate: inv.rate,
            rate_type: inv.rate_type,
            start_date: inv.start_date,
            end_date: inv.end_date || '',
            notes: inv.notes || ''
          }
        : {
            name: '',
            institution: '',
            type: 'CDB',
            invested_amount: '',
            rate: '',
            rate_type: 'prefixado',
            start_date: today(),
            end_date: '',
            notes: ''
          };
      this.invModal = true;
    },

    onInvTypeChange() {
      if (this.invForm.type === 'Tesouro Selic' || this.invForm.type === 'Tesouro Reserva') {
        this.invForm.rate_type = 'selic';
      } else if (this.invForm.type === 'Tesouro IPCA') {
        this.invForm.rate_type = 'ipca';
      }
    },

    async saveInv() {
      try {
        const b = {
          ...this.invForm,
          invested_amount: parseFloat(this.invForm.invested_amount),
          rate: parseFloat(this.invForm.rate),
          end_date: this.invForm.end_date || null
        };
        if (this.invEdit) {
          await this.api('PUT', '/investments/' + this.invEdit.id, b);
          this.toast('Investimento atualizado!');
        } else {
          await this.api('POST', '/investments', b);
          this.toast('Investimento cadastrado!');
        }
        this.invModal = false;
        await this.loadInv();
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    deleteInv(id) {
      this.delConfirm = {
        show: true,
        label: 'este investimento',
        cb: async () => {
          try {
            await this.api('DELETE', '/investments/' + id);
            this.toast('Excluído!');
            await this.loadInv();
          } catch (e) {
            this.toast(e.message, 'error');
          }
        }
      };
    },

    async loadSettings() {
      try {
        this.settings = await this.api('GET', '/settings');
      } catch (e) {}
    },

    async saveSettings() {
      try {
        const b = {
          email_host: this.settings.email_host,
          email_port: parseInt(this.settings.email_port),
          email_user: this.settings.email_user,
          email_to: this.settings.email_to,
          cdi_rate: parseFloat(this.settings.cdi_rate),
          ipca_rate: parseFloat(this.settings.ipca_rate),
          selic_rate: this.settings.selic_rate !== undefined && this.settings.selic_rate !== '' ? parseFloat(this.settings.selic_rate) : null,
          alerts_enabled: this.settings.alerts_enabled === 'true' || this.settings.alerts_enabled === true
        };
        if (this.settings.email_password && !this.settings.email_password.includes('•')) {
          b.email_password = this.settings.email_password;
        }
        await this.api('PUT', '/settings', b);
        this.toast('Configurações salvas!');
        await this.loadSettings();
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    async syncSelicRate() {
      this.syncingSelic = true;
      try {
        const res = await this.api('POST', '/settings/sync-selic');
        if (res && res.rate) {
          this.settings.selic_rate = res.rate;
          if (res.last_update) this.settings.selic_last_update = res.last_update;
        }
        this.toast(res.message || 'Taxa Selic atualizada pelo Banco Central!');
        await this.loadInv();
      } catch (e) {
        this.toast(e.message || 'Erro ao sincronizar taxa Selic', 'error');
      } finally {
        this.syncingSelic = false;
      }
    },

    async testEmail() {
      try {
        await this.api('POST', '/settings/test-email', {});
        this.toast('E-mail de teste enviado!');
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    async changePass() {
      if (!this.supabase) return;
      if (this.cpForm.nw !== this.cpForm.cf) {
        this.toast('As senhas não coincidem', 'error');
        return;
      }
      if (!this.cpForm.nw || this.cpForm.nw.length < 6) {
        this.toast('A nova senha deve ter pelo menos 6 caracteres', 'error');
        return;
      }
      try {
        if (this.cpForm.cur && this.userEmail) {
          const { error: checkErr } = await this.supabase.auth.signInWithPassword({
            email: this.userEmail,
            password: this.cpForm.cur
          });
          if (checkErr) {
            this.toast('Senha atual incorreta.', 'error');
            return;
          }
        }
        const { error } = await this.supabase.auth.updateUser({
          password: this.cpForm.nw
        });
        if (error) throw new Error(this.translateAuthError(error.message));
        this.toast('Senha alterada com sucesso!');
        this.cpForm = { cur: '', nw: '', cf: '' };
      } catch (e) {
        this.toast(e.message, 'error');
      }
    },

    doDelete() {
      if (this.delConfirm.cb) this.delConfirm.cb();
      this.delConfirm = { show: false, label: '', cb: null };
    },

    fmt(v) {
      if (v === null || v === undefined) return 'R$ 0,00';
      const n = Math.abs(parseFloat(v) || 0);
      return (v < 0 ? '− ' : '') + 'R$ ' + n.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    },

    fmtS(v) {
      const n = Math.abs(parseFloat(v) || 0);
      const prefix = (parseFloat(v) || 0) < 0 ? '− ' : '';
      if (n >= 1000000) return prefix + 'R$ ' + (n / 1000000).toFixed(1) + 'M';
      if (n >= 1000) return prefix + 'R$ ' + (n / 1000).toFixed(1) + 'K';
      return this.fmt(v);
    },

    fmtDate(d) {
      if (!d) return '—';
      const p = d.split('-');
      return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : d;
    },

    fmtPct(v) {
      return (parseFloat(v) || 0).toFixed(2).replace('.', ',') + ' %';
    },

    rateLabel(rt) {
      return rt === 'prefixado' ? 'a.a.' : rt === 'cdi' ? '% CDI' : rt === 'selic' ? '+ SELIC' : '+ IPCA';
    },

    formatRate(inv) {
      if (!inv) return '';
      if (inv.rate_type === 'prefixado') return inv.rate + '% a.a.';
      if (inv.rate_type === 'cdi') return inv.rate + '% do CDI';
      if (inv.rate_type === 'ipca') return inv.rate > 0 ? ('IPCA + ' + inv.rate + '% a.a.') : 'IPCA';
      if (inv.rate_type === 'selic') {
        const r = parseFloat(inv.rate) || 0;
        if (r === 0) return 'SELIC (100%)';
        return r > 0 ? ('SELIC + ' + r + '% a.a.') : ('SELIC ' + r + '% a.a.');
      }
      return inv.rate + '% ' + this.rateLabel(inv.rate_type);
    },

    getIP() {
      return window.location.hostname;
    },

    getAppUrl() {
      return window.location.origin;
    },

    toast(msg, type = 'success') {
      const id = Date.now();
      this.toasts.push({ id, msg, type });
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== id);
      }, 3500);
    },
  };
}
