---
name: agy-orchestrator-session-control
description: |-
  Protocolo de sessão do Hermes como arquiteto/orquestrador quando delega tarefas
  de code ao motor agy via subagentes. Regra: Hermes NUNCA escreve code de produção
  direto. Sempre: (1) escrever o prompt no formato BLUEPRINT da skill delegate-agy,
  (2) despachar via terminal(background=true) ou kanban_create, (3) salvar a sessão
  no controle interno, (4) voltar imediatamente pro chat com Will com status,
  (5) aguardar a notificação de conclusão (notify_on_complete) e processar o output
  resumido. Manter histórico das sessões ativas pra não perder o fio.
---

# Agy Orchestrator — Controle de Sessão Ativa

## Regra de Ouro (coração desta skill)

> **Hermes = arquiteto, NÃO coder. Eu orquestro, agy produz, Will aprova.**
> Eu nunca escrevo code de produção direto. Eu organizo, empacota o prompt
> no formato BLUEPRINT, despacho pro agy via subagente, e **fico livre pro
> chat com o Will**. O output do agy chega via notificação automática,
> eu processo o resumo e devolvo pro Will em linguagem natural.
> **Não fico olhando processo, não fico perguntando "ainda tá rodando",
> não fico bloqueando o chat do Will com updates vazios.**

**Will reforçou esta regra explicitamente (2026-06-16):** "voce nao pode codar
so arquitetar". Isso é um sinal de primeira-classe: NUNCA escrever `write_file`/
`patch` em código de produção do homelab/voice. Se a tarefa é estrutural (refactor,
multi-arquivo, nova feature, teste, SRE script), ela vai pro kanban como card
atribuído ao perfil certo (`coder`, `devops`, `reviewer`, `researcher`), NÃO
implementada inline por Hermes.

## Fluxo Canônico (6 passos)

### 0. Mineração técnica ANTES de empacotar (skill-level)
Antes de escrever o BLUEPRINT, **ler o terreno real**: SOUL.md, docs canônicos
em `homelab-context/docs/` e `~/.hermes/docs/`, inventário de serviços
`systemctl --user is-active`, ports `ss -ltn`, models instalados
(`find ~/.local/share -name "*.onnx"`), skills carregadas. O objetivo é
descobrir:
- O que está rodando AGORA (não o que a doc diz que deveria rodar)
- Divergências entre canônico pinado, SOTA recebido e estado real
- Paths reais vs paths documentados
- Lixo técnico / redundância / scripts aposentados
Saída: lista de gaps P0-P3 e a arquitetura limpa proposta. Só então
empacotar o BLUEPRINT com base nessa mineração. (Aprendido em 2026-06-16,
Hermes Jarvis SOTA v2 — SOTA recebido tinha paths errados, modelo OWW
inexistente, conflito daemon vs in-session. Sem mineração, o blueprint
teria codado lixo.)

### 1. Esclarecer ambiguidades (1 pergunta, max 4 opções)
Se faltar decisão crítica (stack, escopo, identidade CPF/CNPJ, brand), perguntar
com `clarify` ANTES de empacotar. Não despachar blueprint com decisão em aberto.

### 2. Empacotar BLUEPRINT.md
Usar o template da skill `delegate-agy/templates/agy-blueprint.md` (10-15KB):
- Objetivo
- Identidade & política
- Stack & libs
- Brand/visual
- Modelo de dados
- Endpoints/funções
- Integrações
- Pastas/arquivos
- Variáveis de ambiente (`.env.example` com `{SECRET}`)
- Restrições
- Workflow (branch, commits, smoke, PR)
- Critérios de aceite (checklist verificável)
- Output esperado

Salvar em:
- `/home/will/workspace/<projeto>/BLUEPRINT.md` (se houver repo)
- ou `/tmp/<projeto>-blueprint-<timestamp>.md` (tarefa avulsa)

### 3. Despachar agy em BACKGROUND com notify_on_complete

**Regra 2026-06-16 (Will):** quando a tarefa é multi-agent, multi-arquivo,
ou faz parte de uma decomposição maior, **preferir `kanban_create` com
assignee=perfil apropriado** em vez de `terminal(background)`. Perfis
disponíveis no board `refrimix-content`: `coder`, `devops`, `researcher`,
`reviewer`. Use `kanban_create` + `parents=[...]` para expressar fan-in
fan-out. Reserve `terminal(background)` para tarefas one-shot que rodam
sozinhas.

Para tasks one-shot via agy:

```python
terminal(
    background=True,
    notify_on_complete=True,
    command=f"cd /home/will/workspace/<projeto> && agy -p \"$(cat BLUEPRINT.md)\" --add-dir /home/will/workspace/<projeto> --dangerously-skip-permissions 2>&1 | tee ~/.gemini/antigravity-cli/agy-<timestamp>.log"
)
```

**SEMPRE** background + notify. Nunca foreground com tarefas > 30s.

### 4. Salvar controle de sessão ativa

Imediatamente após despachar, criar entry no controle:

```python
# Estado em memória do Hermes (passive tracking)
active_agy_sessions = {
    "session_id": "proc_abc123",
    "blueprint_path": "/home/will/workspace/refrimix-landing/BLUEPRINT.md",
    "project": "refrimix-landing",
    "dispatched_at": "2026-06-15T17:30:00Z",
    "expected_output": "HTML one-pager em /tmp/refrimix-landing.html",
    "log_path": "~/.gemini/antigravity-cli/agy-20260615_173000.log",
    "status": "running"
}
```

### ⚠️ Dispatch via `agy -p` direto (workaround para `protocol_violation`)

O caminho canônico do dispatcher kanban (`hermes -p <profile> chat -q "work kanban task <tid>"`) tem um problema conhecido com o motor `agy` (Gemini 3.5 Flash High): o worker faz o trabalho mas não chama `kanban_complete`/`kanban_block` no fim, e o dispatcher mata com `protocol_violation`. **Workaround que funcionou (jun/2026):** despachar `agy -p` direto via `terminal(background=true, notify_on_complete=true)`, bypassando o dispatcher.

**Wrapper bash canônico** (criar em `/tmp/agy-<card>-wrapper.sh`):
```bash
#!/usr/bin/env bash
set -e
PROMPT=$(cat <<'PROMPT'
# Tarefa: <TITULO>

**INSTRUÇÃO CRÍTICA**: ao terminar, chame `kanban_complete(summary=..., metadata=...)` ou `kanban_block(reason=...). Sem isso, dispatcher mata por protocol_violation. Use `kanban_show(task_id='<TID>')` para detalhes.

<conteúdo do card>
PROMPT
)
cd /home/will/workspace/<projeto>
agy -p "$PROMPT" --add-dir /home/will/workspace/<projeto> --dangerously-skip-permissions 2>&1
```

Depois despachar via:
```python
terminal(
    background=True,
    notify_on_complete=True,
    command="bash /tmp/agy-<card>-wrapper.sh"
)
```

O orquestrador (Hermes) chama `kanban_complete` no fim ao processar a notificação, sintetizando o output real do worker a partir dos commits no git. **Trade-off:** perde rastreabilidade por card (a notificação vai pro chat, não pro kanban) mas destrava enquanto o problema de tool-calling do `agy` não for resolvido upstream. Receita completa + troubleshooting: `delegate-agy/references/kanban-agy-integration-2026-06.md` §2.1.

**Race condition OAuth (jun/2026):** se for despachar 3+ agy workers, **NÃO em paralelo**. Sequência com `notify_on_complete` ou `sleep 60` entre spawns, senão todos dão `Error: authentication timed out.` em 30s. Detalhes em `delegate-agy/SKILL.md` pitfall "Race condition no reauth Google OAuth".

## 5. Voltar IMEDIATAMENTE pro Will com status curto

Formato da resposta durante o despacho (NÃO durante a espera):

```
**Despachado, Senhor.** ✓
**Tarefa:** <1 linha>
**Sessão:** proc_xyz123
**ETA estimado:** <1-2 min pra tarefas curtas, 5-15 min pra features>
**Aguardei retorno automático.** Continuo aqui pro que precisar.
```

Depois disso: **livre pro chat**. Não bloquear, não poluir com "ainda rodando".

**Forma NEGATIVA do que NÃO fazer (Will foi explícito sobre isso):**
- ❌ `process(action='poll')` em loop até o agy terminar
- ❌ Mensagens no chat tipo "ainda processando...", "aguarde 30s", "quase lá"
- ❌ Pedir confirmação pro Will pra matar o agy sem deixar ele rodar até o fim
- ❌ Implementar manualmente a task "pra adiantar" (só faça manual se for trivial absoluto: 1-2 linhas, HTML estático de 1 arquivo)
- ❌ Escrever code de produção (write_file/patch em `.py`/`.ts`/`.yaml` de feature/voice/stack) — sempre despachar pro agy ou kanban
- ❌ Despachar `agy` direto em vez de `kanban_create` quando a tarefa é multi-agent (Will prefere kanban como controle de orquestração)

## Processar Notificação de Conclusão

Quando o `notify_on_complete` chegar, o handler faz:

1. **Verificar output real** (NUNCA confiar em auto-report):
   - `ls -la <expected_output_path>` (arquivo existe?)
   - `git -C <project> log --oneline -5` (commits granulares?)
   - `tail -30 <log_path>` (agy terminou sem erro?)
   - Se o output for PR: `gh pr view <n>` ou checar Gitea

2. **Sintetizar em linguagem natural pro Will:**

```
**agy terminou, Senhor.** ✓
**Entregue:** /tmp/estudio-conteudo.html (9.0KB)
**Branch:** agent/estudio-studio (se aplicável)
**Smoke:** HTML validado, tags balanceadas
**Output real:** [resumo de 1-2 frases do que foi feito]
**Próximo:** [ação recomendada — merge, validar visual, etc.]
```

3. **Marcar sessão como done** no controle interno.

4. **Se agy falhou** (quota, erro, output missing):
   - Reportar honestamente o que aconteceu
   - Propor alternativa (implementar manualmente se trivial / esperar quota / re-despachar)
   - **NUNCA inventar output que não aconteceu** — política §00 do SOUL.md

## Pitfalls a Evitar

- **Bloquear o chat do Will com "ainda rodando..."** — proibido. Despacha, responde curto, libera.
- **Codar diretamente com Minimax-M3** quando a tarefa é code — proibido. agy é o motor.
- **Esquecer `--add-dir`** — agy perde acesso ao filesystem. Sempre passar path explícito.
- **Esquecer `--dangerously-skip-permissions`** — agy trava pedindo aprovação a cada tool call.
- **Esquecer `notify_on_complete=true`** — fica invisível, Will não recebe nada.
- **Confiar em auto-report "tarefa concluída"** — sempre verificar output real antes de declarar sucesso.
- **Misturar identidades CPF/CNPJ no mesmo blueprint** — sempre uma identidade por task.
- **Push direto em main** — sempre branch `agent/<nome>` + PR + Will aprova.
- **Hardcode de secret no blueprint** — usar `{SECRET}` ou nome de var sem valor.

## Quando o Will Perguntar "como tá aquele agy?"

- Se sessão ativa: `process(action='poll', session_id=...)` e reportar status
- Se sessão já terminou: reler o log_path e o output_path, sintetizar
- Se nunca existiu: admitir que não tem sessão ativa pra essa tarefa

## Tag do release (rito de finalização, jun/2026)

Quando o release atinge 12/12 gates verdes e está pronto pra review do Will,
criar tag anotada em **todos os repos impactados** (não só o repo principal).
Pattern de calibração (release v2 SRE dev-senior, 2026-06-16):

```bash
# Em cada repo (homelab-context, ~/.hermes, hermes-agent-next):
git checkout <branch-final>  # ex: release/hermes-jarvis-sota-v2
git tag -a v2.0.0 -m "Hermes Jarvis SOTA SRE dev-senior — Release v2.0.0 FINAL

Data: 2026-06-16
Status: 12/12 gates SRE verdes, 0 FAIL.

Arquitetura: in-session estrito (Opcao A).
Telemetria: voice-telemetry service ativo (port 4140, 10/11 checks).
Motor de code: agy (Gemini 3.5 Flash High) consolidado.
2 vulnerabilities criticas corrigidas (Redis Tailscale, T2 cloud 404).
Pruning severo aplicado (3 perfis :4018, 5 scripts, 12 testes, 92 skills/archive).

Pytest: 16+1 passed, 1 skipped, 0 failed.

Refs: kanban t_xxx, t_yyy, t_zzz"
git push origin v2.0.0
```

**Importante:** se a tag já existe com nome similar (ex:
`v2.0.0-release-sota-sre`), **deletar antes de recriar** com nome
canônico `v{N}.{M}.{P}`:
```bash
git tag -d v2.0.0-release-sota-sre
git push origin :refs/tags/v2.0.0-release-sota-sre
git tag -a v2.0.0 -m "..."
git push origin v2.0.0
```

**Por que tag em 3 repos:** o release v2 toca homelab-context (docs),
~/.hermes (config + skills) e hermes-agent-next (runtime voice).
Marcar tag em cada um com mensagem contextual ao repo é o que
permite Will navegar o histórico de releases por stack isoladamente.

**Não criar branch `release/...` com nome contendo "release" + tag
"v2.0.0-release-sota-sre" no mesmo tempo** — confusão. Pattern
canônico: `release/<slug-curto>` (branch) + `v{N}.{M}.{P}` (tag).
Diferença: branch tem mudanças em progresso, tag é snapshot imutável
de uma release finalizada.

## When NOT to use

- Mudança trivial de 1-2 linhas (`patch` direto)
- Diagnóstico de 1 comando (terminal)
- Status read-only (mcp_homelab_core, systemctl status)
- Pesquisa/pergunta
- Geração de imagem/áudio/vídeo (skills específicas, não agy)

## Ver também

- **`hermes-architect-orchestrator-role`** (umbrella class-level) — define o papel do
  Hermes como arquiteto/orquestrador puro (regra pinned 2026-06-16 "voce nao pode
  codar so arquitetar"). Esta skill (agy-orchestrator-session-control) é o
  **sub-protocolo** de como despachar e monitorar; a umbrella define **quando** aplicar
  o papel e quando não.
- `delegate-agy` — motor de code, BLUEPRINT template, smoke script, pitfalls de agy
- `delegate-agy/references/jarvis-sota-v2-release-pattern.md` — workflow 7-fases
  completo (caso de calibração SRE dev-sênior)
- `delegate-agy/references/kanban-agy-integration-2026-06.md` — receita da integração
  agy ↔ kanban (settings, custom_providers, profiles, pitfalls)

## Exceções ao "não codar inline" (papel do arquiteto)

O arquiteto **pode** fazer patches limitados em:
- **Configuração do próprio Hermes** (skills, profiles kanban via `hermes config set`,
  settings agy, `.env.example`) — via CLI nativo `hermes config set`, não `patch` direto
- **Documentação de mineração** (`AUDIT_*.md`, `BLUEPRINT.md`, este skill, references) —
  via `write_file`
- **Templates e scripts de skill** (`templates/`, `scripts/`, `references/` de skill
  existente) — via `write_file` ou `patch`, desde que sob a skill que governa aquela
  classe de trabalho
- **Kanban cards** (`kanban_create`, `kanban_complete`, `kanban_comment`) — é a
  superfície de orquestração canônica

**NÃO pode** patchar `.py`/`.ts`/`.yaml` de **feature/voice/stack** — isso vai pro
agy ou kanban.
- Ver `delegate-agy/scripts/agy-smoke.sh` para smoke test do agy em <10s.
