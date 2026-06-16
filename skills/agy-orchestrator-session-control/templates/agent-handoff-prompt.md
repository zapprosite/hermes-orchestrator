# Agent Handoff Prompt Template

**Quando usar:** Quando o Hermes (Telegram ou CLITUI) precisa que outro agente —
CLITUI pairado, subagente agy, ou worktree orquestrador — execute uma
configuração/script que o runtime atual não consegue rodar sozinho.

**Padrão (2026-06-15, Will colou no CLITUI pra habilitar toolsets Telegram):**

```
Sou o Hermes <origem>, instância que roda via <interface> no <dispositivo>
do Will (chat_id <id> ou user <user>). Tenho a tool `<tool>` habilitada
no meu runtime e consigo executar comandos shell no host onde o bot/CLI
está rodando (<OS>, user `<user>`, home `<home>`). Já consigo fazer
<evidência de smoke básico> — isso tudo já está provado funcionando.

O que eu NÃO consigo fazer, e o que você precisa configurar para mim:

1. <Habilitar recurso X.>
   <Flag/chave exata, caminho do config, formato YAML, etc.>
   <Validação: como confirmar que funcionou.>

2. <Expor path/env Y.>
   <Onde deveria estar visível e como alinhar.>
   <Comando de validação: which X, ls Y, env | grep Z.>

3. <Carregar skills/recursos no boot.>
   <Lista de skills obrigatórias, caminhos esperados.>
   <Se faltar, recriar a partir de <referência>.>

4. <Smoke test fim-a-fimio.>
   a. <Comando exato que prova o caminho completo.>
   b. <Validação intermediária: log esperado, marker file.>
   c. <Validação final: output esperado.>
   d. <Reportar status real.>

5. <Restrições.>
   <Não quebrar a outra instância (CLITUI/Telegram).>
   <Escopo per-platform, não global.>
   <Safety: read-only em secrets, bind 127.0.0.1, sem rm destrutivo.>

Responda em PT-BR com: (1) diff do que mudou, (2) saída do smoke test,
(3) qualquer risco pro runtime paralelo que eu deva avisar pro Will.
Não bloqueie perguntando — use defaults seguros das skills que citei.
```

## Anatomia do Prompt Eficaz

| Seção | Função | Tamanho típico |
|---|---|---|
| **Identidade + contexto** | Quem eu sou, o que já funciona | 3-4 linhas |
| **O que falta** | Lista numerada de pedidos específicos | 5-8 itens |
| **Comandos de validação** | Como confirmar cada passo | inline nos itens |
| **Smoke test** | Prova fim-a-fimio reproduzível | 5-10 linhas |
| **Restrições** | Não quebrar a outra instância | 2-3 linhas |
| **Formato de resposta** | O que você quer de volta | 1 parágrafo |

## Pitfalls ao Escrever o Handoff

- **Não pedir "configure pra mim"** — sem lista, o outro agente inventa escopo.
- **Sempre incluir comandos de validação** — sem eles, o outro agente "acha que terminou" e reporta OK sem ter verificado.
- **Sempre pedir diff/status real** — não aceitar "tudo configurado". Pedir saída de `ls`, `systemctl status`, `tail <log>`, `git diff`.
- **Escopo per-platform/per-instance** — mudanças globais no `config.yaml` podem quebrar o outro runtime. Sempre lembrar a restrição.
- **Citar skills/paths esperados** — se o outro agente não conhece o caminho exato, ele recria errado.
