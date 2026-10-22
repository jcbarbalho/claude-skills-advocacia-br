---
name: due-diligence-leilao
description: Due diligence de um bem em leilão (judicial, trabalhista, federal ou alienação fiduciária) para um cliente que quer arrematar — coleta edital, matrícula e laudo, confere o processo no DJEN, aplica o checklist (intimação, preço vil, ônus, condomínio, IPTU, ocupação, preferências), soma o custo total e entrega parecer timbrado com risco e lance máximo a decidir pelo cliente. Use quando o advogado trouxer um edital, um lote da vigia de leilões ou um cliente interessado em arrematar.
argument-hint: "[lote_id | link do edital | CNJ] [cliente]"
---

# /due-diligence-leilao

Linha de serviço de assessoria ao arrematante (10/2026). Base: um relatório interno de sondagem
de fontes e uma vigia diária de leilões (script próprio, não publicado).

**Limites:**
- Não dar lance, não criar cadastro em site de leiloeiro e não habilitar o cliente. Isso é dele.
- Não contatar as partes do processo.
- Não estimar valor de mercado sem fonte: o número é do cliente, de corretor ou de laudo.

## 0. Antes de tudo

1. **Prazo:** data e hora do 1º e do 2º leilão. Faltando menos de 5 dias úteis, avisar o advogado já, porque
   a habilitação no site do leiloeiro costuma exigir antecedência (bem acima de R$ 2 milhões: termo
   de capacidade financeira até 24 h antes, no caso da Rio Leilões).
2. **Conflito de interesses:** procurar o CNJ e as partes no Astrea (ou no ERP interno) e no acervo. Se o escritório
   representa exequente, executado ou terceiro no processo, **parar e levar ao advogado**.
3. **Pasta:** `<Cliente>\Leilão - <bem curto> (<CNJ>)\` com `Documentos\` e `Peças\`, e um `intake.md`
   (frontmatter `tipo: intake`) já com bem, processo, datas e o que o cliente quer.

## 1. Coletar

**Lote da plataforma Leilões Judiciais** (o `lote_id` está na vigia):

```
curl -4 -s -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -A "Mozilla/5.0" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_leilao_details","arguments":{"leilaoId":"<lote_id>"}}}' \
  https://www.leiloesjudiciais.com.br/api/mcp/messages
```

Baixar os PDFs anexos (os links `s3-sa-east-1.amazonaws.com/.../anexo/*.pdf`: edital, laudo,
matrícula) para `Documentos\`. Outro leiloeiro: o link ou o PDF vem do advogado ou do cliente.

**Processo:**
- DJEN por número (memória `<MEMORIA>\djen_api_publica.md`,
  que fora do projeto do escritório não carrega sozinha; forçar IPv4 no Python): impugnação, suspensão,
  recurso, decisões sobre a avaliação e a intimação do executado.
- Cópia dos autos só se o processo estiver no LegalMail. Processo de terceiro exige pedido de
  importação no painel, que o advogado faz; sem isso, consulta pública.
- **Matrícula atualizada** (a do edital envelhece): certidão de ônus reais e CNIB. Pedido e custo
  são do cliente.

PDF grande (laudo, cópia de autos): acionar o agente **leitor-de-autos**, com foco no bem.

## 2. Checklist (dispositivos conferidos no corpus em 03/10/2026)

**Edital e procedimento**
- [ ] Conteúdo do art. 886 do CPC: descrição, matrícula, avaliação, preço mínimo, condições,
  comissão e **ônus, recurso ou processo pendente** (inciso VI).
- [ ] Publicado ao menos 5 dias antes (art. 887, § 1º).
- [ ] **Executado cientificado com 5 dias de antecedência** (art. 889, I), e os demais do art. 889.
  É a causa clássica de nulidade; o DJEN mostra impugnações nesse sentido.
- [ ] Preço vil: abaixo do mínimo do edital ou, sem mínimo, abaixo de 50% da avaliação (art. 891,
  parágrafo único) → invalidação (art. 903, § 1º, I).
- [ ] Bem indivisível: a quota do coproprietário ou cônjuge alheio sai do produto, com preferência
  dele (art. 843 e § 1º).
- [ ] Parcelamento: proposta escrita até o início do 1º leilão, não inferior à avaliação (art. 895, I).
- [ ] Comissão do leiloeiro: no mínimo 5%, a cargo do arrematante (Res. CNJ 236/2016, art. 7º),
  devolvida se a arrematação for anulada (§ 2º).
- [ ] Recurso ou impugnação pendente contra a penhora, a avaliação ou o leilão.

**Imóvel**
- [ ] Ônus da matrícula: penhoras de outros credores, hipoteca, usufruto, indisponibilidade.
- [ ] **Condomínio:** o adquirente responde pelos débitos (art. 1.345 do CC). Ler o que o edital diz
  sobre sub-rogação no preço e pedir a planilha de débitos.
- [ ] **IPTU:** CTN, art. 130, parágrafo único — `[não conferido: CTN fora do corpus]`. Pedir a
  certidão de situação fiscal.
- [ ] **Ocupação:** quem ocupa, a que título, custo e prazo da imissão na posse (art. 901, § 1º).
- [ ] **Alienação fiduciária:** preferência do fiduciante até o 2º leilão (Lei 9.514, art. 27, § 2º-B).
- [ ] ITBI e registro: alíquota e base de cálculo do município `[conferir]`.

Cada item vira ✅ ok / ⚠️ atenção / 🔴 impeditivo, com a fonte (fls. do edital, ato da matrícula,
evento do processo).

## 3. Conta do custo total

| Item | Base | Valor |
|---|---|---|
| Lance (1º e 2º leilão) | edital | |
| Comissão do leiloeiro | ≥ 5% do lance | |
| ITBI + registro | município `[conferir]` | |
| Débitos de condomínio (se não sub-rogados) | planilha do condomínio | |
| IPTU em atraso (se não sub-rogado) | certidão fiscal | |
| Desocupação (advogado, prazo) | estimativa | |
| Reforma / regularização | cliente ou corretor | |
| **Total** | | |

**Lance máximo** = valor de mercado (do cliente ou do corretor) − custos − margem que o cliente quer.
A margem é decisão dele; o parecer mostra a conta, não escolhe o número.

## 4. Parecer ao cliente (timbrado)

Escrever o `.txt` com os marcadores do gerador de .docx (`<<TIT>>`, `<<P>>`) e converter:

```
"<PYTHON_DO_ESCRITORIO>" \
  "<ESCRITORIO>/06. Automações/piece_gen/gerar_docx.py" "<parecer.txt>" -o "<Peças\\Parecer ..._CB_v1.docx>"
```

Estrutura:
1. **Conclusão** em uma linha: recomendado / recomendado com ressalvas / não recomendado.
2. O bem e o leilão.
3. Riscos (🔴 primeiro), cada um com a consequência prática.
4. Conta do custo total.
5. Lance máximo: a conta com a margem em aberto.
6. O que o cliente precisa fazer e até quando (habilitação, documentos, certidões).

Rascunho para o advogado revisar; ele envia.

## 5. Registrar

- `intake.md` do caso: conclusão, riscos, datas e o que se espera do cliente.
- Astrea ou ERP interno: cadastro do caso, sem número próprio (o processo é de terceiros), e tarefa para
  a data do leilão.
- Linha no BASTÃO.
- Depois do leilão: arrematou? Então carta de arrematação e imissão (art. 901, § 1º). Perdeu? Fechar o caso.
