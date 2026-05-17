# 🤖 BiFinanças — Agente Financeiro Pessoal no Telegram
### Stack 100% gratuita: Gemini API + Northflank + Google Sheets

---

## ✅ O que esse bot faz

- 📝 Registra gastos e entradas por **texto**, **áudio** e **foto de nota fiscal**
- 🧠 Interpreta linguagem natural ("gastei 45 no mercado no nubank")
- 💳 Detecta forma de pagamento (5 cartões, pix, débito, dinheiro, TED)
- 📦 Gerencia parcelas automaticamente
- 🎯 Acompanha metas (reserva de emergência, dívida com os pais)
- ⭐ Wishlist com prioridade e simulador de compras parceladas
- 📊 Score financeiro, resumo mensal e relatório completo com IA
- ⚠️ Alertas de vencimento, orçamento estourado e lembrete de poupar

---

## 💰 Custo mensal: R$ 0,00

| Serviço | Gratuito? | Limite |
|---|---|---|
| Telegram Bot | ✅ sempre | ilimitado |
| Google Gemini API | ✅ sempre | 1.500 req/dia |
| Northflank (hospedagem) | ✅ always-on | uso pessoal |
| Google Sheets | ✅ sempre | ilimitado |

---

## 📋 Passo a Passo

### 1. Bot no Telegram (5 min)
1. Abra o Telegram → pesquise **@BotFather**
2. Mande `/newbot`
3. Nome: `BiFinanças` | Username: `bifinancas_bot` | Username: `bifinancas_bot`
4. Guarde o token: `7234567890:AAF...`

**Descobrir seu User ID:**
1. Pesquise **@userinfobot** no Telegram
2. Mande qualquer mensagem → ele responde com seu ID numérico

---

### 2. Gemini API (5 min)
1. Acesse **aistudio.google.com**
2. Clique em **Get API Key → Create API Key**
3. Guarde: `AIzaSy...`
4. **Não precisa de cartão de crédito**

---

### 3. Google Sheets (10 min)

**Criar a planilha:**
1. Acesse **sheets.google.com**
2. Crie nova planilha → nomeie "BiFinanças 2026"
3. As 7 abas serão criadas automaticamente pelo bot no primeiro uso
4. Copie o ID da URL:
   `docs.google.com/spreadsheets/d/**ESTE_ID**/edit`

**Credenciais (conta de serviço):**
1. Acesse **console.cloud.google.com**
2. Crie projeto: "bifinancas"
3. **APIs e Serviços → Biblioteca** → ative:
   - Google Sheets API
   - Google Drive API
4. **APIs e Serviços → Credenciais → + Criar Credencial → Conta de Serviço**
5. Nome: `bifinancas-sheets` → Criar
6. Clique na conta criada → **Chaves → Adicionar chave → JSON** → Baixar
7. Abra o JSON, copie o `client_email`
8. Na sua planilha → **Compartilhar** → cole o email → permissão **Editor**

---

### 4. GitHub (5 min)
1. Crie conta em **github.com**
2. **+ → New repository** → nome: `bifinancas` → **Private** → Criar
3. Suba todos os arquivos desta pasta (exceto `.env`)

---

### 5. Northflank (10 min)
1. Acesse **northflank.com** → criar conta gratuita
2. **New Project → New Service → Combined Service**
3. Conecte sua conta GitHub → selecione o repositório `bifinancas`
4. Runtime: **Python** | Start command: `python bot.py`
5. Vá em **Environment → Add Variable** para cada variável:

| Variável | Valor |
|---|---|
| `TELEGRAM_TOKEN` | Token do BotFather |
| `GEMINI_API_KEY` | Chave do Google AI Studio |
| `GOOGLE_SHEETS_ID` | ID da sua planilha |
| `GOOGLE_CREDENTIALS_JSON` | Conteúdo inteiro do JSON (em uma linha) |
| `ALLOWED_USER_ID` | Seu ID numérico do Telegram |

**Como colocar o JSON em uma linha:**
- Abra o arquivo JSON no bloco de notas
- Selecione tudo → Copiar → Cole no campo do Northflank

6. Clique **Deploy** → aguarde ficar verde ✅

---

### 6. Testar
1. Abra o Telegram → pesquise seu bot
2. Mande `/start`
3. Teste: `"gastei 45 no mercado no nubank"`
4. Verifique se apareceu na planilha!

---

## 💬 Como usar no dia a dia

### Registrar (texto livre)
```
gastei 45 no mercado no nubank
almocei fora 32 no pix
paguei fatura Santander 1784
comprei tênis 480 em 3x no Santander
abasteci 150 no débito
recebi salário 4820
VA do mês 820
guardei 200 na reserva
paguei 500 pra minha mãe
```

### Por áudio
Mande um áudio falando o gasto — o bot transcreve e registra automaticamente.

### Por foto
Tire foto de nota fiscal, comprovante de pix ou extrato — o bot lê e registra.

### Wishlist
```
quero comprar airfryer 350
adicionar wishlist: notebook 2500 prioridade alta
```

### Simulador
```
vale a pena comprar TV 2000 em 12x?
consigo comprar moto 8000 em 24x agora?
```

### Comandos disponíveis
```
/saldo          → saldo do mês atual
/cartoes        → faturas dos 5 cartões
/parcelas       → parcelas ativas
/orcamento      → gastos vs limites por categoria
/metas          → todas as metas
/reserva        → reserva de emergência
/pais           → dívida com seus pais
/wishlist       → lista de desejos
/score          → nota financeira do mês (0-10)
/plano          → plano jun/26–jan/27
/alertas        → alertas ativos
/resumo         → análise do mês com IA
/resumo 2026-07 → resumo de mês específico
/relatorio      → relatório geral completo
/ajuda          → guia completo
```

---

## 🔒 Segurança
- Repositório **privado** no GitHub
- Variáveis de ambiente no Northflank (nunca no código)
- `ALLOWED_USER_ID` impede outros de usar seu bot
- Seus dados ficam no **seu** Google Sheets — não em servidor de terceiros

---

## 🔄 Trocar a IA no futuro (se necessário)
Se precisar trocar o Gemini por outra IA, edite apenas o arquivo `ai_interpreter.py`.
Seus dados no Google Sheets **não são afetados** — eles ficam completamente separados.

---

## ❓ Problemas comuns

**Bot não responde:**
- Verifique se o Northflank está rodando (status verde)
- Confirme o `TELEGRAM_TOKEN`

**Erro ao salvar na planilha:**
- Verifique se compartilhou a planilha com o email da conta de serviço
- Confirme o `GOOGLE_SHEETS_ID` e `GOOGLE_CREDENTIALS_JSON`

**Gemini não funciona:**
- Verifique a `GEMINI_API_KEY` no Google AI Studio
- O bot ainda funciona com o parser local para mensagens simples

**"Não autorizado":**
- Verifique o `ALLOWED_USER_ID` — use `0` para desativar temporariamente
