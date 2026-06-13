# Tasks

## Feitas ✅
- ✅ na tela de minhas-escalas o status da escala no modo claro não dava para enxergar (badges com fundo escuro + texto escuro no modo claro — corrigido no theme.css)
- ✅ mostrar no painel do líder os impedimentos (seção "Pendências aguardando você" com impedimentos e trocas + card de contagem)
- ✅ na página de desistência, mostrar os usuários disponíveis para cobrir o furo (lista aparece antes de aprovar)
- ✅ melhorar as páginas de escalação (events/N/detail e equip/N/escalas/N) — cartão-resumo com status/avatar, pendências como alerta (tinha HTML quebrado com <td> solto), visual unificado nas duas
- ✅ home: download da agenda (.ics) só aparece se a pessoa tiver escalas; senão mostra "Quando você for escalado, o download aparece aqui"
- ✅ refatorar os cards da home — formato horizontal (ícone + título + descrição curta + seta), textos simplificados


http://localhost:8000/api/equip/1/escalas/4

de uma melhrada no modal de escalar alguem da equipe sem ter disponibilidade e tb de uma melhorada na parte de ususarios disponiveis e usuarios escaladas para ficar parecido com o resto da pagina
- ✅ padronizar telefones — formato canônico só dígitos com DDD sem +55 (migração 0007 corrige os existentes); signup e edição normalizam/validam; perfil ganhou "Atualizar contato" (email + telefone); exibição formatada (21) 99999-9999

## Backlog / ideias
- Confirmação por WhatsApp/Telegram (modelos Notification já preveem canal)
- Disponibilidade recorrente ("todo domingo de manhã")

---
chmod -R 755 staticfiles/
