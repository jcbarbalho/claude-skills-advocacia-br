---
name: protocolar
description: Protocola petição intermediária (juntada, manifestação, contestação, recurso, memoriais) pelo LegalMail com o checklist do escritório — registro certo (eproc > PJe, grau), quem peticiona e em que polo, rascunho + resumo para o advogado, envio só após o "sim", e o pós-protocolo (intimações a baixar, intake, Astrea, BASTÃO). Use quando o advogado pedir para protocolar, juntar, peticionar ou "subir" uma peça em processo já existente.
argument-hint: "[CNJ] [peça PDF]"
---

# /protocolar — petição intermediária pelo LegalMail

Motor: `06. Automações\piece_gen\protocolo_lm.py`, rodado com a venv do escritório:

```
PY="<PYTHON_DO_ESCRITORIO>"
S="<ESCRITORIO>/06. Automações/piece_gen/protocolo_lm.py"
```

**Não usar `legalmail_actions.protocolar_peticao()`.** Ela pega o registro velho do PJe em CNJ
migrado, não manda o `fk_documento_auxiliar` que o eproc exige e envia sem parar para o resumo.

Fora do escopo: **distribuição de inicial**, que segue a receita da memória
`legalmail_api_referencia`, bloco "DISTRIBUIÇÃO"; marcação de urgência; e processo não monitorado.

Memória citada pelo nome fica em `<MEMORIA>\<nome>.md`.
Fora do projeto do escritório ela não carrega sozinha: ler o arquivo.

## 0. Antes de tocar na API

1. **Intake do caso.** Ler o `intake.md` da pasta do caso; se for casca (< ~1 KB, "criado
   automaticamente"), reconstruir pela peça. É onde está **quem é o nosso cliente e em que polo**.
2. **Data do protocolo.** Em contestação/defesa, o advogado prefere protocolar **na véspera**
   (encurta réplica e preparo adverso). Não protocolar só porque a peça ficou pronta; confirmar o dia.
3. **Peça final em PDF**, datada (`datar_peca.py`), na pasta do caso. Anexos em PDF; o LegalMail
   adequa outros formatos, mas PDF evita surpresa.
4. **Justiça do Trabalho:** o catálogo não tem "Recurso de Revista" e as partes podem vir
   defasadas. Faltando tipo ou parte, o caminho é o PJe direto (advogado). Não improvisar tipo em recurso.

## 1. Resolver o registro certo

```
"$PY" "$S" resolver <CNJ>
```

- **eproc prevalece sobre PJe.** O registro do PJe congela na migração; protocolar nele é protocolar no lugar errado.
- Dois registros vivos podem ser **graus diferentes** (1º grau × câmara/`dcp`). Escolher pelo juízo
  em que o ato tem de ser praticado. Memoriais e recursos no 2º grau vão no registro da câmara.
- **Não monitorado** → não há rota de API para cadastrar. O advogado cadastra pelo painel ou protocola direto.

## 2. Preparar (cria só o rascunho)

```
"$PY" "$S" preparar --idprocessos <id> --pdf "<peça.pdf>" --anexo "<a1.pdf>" --anexo "<a2.pdf>" \
    --tipo "Petição" --solicitante "<nome ou id de quem peticiona>"
```

- `--tipo`: nome exato do catálogo ("Petição", "Contestação", "Petição Intercorrente"...). Se não
  existir, o script lista os disponíveis.
- `--solicitante`: **o nosso cliente**, conferido no intake. Nunca escolher pelo polo: o cliente pode
  ser réu, executado ou embargante. Ambíguo → usar o id.
- eproc: o script resolve o `fk_documento_auxiliar` pelo nome do tipo; se não achar, pede `--doc-auxiliar`.
- Anexo é tipado pelo nome do arquivo (procuração → "Procuração"; resto → "Outros anexos").
- Falhou no meio → `"$PY" "$S" cancelar <idpeticoes>`. Não deixar rascunho órfão.

## 3. Mostrar o resumo e esperar o "sim"

Colar ao advogado o bloco **RESUMO PARA O ADVOGADO** que o `preparar` imprime: processo, sistema, juízo,
peça, tipo, anexos, **quem peticiona e em que polo**. Esperar confirmação expressa, **mesmo que ele
já tenha pedido o protocolo**. Se o solicitante saiu "NÃO DEFINIDO", rodar de novo com `--solicitante`
e cancelar o rascunho anterior.

## 4. Enviar

```
"$PY" "$S" enviar "<manifesto .json indicado no resumo>"
```

O hook `guarda_protocolo` pede confirmação a cada envio; isso é proposital. O manifesto recusa
segundo envio.

**`success` não prova protocolo.** Dizer "enviada, aguardando confirmação", nunca "protocolada".

## 5. Depois do envio (no mesmo ato)

1. **Intimações a baixar.** O `enviar` já lista as do LegalMail. Entregar ao advogado os `idintimacoes`
   que a peça responde **e** os antigos já superados. A API não baixa intimação; é no painel.
   Vazio em PJe ou em intimação por DJEN é normal.
2. **intake.md**: `atualizado:`, uma linha datada (o que subiu, idpeticoes) e as pendências.
3. **Astrea**: lançar o andamento. Tarefa de follow-up só se o advogado pedir: no judicial, ausência de
   tarefa é decisão dele. Se a peça cumpre uma tarefa, editar prefixando "✅ CONCLUÍDA" (nunca excluir).
4. **BASTÃO**: uma linha no bloco da sessão (caso, peça, idpeticoes, intimações a baixar).
5. **Conferir a juntada** no dia útil seguinte: `"$PY" "$S" conferir --idprocessos <id>`. A lista
   reflete a última importação: "não consta até <data>", nunca "não há".

## Armadilhas que já custaram caro

- Protocolar **antes da publicação** deixa o prazo aberto no LegalMail ("prazo fantasma"). Não
  peticionar de novo para fechá-lo; anotar na tarefa do Astrea.
- Erros 400 da API são oráculo: nomeiam um campo por vez. Ler a mensagem inteira antes de sondar.
- Nome de arquivo acentuado pode voltar "Arquivo corrompido"; o script já manda o nome em ASCII.
