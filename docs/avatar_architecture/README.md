# Documentação da Arquitetura Avatar

Esta pasta contém a documentação detalhada da arquitetura para integração de agentes IA com avatares 3D usando Python e Unity.

## Documentos Disponíveis

### [overview.md](overview.md)
Visão geral da arquitetura, princípios fundamentais e diagrama conceitual da separação entre cérebro (Python) e corpo (Unity).

### [layers.md](layers.md)
Detalhamento das três camadas principais do sistema: IA (Python), Comunicação e Unity (Avatar Engine).

### [technologies.md](technologies.md)
Lista completa das tecnologias necessárias, incluindo versões, bibliotecas e requisitos de hardware.

### [development_plan.md](development_plan.md)
Plano de desenvolvimento passo a passo, dividido em 7 fases desde a configuração básica até a integração com streaming.

### [project_organization.md](project_organization.md)
Estrutura organizacional do projeto, com exemplos de código para os principais componentes.

### [best_practices.md](best_practices.md)
Boas práticas de desenvolvimento, incluindo princípios de design, performance, segurança e manutenção.

### [final_result.md](final_result.md)
Descrição do sistema completo resultante, benefícios alcançados e possibilidades de expansão futura.

## Navegação Rápida

- **Novo no projeto?** Comece com [overview.md](overview.md)
- **Quer implementar?** Siga o [development_plan.md](development_plan.md)
- **Precisa de código?** Veja [project_organization.md](project_organization.md)
- **Dúvidas sobre design?** Consulte [best_practices.md](best_practices.md)

## Arquitetura Resumida

```
Python (Cérebro) ↔ WebSocket ↔ Unity (Corpo) ↔ OBS (Streaming)
     ↓                        ↓                        ↓
   IA/LLM                  Comunicação              Captura
   Emoções                 Tempo Real              Transmissão
   TTS                     Bidirecional           Cenário
```

Para mais detalhes, consulte cada documento específico.