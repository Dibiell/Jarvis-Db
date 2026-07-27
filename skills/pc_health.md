# PC Health Monitoring Skill

Este módulo permite que o Jarvis monitore a integridade e o desempenho do hardware em tempo real.

## Capacidades
- **Monitoramento de CPU**: Porcentagem de uso em tempo real.
- **Monitoramento de RAM**: Memória utilizada e disponível.
- **Monitoramento de Disco**: Espaço em disco e atividade.
- **Alertas de Voz**: Notificações automáticas ao ultrapassar limites críticos (ex: CPU > 90% ou RAM > 95%).

## Comandos Típicos
- "Jarvis, como está o desempenho do computador?"
- "Qual o uso de CPU agora?"
- "O sistema está sobrecarregado?"
- "Monitore a saúde do PC."

## Instruções para o Jarvis
Sempre que o usuário perguntar sobre o sistema ou desempenho, use os dados fornecidos pelo módulo `psutil` (injetados no seu contexto) para dar uma resposta técnica porém amigável. Se os níveis estiverem críticos, sugira ações como fechar programas pesados.
