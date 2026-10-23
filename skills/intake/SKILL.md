---
name: intake
description: A ficha viva do caso (intake.md na pasta do caso) em três momentos — LER antes de tudo (conferindo se é real ou casca), CRIAR no caso novo (criar_intake.py, com Dados cadastrais e completo false) e ATUALIZAR depois de cada ato (atualizado, Observações, Pendências). Use ao pegar qualquer caso para analisar intimação, minutar, opinar ou preparar audiência ("abre o caso do Fulano", "o que temos do X?", "lê o intake"); ao abrir caso novo ("caso novo", "cadastra o cliente"); e logo depois de protocolar, enviar ou decidir algo num caso. Também quando o advogado perguntar "você leu o intake?".
argument-hint: "[pasta do caso | nome do cliente | --cnj <nº>] [ler | criar | atualizar | completar]"
---

# /intake — a ficha viva do caso

O `intake.md` é a única fonte que guarda o que **não está nos autos nem no sistema de gestão**: as
decisões do advogado, as correções de premissa, a estratégia escolhida e a qualificação conferida.
Peça, formulário e termo puxam dele. Ficha errada ou vazia contamina tudo que sai a partir dela.

```
PY="<PYTHON_DO_ESCRITORIO>"
PG="<ESCRITORIO>/scripts/intake"     # criar_intake.py e checar_intake.py (scripts/intake/ deste repositório)
```

Memória citada pelo nome fica em `<MEMORIA>\<nome>.md`. Fora do projeto do escritório, ela não
carrega sozinha: ler o arquivo.

**Regra de ouro.** Nunca inventar dado: o que não está na fonte fica `[INSERIR: ...]` ou
`[VERIFICAR: ...]`. A ficha é rascunho e organização, então criar e editar podem ir sem perguntar.
Excluir intake, nunca.

## Onde fica

- `intake.md` na **pasta do CASO** (`<Cliente>\<Caso>\intake.md`), não em `Documentos` ou `Peças`.
  Cliente com um caso só pode ter a ficha na raiz da pasta do cliente.
- A pasta é do **cliente contratante**: a filha contrata, o processo é da mãe, a ficha fica na
  pasta da filha.
- Caso coletivo (vários aderentes da mesma ação) segue regra própria de pasta: uma ficha comum,
  os aderentes numa subpasta.
- Checklists antigos de cliente novo são outra coisa. A ficha viva é o `intake.md`.

## 1. LER: antes dos autos, do sistema de gestão e de qualquer resumo

**"Sempre leia o intake antes."** Antes de analisar intimação, minutar, opinar ou preparar
audiência:

```
"$PY" "$PG/checar_intake.py" "<pasta do caso>"       # ou o intake.md, ou "Nome do Cliente"
"$PY" "$PG/checar_intake.py" --cnj <nº CNJ>           # acha a ficha pelo processo
```
O checador só lê. Ele dá um veredito por ficha:
- **🔴 RECONSTRUIR ANTES DE MINUTAR**: casca, que é `completo: false`, a marca de ficha criada
  automaticamente por uma rotina ou menos de 1 KB. **Intake-casca é pior que intake nenhum**:
  parece documentação e não é. Caso real: uma ficha de 764 bytes foi lida sem estranhamento, e a
  peça saiu com o argumento fraco. O forte (a parte não tinha integrado a ação coletiva) estava na
  versão anterior da peça, na mesma pasta. Ir ao passo 4.
- **🟡 LER E COMPLETAR NO MESMO ATO**: falta Dados cadastrais, CPF/CNPJ, vara, comarca ou
  distribuição; arquivo fora de UTF-8; ou `atualizado:` há mais de 30 dias. Ficha velha engana:
  num caso real, o resumo dizia que a construtora cancelou o contrato, quando quem cancelou foi o
  banco, e o erro chegou aos memoriais. Conferir os andamentos antes de confiar no resumo.
- **OK PARA LER.**

Depois, **abrir e ler a ficha inteira**. O checador não substitui a leitura: ele não sabe o que a
ficha diz, só se ela parece real.

- **Mais de uma matéria do cliente?** Ler todas as fichas da mesma história. Caso real: o aviso
  que valia para a matéria criminal ("alinhar com o advogado da outra frente antes de qualquer peça
  que descreva contatos") estava no intake da matéria de família. O checador lista as outras fichas
  do cliente. Num cliente com dezenas de casos independentes, só as do mesmo fato.
- **Não há ficha?** Ir ao passo 2 e preencher pelos autos ANTES de minutar.
- Ausência de dado no intake **não** é ausência no caso.

## 2. CRIAR: caso novo

Logo depois de criar as pastas `Documentos`, `Peças` e `Honorários`:
```
"$PY" "$PG/criar_intake.py" --pasta "<pasta do caso>" --cliente "<Cliente>" --adversario "<Adversário>" \
     --processo "<nº se houver>" --area "<Consumidor/Sucessões/...>" --papel <autor|reu> --resumo "<1 linha>"
```
- Não sobrescreve ficha existente. `--force` só com o "sim" do advogado, porque apaga o que ela tem.
- A ficha nasce com frontmatter de vault do Obsidian (`tipo: intake`, `processos`, `situacao`,
  **`completo: false`**, `atualizado`) e os blocos Dados cadastrais, Fatos-âncora, O caso,
  Decisões e estratégia, Verbas, Provas, Pendências e Observações.
- **Não renomear os rótulos `- **Rótulo:** valor`**: outros scripts (cálculo de condenação,
  minuta de petição simples, cadastro no sistema de gestão) leem por eles.
- Preencher já o que se sabe. A ficha fica `completo: false` até o passo 4.

## 3. ATUALIZAR: depois de cada ato, no mesmo fluxo

Vale para protocolo, envio, decisão do advogado, reunião, documento recebido e intimação tratada.
Não esperar pedirem.
1. Ler a ficha antes de editar: o advogado e outras sessões também a editam.
2. `atualizado: AAAA-MM-DD` no frontmatter.
3. Linha datada em **Observações / Atualizações**: o que foi feito, com ids (protocolo, evento,
   envelope de assinatura, valores). Formato: `- [AAAA-MM-DD] — <o quê>`.
4. **Pendências**: dar baixa no que se resolveu (`- [x] ✅ ... (data)`) e incluir o que o ato criou.
5. Decisão ou correção de premissa do advogado vai para **Decisões e estratégia**, com a data e as
   palavras dele. É o que mais se perde.

O intake **não substitui** o sistema de gestão: são os dois, a timeline do sistema (cliente e
relatório) e a ficha. E a ficha não gera tarefa: no judicial, a captura de andamentos já avisa; no
extrajudicial, todo ato tem follow-up agendado.

## 4. COMPLETAR uma casca ou uma ficha sem Dados cadastrais

**Todo intake abre com "Dados cadastrais"**, preenchido e em dia.
1. **Fontes, nesta ordem:** inicial e procuração (qualificação); capa e autos (processo, vara,
   distribuição, citação); a peça mais recente da pasta `Peças` (o estado do caso); o relato escrito
   do cliente, que vale como confirmado.
2. **Qualificação completa, copiada como está no documento**: nome exatamente igual (caso real: um
   sobrenome ganhou acento ao ser copiado da ficha, quando a inicial e a procuração o escrevem sem),
   nacionalidade, estado civil, profissão, RG com órgão e UF, CPF, endereço com CEP, e-mail e
   telefone. O mesmo para quem o cliente representa, para a parte contrária e para o advogado dela.
   **Nunca reaproveitar qualificação de homônimo** encontrada no acervo.
3. **Processo:** CNJ, juízo, comarca, classe, valor da causa, data de distribuição, segredo,
   gratuidade.
4. **Fatos-âncora:** evento danoso (data e local), citação (data e forma) e, quando houver,
   audiência, sentença e trânsito.
5. **Fonte de cada dado** no fim da linha: (inicial), (procuração), (CNH), (autos, fls./id/ev.).
6. Só então: `completo: true` no frontmatter e `incompleto` fora das tags. Rodar o checador de novo.

## Saída

Dizer em uma linha qual ficha foi lida e o veredito (ou o que foi criado, atualizado ou
completado), e o que ficou `[INSERIR]` para o advogado, de uma vez só.
