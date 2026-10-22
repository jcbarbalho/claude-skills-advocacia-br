# -*- coding: utf-8 -*-
r"""push_legislativo.py — watchlist de proposições, com alerta quando ELAS andam.

    python push_legislativo.py --seguir 2642783 --motivo "altera a LRP"
    python push_legislativo.py --listar
    python push_legislativo.py --checar --enviar-telegram
    python push_legislativo.py --esquecer 2642783

Complementa o `radar_legislativo.py`, que varre por TEMA uma vez por mês e responde
"o que estão propondo que mexe nas minhas leis". Aqui é o outro eixo: seguir uma
proposição específica e saber quando ela se move. O radar é o funil; este é o
acompanhamento.

⚠️ Isto NÃO é o push do tribunal. Não há processo, não há parte, não há efeito
   jurídico nenhum — e não existe webhook na Câmara: é polling, com atraso de até
   um dia. É vigilância informativa, e chamar de "push" promete mais do que entrega.

Fonte: API de Dados Abertos da Câmara dos Deputados (sem autenticação).

Configuração (tudo opcional):
    PUSH_LEGIS_DIR      pasta da watchlist e dos relatórios (padrão: ./radar, ao lado do script)
    TELEGRAM_BOT_TOKEN  token do bot, para --enviar-telegram
    TELEGRAM_CHAT_ID    chat que recebe o resumo
O Senado fica para depois — e, quando for, tem de nascer em
`legis.senado.leg.br/dadosabertos/processo`: o endpoint antigo (`/materia/pesquisa/lista`)
responde com DataDesativacaoCompleta de 01/02/2026, data já vencida, e está em sobrevida.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
RADAR = Path(os.environ.get("PUSH_LEGIS_DIR") or BASE / "radar")
LISTA = RADAR / "watchlist.json"
API = "https://dadosabertos.camara.leg.br/api/v2"
FICHA = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao="
UA = "push-legislativo/1.0 (+https://github.com/jcbarbalho/claude-skills-advocacia-br)"

# A API da Câmara às vezes não responde por IPv6 em redes domésticas: forçar IPv4.
_orig = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, f=0, t=0, pr=0, fl=0: _orig(h, p, socket.AF_INET, t, pr, fl)

# Classificação por codTipoTramitacao — levantada dos códigos REAIS da API
# (1.127 tramitações de 12 proposições, em 27/09/2026). Classificar por código,
# não por texto: a descrição varia de órgão para órgão, o código não.
ALTO = {
    322: "parecer do relator", 336: "aprovação do parecer", 240: "aprovação",
    1231: "votação em plenário", 1235: "APROVADO em plenário",
    1236: "REJEITADO em plenário", 502: "arquivamento", 640: "desarquivamento",
    # ⚠️ 196 não apareceu na amostra de 2023 e saiu como "rotina" no 1º teste real.
    # URGÊNCIA APROVADA é dos sinais mais fortes que existem: tira a proposição das
    # comissões e libera a votação a qualquer momento. Sem isto, o alerta chegaria
    # depois de a lei estar votada.
    196: "URGÊNCIA aprovada — pode ir a voto a qualquer momento",
}
MEDIO = {
    320: "designação de relator", 110: "distribuição", 504: "apensação",
    250: "retirada de pauta", 242: "discussão em plenário", 100: "apresentação",
}
# Eventos decisivos que não apareceram na amostra: casar por texto, como rede de
# segurança. Sem isto, uma sanção passaria como ruído por não ter código conhecido.
TEXTO_ALTO = re.compile(
    r"san[çc][ãa]o|veto|transformado em norma|remessa ao senado|remessa [àa] sanç|"
    r"remetido ao senado|convertid[ao] em lei|promulga", re.I)


def get(url: str, tentativas: int = 3):
    erro = None
    for n in range(tentativas):
        try:
            req = Request(url, headers={"Accept": "application/json", "User-Agent": UA})
            with urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:                                       # noqa: BLE001
            erro = e
    raise RuntimeError(f"{url}: {erro}")


def carregar() -> dict:
    d = json.loads(LISTA.read_text(encoding="utf-8")) if LISTA.exists() else {}
    # Ciclo de vida, lição de uma planilha de monitoramento legislativo profissional: a
    # watchlist tem de ter três estados. Sem isso, proposição arquivada ou já
    # sancionada fica sendo consultada para sempre e o acompanhamento vira lixo.
    d.setdefault("itens", {})          # acompanhados
    d.setdefault("sancionados", {})
    d.setdefault("arquivados", {})
    return d


def salvar(d: dict) -> None:
    RADAR.mkdir(parents=True, exist_ok=True)
    LISTA.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def relevancia(t: dict) -> tuple[str, str]:
    cod = int(t.get("codTipoTramitacao") or 0)
    desc = (t.get("descricaoTramitacao") or "").strip()
    texto = f"{desc} {t.get('despacho') or ''}"
    if cod in ALTO:
        return "🔴", ALTO[cod]
    if TEXTO_ALTO.search(texto):
        return "🔴", desc.lower() or "evento decisivo"
    # Rede de segurança para código novo: no PLENÁRIO, o que aprova, rejeita ou
    # dá urgência é sempre decisivo, tenha o código que tiver.
    if (t.get("siglaOrgao") or "").upper() == "PLEN" and \
            re.search(r"aprova|rejeit|urg[êe]ncia|vota", desc, re.I):
        return "🔴", desc.lower()
    if cod in MEDIO:
        return "🟡", MEDIO[cod]
    return "⚪", desc.lower()


def seguir(pid: int, motivo: str, d: dict, prioridade: str = "média",
           posicao: str = "neutro") -> str:
    p = get(f"{API}/proposicoes/{pid}")["dados"]
    tram = get(f"{API}/proposicoes/{pid}/tramitacoes")["dados"]
    ultima = max((int(t["sequencia"]) for t in tram), default=0)
    d["itens"][str(pid)] = {
        "id": pid,
        "rotulo": f'{p["siglaTipo"]} {p["numero"]}/{p["ano"]}',
        "ementa": p["ementa"],
        "motivo": motivo,
        "prioridade": prioridade,      # alta | média | baixa — decide o que vai ao Telegram
        "posicao": posicao,            # convergente | divergente | neutro
        "seguido_em": datetime.now().strftime("%Y-%m-%d"),
        # a partir daqui só avisa o que for NOVO: o histórico entra como linha de base
        "ultima_sequencia": ultima,
        "ultimo_check": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return f'{d["itens"][str(pid)]["rotulo"]} (seq. {ultima})'


def checar(d: dict, log) -> list:
    eventos = []
    for chave, item in d["itens"].items():
        try:
            tram = get(f'{API}/proposicoes/{item["id"]}/tramitacoes')["dados"]
        except RuntimeError as e:
            log(f'  ! {item["rotulo"]}: {e}')
            continue
        novos = [t for t in tram if int(t["sequencia"]) > item.get("ultima_sequencia", 0)]
        if novos:
            item["ultima_sequencia"] = max(int(t["sequencia"]) for t in novos)
        item["ultimo_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        for t in novos:
            sev, rotulo = relevancia(t)
            # o evento que ENCERRA o acompanhamento também move a proposição de aba
            cod = int(t.get("codTipoTramitacao") or 0)
            texto = f'{t.get("descricaoTramitacao") or ""} {t.get("despacho") or ""}'
            if re.search(r"transformad[oa] em (norma|lei)|san[çc]ion|convertid[ao] em lei",
                         texto, re.I):
                item["saiu_em"], item["desfecho"] = t.get("dataHora", "")[:10], "sancionado"
            elif cod == 502:
                item["saiu_em"], item["desfecho"] = t.get("dataHora", "")[:10], "arquivado"
            eventos.append({
                "proposicao": item["rotulo"], "id": item["id"], "sev": sev,
                "evento": rotulo, "orgao": t.get("siglaOrgao"),
                "data": (t.get("dataHora") or "")[:16].replace("T", " "),
                "despacho": re.sub(r"\s+", " ", t.get("despacho") or "").strip(),
                "situacao": t.get("descricaoSituacao"),
                "teor": t.get("url"),
            })
        log(f'  {item["rotulo"]}: {len(novos)} novidade(s)'
            + (f' → {item["desfecho"].upper()}' if item.get("desfecho") else ""))

    # move quem teve desfecho para a aba própria, saindo da consulta diária
    for chave in [k for k, v in d["itens"].items() if v.get("desfecho")]:
        item = d["itens"].pop(chave)
        destino = "sancionados" if item["desfecho"] == "sancionado" else "arquivados"
        d[destino][chave] = item
        log(f'  {item["rotulo"]} saiu dos acompanhados → {destino}')
    # A Câmara registra o mesmo ato em duas sequências (a aprovação da urgência e a
    # alteração de regime que decorre dela, no mesmo minuto). Para quem lê, é um
    # evento só — avisar duas vezes gasta a atenção que o alerta depende de ter.
    unicos, vistos = [], set()
    for e in eventos:
        chave = (e["proposicao"], e["evento"], e["data"])
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(e)

    ordem = {"🔴": 0, "🟡": 1, "⚪": 2}
    return sorted(unicos, key=lambda e: (ordem[e["sev"]], e["data"]))


def relatorio(eventos: list, d: dict) -> str:
    hoje = datetime.now()
    L = [f"# Push legislativo — {hoje:%d/%m/%Y}\n",
         f"> {len(d['itens'])} proposição(ões) na watchlist · {len(eventos)} movimento(s) novo(s).",
         "> Fonte: Dados Abertos da Câmara. Polling diário, não é notificação oficial.\n"]
    if not eventos:
        L.append("Nenhuma das proposições seguidas andou desde a última checagem.")
        return "\n".join(L)
    for grupo, titulo in (("🔴", "Merece leitura hoje"), ("🟡", "Andou, sem decidir nada"),
                          ("⚪", "Rotina")):
        do_grupo = [e for e in eventos if e["sev"] == grupo]
        if not do_grupo:
            continue
        L.append(f"\n## {grupo} {titulo} ({len(do_grupo)})\n")
        for e in do_grupo:
            L.append(f"**{e['proposicao']}** — {e['evento']} · {e['orgao']} · {e['data']}")
            if e["despacho"]:
                L.append(f"  > {e['despacho'][:400]}")
            if e["situacao"]:
                L.append(f"  Situação: {e['situacao']}")
            L.append(f"  [ficha]({FICHA}{e['id']})" + (f" · [teor]({e['teor']})" if e["teor"] else ""))
            L.append("")
    return "\n".join(L)


# ----------------------------------------------------- garimpo por área
# As áreas abaixo são as de um escritório de advocacia cível; troque pelas suas.
# ⚠️ Léxico com CONTEXTO, nunca palavra solta. As armadilhas que já custaram caro:
#   "alimentos" casa com COMIDA (segurança alimentar, rotulagem) — exigir prestação/pensão
#   "execução"  casa com execução PENAL e orçamentária — exigir civil/cumprimento/título
#   "guarda" está dentro de "aGUARDAr" e "partilha" dentro de "comPARTILHAr" — usar \b
AREAS = {
    "consumidor": r"c[óo]digo de defesa do consumidor|\b8\.?078\b|rela[çc][ãa]o de consumo|"
                  r"superendivida|pr[áa]ticas? abusivas?|publicidade enganosa|"
                  r"prote[çc][ãa]o do consumidor",
    "família/alimentos": r"presta[çc][ãa]o de alimentos|pens[ãa]o aliment[íi]cia|"
                         r"devedor de alimentos|\bguarda compartilhada\b|\bguarda unilateral\b|"
                         r"\bdiv[óo]rcio\b|regime de bens|uni[ãa]o est[áa]vel|"
                         r"aliena[çc][ãa]o parental|poder familiar",
    "sucessões": r"\binvent[áa]rio\b|\bpartilha de bens\b|\bheran[çc]a\b|"
                 r"sucess[ãa]o heredit[áa]ria|\btestamento\b|arrolamento",
    "processo civil": r"c[óo]digo de processo civil|\b13\.?105\b|cumprimento de senten[çc]a|"
                      r"execu[çc][ãa]o de t[íi]tulo|execu[çc][ãa]o civil|\bpenhora\b|"
                      r"honor[áa]rios sucumbenciais|juizado especial|tutela de urg[êe]ncia|"
                      r"gratuidade de justi[çc]a",
    "registro público": r"registros? p[úu]blicos?|\b6\.?015\b|\b8\.?935\b|registro civil|"
                        r"registro de im[óo]veis|tabeli|cart[óo]ri|notari|usucapi[ãa]o|"
                        r"ata notarial|serventia extrajudicial|emolumentos",
    "imobiliário": r"\bloca[çc][ãa]o\b|inquilinato|\b8\.?245\b|condom[íi]nio edil[íi]cio|"
                   r"incorpora[çc][ãa]o imobili[áa]ria|aliena[çc][ãa]o fiduci[áa]ria|"
                   r"\b9\.?514\b|regulariza[çc][ãa]o fundi[áa]ria",
    "advocacia": r"estatuto da (ordem dos )?advoga|\b8\.?906\b|\bOAB\b|exerc[íi]cio da advocacia|"
                 r"honor[áa]rios advocat[íi]cios",
    "bancário/crédito": r"consignado|margem consign|\bRMC\b|cart[ãa]o de cr[ée]dito|"
                        r"juros remunerat|capitaliza[çc][ãa]o de juros|cadastro positivo|"
                        r"negativa[çc][ãa]o|prote[çc][ãa]o ao cr[ée]dito",
}
DESCARTE = (r"seguran[çc]a alimentar|desperd[íi]cio de alimentos|rotulagem|merenda|"
            r"alimenta[çc][ãa]o escolar|execu[çc][ãa]o penal|or[çc]ament|"
            r"cr[ée]dito extraordin[áa]rio|data comemorativa|denomina[çc][ãa]o|dia nacional|"
            r"declara.{0,15}utilidade p[úu]blica")


def norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def garimpar(anos: list, tipos: list, ja: set, log) -> list:
    achados = []
    for tipo in tipos:
        for ano in anos:
            pag, vistos = 1, 0
            while True:
                try:
                    d = get(f"{API}/proposicoes?siglaTipo={tipo}&ano={ano}&itens=100"
                            f"&pagina={pag}&ordem=DESC&ordenarPor=id")["dados"]
                except RuntimeError as e:
                    log(f"  ! {tipo}/{ano} pág.{pag}: {e}")
                    break
                if not d:
                    break
                vistos += len(d)
                for p in d:
                    em = norm(p["ementa"])
                    if re.search(DESCARTE, em):
                        continue
                    areas = [a for a, rx in AREAS.items() if re.search(rx, em)]
                    if areas and str(p["id"]) not in ja:
                        achados.append({"id": p["id"], "rotulo": f'{tipo} {p["numero"]}/{ano}',
                                        "areas": areas, "ementa": p["ementa"]})
                pag += 1
            log(f"  {tipo}/{ano}: {vistos} varridas")
    return achados


# Garimpo cru devolve centenas: sem a situação de cada uma, a lista é grande demais
# para alguém marcar à mão — e metade está arquivada. Uma requisição por candidato
# transforma volume em fila de leitura.
VIVO_FORTE = re.compile(r"pronta para pauta|urg[êe]ncia|aguardando (vota|delibera)|"
                        r"parecer aprovado|pauta|plen[áa]rio", re.I)
MORTO = re.compile(r"arquivad|rejeitad|retirad[ao] pelo autor|pereceu|"
                   r"transformad[oa] em (norma|lei)|devolvid[ao] ao autor", re.I)


def enriquecer(cand: list, log) -> list:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def status(c):
        try:
            p = get(f'{API}/proposicoes/{c["id"]}')["dados"]
            st = p.get("statusProposicao") or {}
            c["situacao"] = (st.get("descricaoSituacao") or
                             st.get("descricaoTramitacao") or "—")
            c["orgao"] = st.get("siglaOrgao") or ""
            c["desde"] = (st.get("dataHora") or "")[:10]
            c["regime"] = st.get("regime") or ""
        except RuntimeError:
            c["situacao"] = "? (falha na consulta)"
            c["desde"] = ""
        texto = f'{c.get("situacao","")} {c.get("regime","")}'
        if MORTO.search(texto):
            c["sev"] = "❌"
        elif VIVO_FORTE.search(texto):
            c["sev"] = "🔴"
        elif c.get("desde", "") and c["desde"] < (datetime.now().replace(
                year=datetime.now().year - 1)).strftime("%Y-%m-%d"):
            c["sev"] = "⚪"          # viva no papel, parada há mais de um ano
        else:
            c["sev"] = "🟡"
        return c

    with ThreadPoolExecutor(max_workers=6) as pool:
        futuros = [pool.submit(status, c) for c in cand]
        for i, f in enumerate(as_completed(futuros), 1):
            f.result()
            if i % 100 == 0:
                log(f"  situação de {i}/{len(cand)}")
    return cand


def telegram(texto: str) -> None:
    from urllib.parse import urlencode
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("[telegram] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID não definidos — relatório "
              "gravado mesmo assim", file=sys.stderr)
        return
    dados = urlencode({"chat_id": chat, "text": texto[:4000],
                       "disable_web_page_preview": "true"}).encode()
    try:
        urlopen(Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=dados),
                timeout=60).read()
        print("[telegram] enviado")
    except Exception as e:                                           # noqa: BLE001
        print(f"[telegram] FALHA ({e}) — relatório gravado mesmo assim", file=sys.stderr)


def resumo_telegram(eventos: list) -> str:
    altos = [e for e in eventos if e["sev"] == "🔴"]
    linhas = [f"🏛️ *Push legislativo — {datetime.now():%d/%m}*", ""]
    if altos:
        linhas.append(f"🔴 *{len(altos)} movimento(s) que decidem:*")
        for e in altos[:6]:
            linhas.append(f"• {e['proposicao']}: {e['evento']} ({e['orgao']})")
    outros = len(eventos) - len(altos)
    if outros:
        linhas.append(f"\n🟡⚪ mais {outros} movimento(s) de tramitação")
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seguir", type=int, action="append", help="id da proposição na Câmara")
    ap.add_argument("--motivo", default="")
    ap.add_argument("--prioridade", default="média", choices=["alta", "média", "baixa"])
    ap.add_argument("--posicao", default="neutro",
                    choices=["convergente", "divergente", "neutro"])
    ap.add_argument("--esquecer", type=int)
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--checar", action="store_true")
    ap.add_argument("--garimpar", action="store_true",
                    help="varre a Câmara pelas áreas de AREAS e lista candidatos")
    ap.add_argument("--ano", type=int, action="append")
    ap.add_argument("--tipos", default="PL,PLP,PEC,MPV")
    ap.add_argument("--enviar-telegram", action="store_true")
    a = ap.parse_args()

    def log(m):
        print(m, flush=True)

    d = carregar()

    if a.esquecer:
        fora = d["itens"].pop(str(a.esquecer), None)
        salvar(d)
        log(f'removido: {fora["rotulo"] if fora else a.esquecer}')
        return 0

    if a.seguir:
        for pid in a.seguir:
            try:
                log("+ " + seguir(pid, a.motivo, d, a.prioridade, a.posicao))
            except RuntimeError as e:
                log(f"! {pid}: {e}")
        salvar(d)
        return 0

    if a.listar:
        log(f'ACOMPANHADOS ({len(d["itens"])}):')
        for it in d["itens"].values():
            pri = (it.get("prioridade") or "-").upper()[:5]
            log(f'  [{pri:<5}] {it["rotulo"]:<16} seq.{it["ultima_sequencia"]:<4} '
                f'{it["motivo"][:42]}')
            log(f'            {it["ementa"][:100]}')
        for aba, titulo in (("sancionados", "SANCIONADOS"), ("arquivados", "ARQUIVADOS")):
            if d.get(aba):
                log(f'\n{titulo} ({len(d[aba])}):')
                for it in d[aba].values():
                    log(f'  {it["rotulo"]:<16} {it.get("saiu_em","")}  {it["motivo"][:45]}')
        return 0

    if a.garimpar:
        anos = a.ano or [datetime.now().year]
        tipos = [t.strip().upper() for t in a.tipos.split(",") if t.strip()]
        ja = set(d["itens"]) | set(d["sancionados"]) | set(d["arquivados"])
        log(f"Garimpando {tipos} em {anos} (já seguidas: {len(ja)})...")
        cand = garimpar(anos, tipos, ja, log)
        log(f"consultando a situação de {len(cand)} candidatos...")
        cand = enriquecer(cand, log)
        vivos = [c for c in cand if c["sev"] != "❌"]
        log(f"  {len(cand) - len(vivos)} descartados (arquivados, rejeitados ou já lei)")
        ordem = {"🔴": 0, "🟡": 1, "⚪": 2}
        por_area: dict = {}
        for c in sorted(vivos, key=lambda x: (ordem[x["sev"]], x["desde"]), reverse=False):
            for ar in c["areas"]:
                por_area.setdefault(ar, []).append(c)
        hoje = datetime.now()
        L = [f"# Candidatos à watchlist — {hoje:%d/%m/%Y}\n",
             f"> Varredura de {', '.join(tipos)} em {', '.join(map(str, anos))}: "
             f"**{len(vivos)} vivos** de {len(cand)} achados, em {len(por_area)} área(s).",
             "> 🔴 em pauta ou com urgência · 🟡 tramitando · ⚪ viva no papel, parada há mais "
             "de um ano\n",
             "> Marcar `x` na coluna Seguir e rodar `--seguir <id>` para cada marcado.\n",
             "⚠️ Filtro por ementa: pega o que o autor **disse** que a proposição faz. "
             "Proposição cujo efeito real está no corpo escapa.\n"]
        for ar in sorted(por_area, key=lambda k: -len(por_area[k])):
            L.append(f"\n## {ar} ({len(por_area[ar])})\n")
            L.append("| Seguir | | Proposição | id | Situação | Desde | Ementa |")
            L.append("|---|---|---|---|---|---|---|")
            for c in por_area[ar]:
                em = c["ementa"].replace("|", "/")[:170]
                L.append(f"| | {c['sev']} | {c['rotulo']} | {c['id']} | "
                         f"{c.get('situacao','')[:40]} | {c.get('desde','')} | {em} |")
        RADAR.mkdir(parents=True, exist_ok=True)
        arq = RADAR / f"{hoje:%Y-%m-%d} candidatos watchlist.md"
        arq.write_text("\n".join(L), encoding="utf-8")
        log(f"\n{len(cand)} candidato(s) · {arq.name}")
        for ar in sorted(por_area, key=lambda k: -len(por_area[k])):
            log(f"  {len(por_area[ar]):>4}  {ar}")
        return 0

    if a.checar:
        if not d["itens"]:
            log("watchlist vazia — usar --seguir <id>")
            return 1
        log(f'Checando {len(d["itens"])} proposição(ões)...')
        eventos = checar(d, log)
        salvar(d)
        RADAR.mkdir(parents=True, exist_ok=True)
        arq = RADAR / f"{datetime.now():%Y-%m-%d} push legislativo.md"
        arq.write_text(relatorio(eventos, d), encoding="utf-8")
        log(f"\n{len(eventos)} movimento(s) · relatório: {arq.name}")
        if eventos and a.enviar_telegram:
            telegram(resumo_telegram(eventos))
        elif not eventos:
            log("nada novo — Telegram não acionado")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(main())
