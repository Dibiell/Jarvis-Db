# Skill: claude-mem (Claude-nem)

Esta skill fornece uma camada de memória persistente e semântica para o JARVIS.

## Capacidades:
- **Resumo Semântico**: Captura ações e decisões importantes para futuras sessões.
- **Prevenção de "Context Rot"**: Garante que o Jarvis lembre do estado anterior do projeto.
- **Busca Histórica**: Permite pesquisar por decisões tomadas em conversas passadas.

## Como funciona:
O Jarvis salvará automaticamente insights e fatos no diretório `/memory` e os consultará no início de cada sessão (via `CLAUDE.md`).
