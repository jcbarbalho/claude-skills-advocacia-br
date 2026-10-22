# Skills e agentes do Claude Code para advocacia cível brasileira

Procedimentos de um escritório de advocacia cível (TJRJ e TJSP) escritos como **skills** e
**subagentes** do [Claude Code](https://code.claude.com). Cada um nasceu de um erro real ou de uma
tarefa que se repetia, e foi testado em caso concreto antes de entrar aqui. Os exemplos foram
anonimizados: não há nome de cliente, número de processo ou dado pessoal.

> ⚠️ Isto não é aconselhamento jurídico nem substitui o advogado. Tudo o que estas ferramentas
> produzem é **rascunho para revisão humana**. Nenhuma delas envia, protocola ou assina sozinha.

## Princípios comuns

Valem para todos os arquivos e são o que mais vale copiar:

1. **Rascunho, nunca ato.** Enviar, protocolar, assinar, pagar e apagar dependem do "sim" expresso
   do advogado, dado na hora, mesmo que ele já tenha pedido antes.
2. **Conferir na fonte.** Todo artigo citado é conferido num corpus local de legislação. Julgado,
   súmula ou ementa nunca são completados de memória: o que não foi conferido sai marcado
   `[VERIFICAR]` ou `❓ não conferido`.
3. **Fato ≠ inferência.** O que está no documento é fato. O que o modelo deduz vai marcado como
   inferência, com o raciocínio.
4. **Página do PDF ≠ folha dos autos.** As duas são registradas, e a folha nunca é inventada.
5. **Agente lê muito e devolve pouco; skill conversa.** O que exige decisão do advogado ou ato
   irreversível é skill. O que lê em volume, roda em paralelo ou precisa de olhar independente é
   agente.
6. **O modelo certo para cada tarefa.** O raciocínio (revisão adversarial, tese nova) vai no Opus.
   Leitura e conferência em volume vão no Sonnet.

## O que tem aqui

### Agentes (`agents/`)

| Agente | O que faz | Modelo |
|---|---|---|
| `revisor-adversario` | Lê a peça a frio, como o juiz e como o advogado adverso, e devolve até 12 furos por gravidade (🔴 derruba, 🟠 enfraquece, 🟡 acabamento). Só leitura. | Opus, alto |
| `teses-fora-da-caixa` | Procura tese nova fora do repertório da área: finalidade do instituto, enriquecimento sem causa, boa-fé, analogia, outros ramos e enunciados do CJF dos dois lados. Cada hipótese vem com a ponte com os fatos, o dispositivo conferido e a objeção mais forte. | Opus, extra-alto |
| `conferente-de-citacoes` | Confere cada artigo, súmula, tema e julgado de uma peça (existência, vigência, direito intertemporal) e devolve uma tabela ✅/⚠️/🟠/🔴/❓. | Sonnet, alto |
| `cronologia-dos-fatos` | Monta a linha do tempo pelas fontes, com grau de prova (documento, relato, segunda mão), lista os conflitos de data e de ordem e confere a narrativa de uma peça. | Sonnet, alto |
| `pesquisador-biblioteca` | Pesquisa por conteúdo a biblioteca de teses do escritório e traz o encaixe, o que reaproveitar, os pontos de atenção e o caso-fonte. | Sonnet, médio |
| `leitor-de-autos` | Lê uma faixa de páginas de autos (com OCR quando precisa) e grava notas com página do PDF e folha. Vários rodam em paralelo para autos grandes. | Sonnet, médio |

### Skills (`skills/`)

| Skill | O que faz |
|---|---|
| `preparo-audiencia` | Roteiro de audiência (conciliação, ACIJ do JEC, AIJ, preliminar do JECrim): pontos controvertidos com ônus e prova, perguntas sem indução (art. 459 do CPC), contradita, acordo, alegações finais e orientação ao cliente. Adaptada do `deposition-prep` da Anthropic (ver NOTICE). |
| `protocolar` | Protocolo de petição intermediária **feito para a API do [LegalMail](https://legalmail.com.br)**: registro certo (eproc × PJe, grau), quem peticiona e em que polo, resumo antes do "sim", e o pós-protocolo. O motor (um script próprio que chama a API) não está publicado. Para outro sistema de peticionamento vale o checklist, e o motor tem de ser reescrito. |
| `due-diligence-leilao` | Due diligence de imóvel em leilão para quem quer arrematar: edital, matrícula, intimação do executado, preço vil, ônus, condomínio, ocupação, custo total e lance máximo a decidir pelo cliente. |
| `markitdown` | Ler qualquer documento (docx, xlsx, pdf, pptx) como Markdown, e quando não usar. |

### Scripts (`scripts/`)

| Script | O que faz |
|---|---|
| [`push-legislativo`](scripts/push-legislativo/) | Segue proposições da Câmara dos Deputados pela API de Dados Abertos e avisa (relatório diário e Telegram, opcional) quando elas andam, com a classificação por código de tramitação que separa o que decide (parecer, votação, **urgência aprovada**) da rotina. Inclui um garimpo por área para descobrir o que seguir. Só biblioteca padrão do Python. |

## Testes feitos

Os agentes novos foram testados **às cegas** contra um gabarito: o resultado que o escritório já
tinha alcançado no mesmo caso, sem que o agente visse esse resultado.

- **`cronologia-dos-fatos`** (caso de compra fraudulenta): recebeu só os documentos e a primeira
  versão de uma petição inicial que tinha narrado os fatos fora de ordem. Pegou o erro (um crédito
  na fatura do cartão era anterior à data em que o cliente dizia ter descoberto a fraude) e mais
  três pontos que o gabarito não tinha. Deu dois falsos alarmes, e as regras que os causaram foram
  corrigidas no prompt.
- **`teses-fora-da-caixa`** (colação em inventário), rodado no Opus e no Fable: os dois chegaram
  sozinhos aos três fundamentos que o escritório tinha construído. O Opus ainda achou o enunciado
  do CJF que sustentava a tese adversária; o Fable propôs uma leitura estratégica melhor, a cerca
  de 2,5 vezes o custo. Ficou o Opus como padrão.

## Como usar

1. Copie `agents/*.md` para `~/.claude/agents/` e cada pasta de `skills/` para `~/.claude/skills/`.
2. Troque os marcadores pelos caminhos do seu ambiente:

| Marcador | O que é |
|---|---|
| `<ESCRITORIO>` | pasta raiz do acervo do escritório (no original, um Drive sincronizado) |
| `<PYTHON_DO_ESCRITORIO>` | o Python do ambiente virtual onde rodam os scripts |
| `<MEMORIA>` | pasta de memória do Claude Code do projeto do escritório |
| `mcp__jurisprudencia__*` | as ferramentas de um conector MCP de busca de jurisprudência; troque pelo nome do seu conector |

3. Adapte as convenções de pasta, descritas abaixo, ou reescreva as seções que dependem delas.

### O que não vem junto

Os arquivos citam scripts e acervos internos que **não** estão neste repositório. Quem baixar
recebe o método, não um sistema pronto:

- `piece_gen/`: scripts próprios (extração de páginas com OCR, linter de peça, crítica estratégica,
  indexador da biblioteca de teses, gerador de .docx em papel timbrado, protocolo por API);
- `09. Legislação/`: corpus local de legislação federal e do TJRJ, um arquivo por lei, com âncora
  `### Art. N` por artigo e corpus de súmulas, temas repetitivos e de repercussão geral;
- a biblioteca de teses do escritório e o seu espelho em texto;
- integrações: LegalMail (peticionamento), Astrea (gestão de processos), DJEN (comunicações
  processuais, API pública).

### Convenções de pasta do original

- Uma pasta por cliente e, dentro dela, uma por caso, com `intake.md` (ficha viva do caso),
  `Peças\` e `Documentos\`.
- Minuta feita pela IA leva o sufixo `_CB` (`_CB_v1`, `_CB_v2`...). Revisão humana vira `_rev` + as iniciais do revisor.
- `BASTÃO` é um arquivo de passagem de turno entre sessões do Claude Code: cada sessão lê ao
  começar e escreve ao terminar.

## Licença

Apache-2.0 (arquivo `LICENSE`). A skill `preparo-audiencia` deriva de material da Anthropic sob a
mesma licença; ver `NOTICE`.
