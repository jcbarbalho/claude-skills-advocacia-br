---
name: caso-novo
description: Abre caso novo no escritório em duas trilhas — A (êxito direto, o cliente já fechou) ou B (negociação, com proposta e funil de vendas) — e, no aceite, cria a pasta, o intake, o cadastro e a pasta no sistema de gestão, a tarefa de conferência, a procuração, o contrato e o registro de honorários. Use quando o advogado disser "caso novo", "abre o caso do Fulano", "pode abrir", "fechou com X", "X aceitou", "faz uma proposta para Y", ou quando a triagem trouxer documentos de cliente que ainda não tem pasta.
argument-hint: "[nome do cliente] [contra quem] [A | B]"
---

# /caso-novo — do primeiro contato à pasta aberta

Roteiro de abertura de caso de um escritório cível. A ordem importa: **procurar antes de criar**,
**negociar antes de abrir a pasta** e **não presumir dado nenhum**. As integrações citadas
(sistema de gestão, gerador de documentos) são do escritório original e não vêm neste
repositório; troque pelos seus.

```
PY="<PYTHON_DO_ESCRITORIO>"
PG="<ESCRITORIO>/scripts"            # criar_intake.py em scripts/intake/ deste repositório
```

**Regra de ouro.** Pasta, ficha do caso, cadastro, tarefa e rascunhos podem ir sem perguntar.
**Enviar proposta ou contrato ao cliente, mandar para assinatura e marcar o negócio como
ganho ou perdido só com o "sim" do advogado**, dado na hora. Nenhum dado de qualificação é
inventado: o que não está em documento fica `[INSERIR: ...]`.

## 0. Antes de tudo: quem é o cliente e qual a trilha

1. **Já existe?** Procurar antes de criar, para não duplicar: a pasta do cliente no acervo (pelo
   sobrenome, com e sem acento), a pessoa e os processos no sistema de gestão, e as notas de
   passagem de turno entre sessões. Cliente antigo com caso novo ganha uma pasta de **caso** dentro
   da pasta dele, e não um cadastro novo.
2. **Homônimo não é o cliente.** Só o primeiro nome, ou um nome igual a outro do acervo, é pessoa
   distinta até o advogado confirmar. Caso real: a qualificação de uma cliente antiga com o mesmo
   primeiro nome foi parar no contrato, na procuração, na ficha e no cadastro da cliente nova.
   Nunca copiar CPF, RG ou endereço de outra ficha.
3. **A pasta é de quem contrata.** A filha contrata a regularização do imóvel e o inventário é da
   mãe: tudo vai na pasta da filha. Duas pastas espalham o mesmo caso, e a próxima sessão acha
   metade. Na ficha, a outra pessoa entra como "parte no processo (relação com o cliente)".
4. **Trilha:**

| A — Êxito direto | B — Negociação |
|---|---|
| "já fechou", "êxito", "pode abrir", "aceitou" | precisa de proposta, há dúvida ou valor a combinar |
| abre tudo agora | entra no funil; a pasta só abre depois do aceite |

Na dúvida, B. Faça **uma** pergunta ao advogado, com tudo o que falta de uma vez: nome completo,
contra quem, modalidade e valor dos honorários.

## Trilha B — Negociação

1. **Negócio no funil** do sistema de gestão (no original, um CRM com as etapas Contato inicial →
   Reunião marcada → Proposta enviada → Negociação). O negócio leva:
   - título "<Cliente> — <assunto>" e a pessoa (cadastro existente, ou só o nome);
   - na descrição: resumo do caso, data de entrada, termos da proposta e caminho da pasta;
   - valor estimado, origem (indicação, parceria) e previsão de fechamento, se houver.
2. **Proposta de honorários** com as modalidades pertinentes (êxito, mensal, por etapa, fixo), no
   estilo do escritório e no papel timbrado, com a mesma régua de espaçamento das peças. Nome:
   `Proposta de Honorários - <Cliente> - <Assunto>_<IA>_v1`.
3. **Enviada** (pelo advogado, ou pela IA com o "sim" dele) → mover o negócio para "Proposta
   enviada". Proposta é extrajudicial, e o extrajudicial não tem captura de andamentos: **o
   retorno do cliente precisa de data agendada**, senão ninguém volta a ele.
4. **Aceite** → negócio ganho; recusa ou desistência → perdido, com o motivo (é o que mostra depois
   onde o funil vaza). Seguir para a Trilha A.

## Trilha A — Abrir o caso

1. **Pastas**: `<Cliente>/` com `Documentos/`, `Peças/` e `Honorários/`. Cliente com mais de um caso:
   `<Cliente>/<Caso>/` com as três dentro. Nome em caixa mista, como no documento. No Windows, caminho
   perto de 240 caracteres quebra script e Word: encurte o nome do caso.
2. **Ficha do caso**: skill [`/intake`](../intake/SKILL.md), passo 2 (`criar_intake.py`). Nasce
   `completo: false`; preencha o que já se sabe.
3. **Sistema de gestão**:
   - pessoa: buscar pelo CPF/CNPJ; não havendo, cadastrar como cliente (a parte contrária, como
     parte contrária);
   - pasta do caso, com cliente, parte contrária e partes. Sem número CNJ é **caso**; o processo
     entra quando houver número;
   - tarefa "Conferir organização e documentos na pasta" para o próximo dia útil;
   - o trabalho até o protocolo (minutar, revisar, documentação pendente, protocolar) é tarefa na
     pasta. Concluída, marca-se na descrição; tarefa não se exclui, porque o histórico é o controle.
4. **Procuração** do modelo do escritório: os procuradores que de fato atuam, poderes ad judicia et
   extra com receber, dar quitação e nomear preposto (essencial no JEC). Finalidade só "distribuição
   de ação em face de <adversário>", **sem narrar os fatos**: a procuração não é a inicial, e o
   que ela narra pode ser usado contra o cliente. Flexão de gênero conferida.
5. **Contrato de honorários**: modalidade e valor **confirmados pelo advogado**. O percentual de
   êxito não se presume.
6. **Controle de honorários**: registrar o contrato (modalidade, valor, forma, próximo vencimento)
   onde a rotina de cobrança lê.

## Nomes de arquivo

- Contencioso: `<Tipo> - <Cliente> X <Adversário>_<IA>_v1`; consultivo: `<Tipo> - <Cliente> - <Assunto>_<IA>_v1`.
- `<IA>` é o sufixo de quem gerou (uma sigla por assistente, para saber de onde veio cada minuta).
  A revisão humana troca o sufixo por `_rev` + iniciais; a versão final, `_rev<iniciais> - Final`.
- Cliente corporativo com dezenas de casos pode ter regra própria (o nome da empresa primeiro).

## Saída

Ao advogado, curto:
```
✓ Pasta: <caminho>
✓ Ficha: criada (completo: false; falta [INSERIR] ...)
✓ Sistema: pessoa <id> · pasta <aberta/falta> · tarefa de conferência <data>
✓ Rascunhos: procuração, contrato (ou proposta) em <caminho>
✓ Honorários: registrado / falta valor
⏳ Com o seu "sim": enviar ao cliente / assinatura / marcar o negócio ganho
```
