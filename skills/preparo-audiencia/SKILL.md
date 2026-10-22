---
name: preparo-audiencia
description: Prepara o roteiro de uma audiência (conciliação, ACIJ do JEC, AIJ ou preliminar do JECrim) a partir do intake e das peças do caso — pontos controvertidos com ônus e prova, perguntas para o depoimento pessoal e as testemunhas (sem indução, art. 459 CPC), contradita, proposta de acordo, alegações finais orais, checklist de comparecimento/representação e o rascunho da orientação ao cliente. Use quando o advogado disser "preparar a audiência", "roteiro da AIJ", "audiência do Fulano semana que vem", ou quando houver audiência próxima na agenda.
argument-hint: "[cliente ou CNJ] [data]"
---

# /preparo-audiencia

Adaptado do `deposition-prep` do `anthropics/claude-for-legal` (litigation-legal). Ficou a
estrutura (mapa por temas, registro fiel, calibragem oral, não escrever o depoimento de ninguém).
Saiu o que é do direito americano: deposition fora do juízo, discovery, pergunta fechada sugestiva
para "encaixotar" a testemunha. **No Brasil o juiz não admite pergunta que possa induzir a resposta
(art. 459 do CPC)**, então o roteiro de testemunha é de perguntas abertas e neutras, encadeadas.

O produto é um **roteiro interno** em markdown na pasta do caso, mais o rascunho da orientação ao
cliente. Não é peça e não vai a protocolo.

Memória citada pelo nome (`estilo_emails`, `calculo_qual_ferramenta`) fica em
`<MEMORIA>\<nome>.md`. Fora do projeto do escritório ela não carrega
sozinha: ler o arquivo.

## 1. Montar o caso (nesta ordem)

1. **Intake primeiro** (`<cliente>\<caso>\intake.md`). Se for casca (< ~1 KB, "criado
   automaticamente"), reconstruir pela peça mais recente antes de seguir. Caso com pastas irmãs:
   ler o intake de todas.
2. **A audiência:** tipo, data, hora, modalidade (presencial, telepresencial ou híbrida) e juízo.
   Fonte: agenda do Astrea (`astrea_agenda_por_cliente`) e o despacho que designou. Grep do nome
   do caso no BASTÃO.
3. **Peças:** inicial, contestação, réplica e **decisão de saneamento**, que fixa os pontos
   controvertidos e as provas deferidas. Estão em `Peças\` e `Documentos\`. O advogado já leu os autos:
   não baixar a íntegra "para conferir" o que ele descreveu. Baixar só se faltar peça essencial; o
   download dispensa autorização.
4. **Versão do cliente:** o que ele afirmou **por escrito** (e-mail, questionário) é a versão
   confirmada. Não marcar `[CONFIRMAR]` nisso.
5. **Biblioteca Jurídica** quando houver tese do acervo na matéria: acionar o agente
   **pesquisador-biblioteca** ou fazer Grep no espelho
   `<ESCRITORIO>\06. Automações\00_biblioteca\texto\`. Os PONTOS DE
   ATENÇÃO alimentam as alegações finais e os riscos.
6. **Lei:** todo dispositivo citado no roteiro é conferido no corpus `09. Legislação`. Enunciado do
   FONAJE ou do COJES que não esteja no corpus nem registrado na memória ou no BASTÃO leva `[conferir]`.

## 2. Classificar a audiência: o roteiro muda com o tipo

| Tipo | O que importa | Base |
|---|---|---|
| **Conciliação/mediação (CPC)** | presença, representação, proposta de acordo | art. 334, §§ 8º a 10 |
| **ACIJ do JEC** | conciliação e, frustrada, instrução no mesmo ato; contestação e provas ali | Lei 9.099, arts. 20, 33, 34, 51, I |
| **AIJ (rito comum)** | provas orais na ordem do art. 361; alegações finais orais | CPC, arts. 358 a 368 |
| **Preliminar do JECrim** | composição civil e transação penal; efeito de cada uma no cível | Lei 9.099, arts. 68, 72 a 76 |

**Preliminar do JECrim, o que muda:** o roteiro troca provas por **decisão sobre as saídas**.
- **Composição civil** (art. 74): homologada, vira **título executivo no juízo cível**. Só extingue a
  punibilidade em ação privada ou pública condicionada (parágrafo único). Em pública incondicionada
  (contravenção, por exemplo) não extingue nada e ainda fixa valor que repercute na ação cível conexa.
- **Transação penal** (art. 76): não gera reincidência nem consta de antecedentes, impede novo
  benefício por 5 anos (§§ 4º e 6º) e **não tem efeitos civis** (§ 6º). Conferir os impedimentos do
  § 2º antes de recomendar.
- Havendo ação cível conexa: o roteiro traz uma linha comparando cada saída com a estratégia da
  contestação cível. A decisão é do advogado com o cliente.
- O autor do fato comparece com advogado (art. 68). Coautor: alinhar a versão antes, sem combinar
  conteúdo de depoimento.

**Comparecimento e representação, conferir sempre:**
- **JEC, autor ausente** = extinção (art. 51, I). **Réu ausente** = revelia (art. 20).
- JEC até 20 salários mínimos: as partes comparecem pessoalmente (art. 9º).
- **Preposto com carta de preposição é regra do RÉU PJ** (art. 9º, § 4º). ME **autora** é representada
  pela sócia-administradora com contrato social e identidade, não por preposto. Erro já cometido
  no escritório.
- Conciliação no CPC: ausência injustificada é ato atentatório, multa de até 2% (art. 334, § 8º);
  representante só com **procuração específica** com poderes para transigir (§ 10).

## 3. Postura de cada depoente

- **Nosso cliente (depoimento pessoal):** preparar os temas, não as falas. Ele não pode ler escritos
  preparados, só consultar notas breves (art. 387). Intimado sob pena de confesso, ausência ou recusa
  geram a pena (art. 385, § 1º). Quem ainda não depôs não assiste ao depoimento da outra parte
  (art. 385, § 2º).
- **Parte contrária (depoimento pessoal):** perguntas que extraiam admissão dos fatos que ela vai
  ter de reconhecer, documento em mãos. Evasiva vira recusa de depor (art. 386).
- **Nossas testemunhas:** perguntas abertas que deixem a testemunha contar o que viu. Antes, conferir
  o rol e o prazo (art. 357, §§ 4º e 6º; no JEC, até 3, art. 34) e a intimação: carta com AR juntada
  3 dias antes (art. 455, § 1º), ou compromisso de levar, e aí a ausência vale desistência (§ 2º). No
  JEC, o requerimento de intimação vai à Secretaria 5 dias antes (art. 34, § 1º).
- **Testemunhas da outra parte:** primeiro, **contradita** (art. 457, § 1º). Levantar parentesco,
  amizade íntima, inimizade, interesse e vínculo de emprego, e ter a prova à mão (documento, ou até 3
  testemunhas no ato). Depois, perguntas neutras e encadeadas que exponham o limite do que ela sabe:
  onde estava, como soube, o que viu ela mesma. Nunca pergunta que sugira a resposta (art. 459).

**Disciplina inegociável:** não se escreve o depoimento de ninguém nem se ensaia resposta. Orienta-se
sobre forma (ouvir a pergunta inteira, responder só o que sabe, dizer "não sei" ou "não lembro"
quando for o caso) e sobre os temas. A testemunha presta compromisso (art. 458).

## 4. Montar o roteiro

Salvar em `<caso>\Audiência\Roteiro - <tipo> <AAAA-MM-DD>_CB.md` (criar a pasta). Modelo:

```markdown
---
tipo: roteiro-audiencia
caso: <cliente> x <parte contrária>
processo: <CNJ>
audiencia: <tipo> · <data> <hora> · <modalidade> · <juízo>
atualizado: <AAAA-MM-DD>
---

# Roteiro — <tipo> — <cliente> x <parte contrária>

**Objetivo da audiência (uma frase):** o que precisa sair provado ou admitido.
**Nossa tese em uma linha:** ...
**Polo do cliente / quem comparece / representação:** ... (art. 9º, § 4º; contrato social; carta de preposição)

## 1. Pontos controvertidos

| # | Fato controvertido | Quem alega | Ônus (art. 373; CDC, art. 6º, VIII) | Nossa prova | Prova deles | Quem pode falar disso |
|---|---|---|---|---|---|---|

Fonte: saneador (art. 357, II) ou, no JEC, o confronto inicial × contestação. Os 3 ou 4 que decidem
a causa em **negrito**.

## 2. Conciliação
- Valor atualizado do pedido (com o índice certo; ver `calculo_qual_ferramenta`).
- **Piso e teto autorizados pelo cliente:** `[DECISÃO DO ADVOGADO / CLIENTE]` (nunca inventar número).
- O que ganhamos e arriscamos se não houver acordo (as 2 ou 3 razões, sem otimismo).
- Itens não monetários negociáveis (prazo, forma de pagamento, obrigação de fazer, retirada de negativação).

## 3. Depoimento pessoal da parte contrária
Por ponto controvertido: objetivo → documento (fls./evento) → perguntas.

## 4. Testemunhas
### 4.1 Nossas (abertas)
### 4.2 Deles: contradita (fundamento e prova) e perguntas

## 5. Nosso cliente: temas sensíveis
O que vão perguntar, onde a versão dele é frágil, o que ele NÃO deve ampliar.

## 6. Alegações finais orais (até 20 min, art. 364)
3 ou 4 pontos, o mais forte primeiro, cada um amarrado à prova produzida.
No JEC, preparar também a versão de 3 minutos.

## 7. Riscos e decisões a tomar na hora
- ...

## Documentos para ter abertos na audiência
| Doc | fls./evento | Para quê |
|---|---|---|
```

**Fidelidade ao registro:** aspas só para texto que está diante de mim, com fls. ou evento. Sem a
passagem exata: paráfrase sem aspas e `[conferir fls.]`. Uma contradição atribuída errado desmonta a
pergunta na hora em que o advogado contrário pede para ler o trecho inteiro.

**Calibragem oral:** o roteiro é lido em pé, em tempo real. 3 ou 4 temas, o confronto mais forte
primeiro. Roteiro longo faz pular sequência. Se o caso é grande, dizer onde o advogado pode cortar.

## 5. Checklist e orientação ao cliente

No fim do roteiro, uma seção **Logística**:
- documentos com foto; contrato social (PJ); carta de preposição (réu PJ); procuração com poderes
  para transigir, se for o caso;
- testemunhas: intimação ou compromisso de levar, endereço e telefone;
- telepresencial: link, teste de câmera e áudio, documento à mão, ambiente sem interferência;
- prazo para arguir impedimento de comparecimento: até a abertura (art. 362, § 1º).

E o **rascunho da mensagem ao cliente** no registro de e-mail do advogado (ver `estilo_emails`):
data, hora, local ou link, o que levar, chegar antes, como responder (forma, nunca conteúdo
ensaiado), fechando com uma pergunta. **Rascunho**: o advogado envia.

## 6. Depois da audiência (no mesmo dia)

- Registrar o resultado no `intake.md` (termo, acordo, provas, próximos prazos) e no Astrea.
- Linha no BASTÃO. Resultado não registrado vira pergunta ao advogado na semana seguinte; já
  aconteceu.
- Acordo ou sentença em audiência com prazo correndo → avisar o advogado do termo.

## O que esta skill não faz

- Não decide proposta de acordo, número nem estratégia. Prepara a decisão do advogado.
- Não prevê o que a testemunha vai dizer; prepara para as respostas prováveis.
- Não substitui o juízo do advogado na sala: as perguntas de seguimento são dele.
