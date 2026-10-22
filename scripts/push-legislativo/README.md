# Push legislativo

Acompanha proposições da **Câmara dos Deputados** e avisa quando elas andam. Usa só a
[API de Dados Abertos da Câmara](https://dadosabertos.camara.leg.br), sem autenticação, e só a
biblioteca padrão do Python 3.10+.

> ⚠️ Não é o push de tribunal. Não há processo nem efeito jurídico, e a Câmara não tem webhook: é
> polling diário, com atraso de até um dia. É vigilância informativa.

## Uso

```bash
python push_legislativo.py --seguir 2642783 --motivo "altera a LRP" --prioridade alta
python push_legislativo.py --listar
python push_legislativo.py --checar                    # grava o relatório do dia
python push_legislativo.py --checar --enviar-telegram  # e manda o resumo
python push_legislativo.py --esquecer 2642783
python push_legislativo.py --garimpar --ano 2025 --ano 2026   # candidatos por área
```

O `id` é o da proposição na API (aparece na URL da ficha de tramitação, `idProposicao=`).

**Configuração (variáveis de ambiente, todas opcionais):**

| Variável | Para quê |
|---|---|
| `PUSH_LEGIS_DIR` | pasta da `watchlist.json` e dos relatórios (padrão: `./radar` ao lado do script) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | resumo no Telegram com `--enviar-telegram` |

Para rodar todo dia útil, agende o `--checar` (Agendador de Tarefas do Windows ou cron).

## Como classifica, e por quê

A classificação usa o **código** do tipo de tramitação (`codTipoTramitacao`), não o texto: a
descrição varia de órgão para órgão, o código não. Os códigos saíram de 1.127 tramitações reais de
12 proposições.

| | Códigos |
|---|---|
| 🔴 decide | 322 parecer do relator · 336 aprovação do parecer · 240 aprovação · 1231 votação · 1235 aprovado · 1236 rejeitado · 502 arquivamento · 640 desarquivamento · **196 urgência aprovada** |
| 🟡 anda | 320 designação de relator · 110 distribuição · 504 apensação · 250 retirada de pauta · 242 discussão · 100 apresentação |
| ⚪ rotina | o resto (recebimento, publicação, prazos) |

**Lições que estão no código:**
- **Urgência aprovada (196) é o sinal mais forte que existe**, e quase passou como rotina porque
  não estava na amostra inicial. Ela tira a proposição das comissões e libera a votação a qualquer
  momento. Por segurança, no Plenário (`PLEN`) tudo o que aprova, rejeita, vota ou dá urgência é 🔴,
  tenha o código que tiver; sanção, veto e remessa ao Senado também, casados por texto.
- **Eco do mesmo ato:** a Câmara registra a urgência e a mudança de regime que ela causa em duas
  sequências, no mesmo minuto. O script deduplica por proposição, evento e data.
- **Linha de base:** ao seguir uma proposição, grava-se a sequência atual. Só o que vier depois vira
  alerta; senão, o primeiro check despeja a tramitação inteira.
- **Ciclo de vida:** a watchlist tem três estados (acompanhadas, sancionadas, arquivadas). A
  proposição que chega a um desfecho sai da consulta diária.

## Garimpo por área

`--garimpar` varre PL, PLP, PEC e MPV do ano, filtra a **ementa** por um léxico de áreas (consumidor,
família, sucessões, processo civil, registro público, imobiliário, advocacia, bancário), descarta
falsos positivos conhecidos ("alimentos" no sentido de comida, execução penal, datas comemorativas)
e consulta a situação de cada candidato: 🔴 em pauta ou com urgência, 🟡 tramitando, ⚪ parada há
mais de um ano, ❌ arquivada ou já lei (descartada). Em 2025 e 2026: 12.168 proposições varridas,
596 candidatas e 59 🔴.

Troque o dicionário `AREAS` pelas suas áreas. O léxico usa contexto, nunca palavra solta: "guarda"
está dentro de "aguardar", e "partilha" dentro de "compartilhar".

**Limite do método:** o filtro lê a ementa, isto é, o que o autor diz que a proposição faz. Um
artigo enxertado no corpo do projeto, sem relação com a ementa (o "jabuti"), não aparece.

## Ainda não cobre

- **Senado.** Quando entrar, tem de nascer em `legis.senado.leg.br/dadosabertos/processo`: o
  endpoint antigo (`/materia/pesquisa/lista`) anuncia desativação em 01/02/2026 e está em sobrevida.
- Assembleias legislativas e câmaras municipais (cada uma tem sua própria API, quando tem).
