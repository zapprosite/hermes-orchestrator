# Mineração Técnica Pré-Blueprint — Padrão SRE Dev-Sênior

> **Quando usar:** sempre que o briefing vier de "fora" (SOTA avulso, spec externa, doc de terceiro,
> request do Will sem contexto prévio) e a tarefa for arquitetural (multi-subsystem, doc
> fragmentada, motor misto, decisão A/B/C pendente). **NUNCA aceitar cegamente** o input
> como verdade. Cruzar com canônico pinado, filesystem real e serviços rodando.
>
> Caso de calibração: Hermes Jarvis SOTA v2 (2026-06-16). Will pediu: *"voce entendeu seu
> objetivo? ler toda bagunca que os dev juniores deixaram e vamos minerar o que presta
> definir uma arquitetura hermes cli/tui funcionando com um stream de audio usando audio full
> gpu sem fall-back de cpu, ja exite jarvis funcionando e clonado mas e um arquitetura salada
> voce tem que fazer uma mineracao e entregar algo estavel e profissional sem lixos tecnicos,
> algo com telemetria SRE dev senior de verdade."*

## Por que mineração antes de blueprint

Codar direto a partir de um SOTA/spec externo sem cruzar com o real gera:
- Lixo técnico que vira release bloqueante (paths inexistentes, modelos binários fantasma)
- Decisões arquiteturais contraditórias (SOTA diz A, canônico diz B, real roda C)
- Trabalho desperdiçado em arch que ninguém consegue rodar

## Workflow de 6 passos (15-30min de SRE read-only)

### 1. Triagem do briefing (sem ler tudo)

Identificar:
- **Fontes citadas** (canônico pinado? doc terceiro? SOTA avulso? conversa anterior?)
- **Subsystems afetados** (voz? LLM routing? memory? gateway? browser?)
- **Decisões pendentes** (stack? escopo? identidade CPF/CNPJ? in-session vs daemon?)
- **Critérios de aceite** (o que Will considera "estável e profissional"?)

Saída: lista de 5-10 perguntas que precisam ser respondidas pela mineração.

### 2. Inventário automático (filesystem + serviços + runtime)

**Código:**
```bash
# Contagem por módulo (decide o que é KEEP/CUT/REFACTOR)
find /home/will/workspace/homelab-context/modules -name "*.py" -not -path "*__pycache__*" | xargs wc -l | sort -rn
find /home/will/.hermes/hermes-agent-next/agent -maxdepth 1 -name "*.py" -not -path "*__pycache__*" | xargs wc -l | sort -rn

# Tamanho total e arquivos
du -sh /home/will/workspace/homelab-context/modules/<voz>
find ... | wc -l  # total de .py

# Scripts canônicos vs legados
ls -la /home/will/.hermes/scripts/ | wc -l  # 60-80 esperado; >100 = lixo
ls /home/will/.hermes/scripts/ | head -50
```

**Serviços rodando (vs. declarado no canônico):**
```bash
systemctl --user is-active <cada unit> # do HERMES_VOICE_CANONICAL_INVENTORY.md
ss -ltn | grep -E ':8001|:8202|:8765|:7880|:6379|:6378|:6377'  # SSoT ports
ps -eo pid,pcpu,pmem,etime,cmd | grep -iE 'headless_client|wake_oww|openwakeword' | grep -v grep
```

**Paths e modelos binários declarados:**
```bash
# Onde o SOTA disse que está vs. onde realmente está
ls -la /path/declarado_pelo_sota 2>&1
find /home/will -name "<modelo>.onnx" 2>/dev/null
find /home/will -path "*wake*" 2>/dev/null
```

**TTS/STT/LLM saúde:**
```bash
curl -s http://127.0.0.1:8202/v1/audio/voices  # TTS: deve ter 1 voz canônica
curl -s -m 3 -X POST http://127.0.0.1:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen","messages":[{"role":"user","content":"diga ok"}],"max_tokens":5}'
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

### 3. Triângulo Canônico ↔ Real ↔ SOTA (tabela obrigatória)

Para cada tópico com divergência potencial, montar linha de tabela:
| Tópico | Canônico diz | Real mostra | SOTA diz | Decisão |
|---|---|---|---|---|
| Runtime voice | in-session pinned | daemon active | híbrido 24/7 | **A in-session** |
| Modelo OWW | `jarvis_ptbr_user.onnx` em `/data/hermes/wake_models/` | path inexistente | `jarvis_ptbr_user.onnx` CUDA EP | localizar/treinar ou fallback `hey_jarvis_v0.1` |
| TTS voice | `jarvis-clone-trimmed` fail-closed | `voices: ["jarvis-clone-trimmed"]` | bate | KEEP |
| LLM T1 | Qwen 0,35s | 60-130ms | bate | KEEP |
| LLM T2 | MiniMax-M3 | :4018 retorna 401 (morto) | bate | remover 3 perfis órfãos |
| Daemon | aposentado (INVENTORY) | `active` | "híbrido 24/7" | P0 contradiction |

**Diagnóstico típico:** 3-5 divergências em qualquer sistema real. Marcar P0 (bloqueia release),
P1 (atrapalha), P2 (ruído).

### 4. Lixo técnico priorizado

| ID | Item | Path | Ação | Motivo |
|---|---|---|---|---|
| P0-1 | Contradição daemon canônico vs real | `~/.config/systemd/user/*.service` | decidir A/B (parar/reabilitar doc) | INVENTORY diz aposentado, real diz active |
| P1-1 | 3 perfis órfãos | `~/.hermes/config.yaml` | remover | HTTP 401, rejeitados por cloud_tier.py |
| P1-2 | Doc fragmentada | `homelab-context/docs/` | consolidar em 4-5 docs | 3 docs divergindo entre si |
| P1-3 | Path fantasma | `~/.data/hermes/wake_models/*.onnx` | localizar/criar | declarado no LAUNCHER mas não existe |
| P2-1 | Scripts legados | `~/.hermes/scripts/` | mover pra `_archive_<ts>/` | 60+ arquivos, ~30% legados |
| P3-1 | Typos | vários | fix oportunista | cosmético |

### 5. Recomendação de release (decisão única, sem ambiguidade)

Para cada decisão arquitetural pendente, listar 2-3 opções com **prós/contras/risco** e
**recomendação única** baseada em estabilidade medida (soak 24h, smoke gates) +
princípios canônicos pinned. **Nunca** "depende" — Will prefere decisão A com motivo
claro do que "eu não sei".

### 6. Plano de cards kanban

A partir dos gaps P0-P3, criar cards no kanban com:
- **Card 0 (Auditoria)**: este passo de mineração vira deliverable `AUDIT_<TOPIC>_<DATA>.md`
- **Cards 1..N**: um por gap de prioridade, com assignee específico (`coder` para code,
  `devops` para SRE/config, `reviewer` para doc/architecture review, `researcher` para
  pesquisa externa)
- **Card final (PRUNE/Validate)**: fecha o release, valida com gates SRE

Dependências: Card 0 (auditoria) bloqueia 1..N. Card final depende de todos.

**Critério de aceite da mineração:** `AUDIT_<TOPIC>_<DATA>.md` commitado em branch
`agent/<projeto>-audit` com seções TL;DR + inventário bytes/LOC + tabela de divergências
+ P0-P3 priorizado + recomendação única + 6-12 cards planejados.

## Quando NÃO usar mineração

- Tarefa one-shot bem definida (não precisa de inventário de 165 .py)
- Tarefa urgente SRE ("Redis caiu, recupera") — vai direto pro `terminal`
- Tarefa de leitura/pergunta
- Tarefa trivial (1-2 linhas de patch)

## Templates relacionados

- `delegate-agy/templates/agy-blueprint.md` — formato do blueprint que sai DEPOIS da mineração
- `delegate-agy/references/jarvis-sota-v2-release-pattern.md` — workflow 7-fases completo
  que consome este passo 0 + 5 passos seguintes do orchestrator-session-control

## Sinais de que pulei a mineração (anti-patterns)

- Despachar blueprint com paths que não existem no filesystem
- Blueprint com modelo binário que nunca foi baixado
- Decisão arquitetural "vou descobrir durante a execução" (Will odeia)
- Aceitar SOTA externo como verdade sem cruzar com canônico
- Despachar 5+ cards sem `AUDIT_*.md` prévio
