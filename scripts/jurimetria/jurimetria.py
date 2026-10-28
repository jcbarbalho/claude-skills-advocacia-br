# -*- coding: utf-8 -*-
"""jurimetria.py — quanto o TJRJ dá, e quanto dá cada juízo, num tipo de caso (DJEN + DataJud/CNJ).

Duas fontes públicas, gratuitas e sem login:
  · DJEN (comunicaapi): a SENTENÇA publicada, com dispositivo, valor e assinatura do juiz.
    É daqui que saem o valor do dano moral, o resultado e o nome do magistrado.
  · DataJud: só metadados. Agrega no servidor a taxa de procedência por vara (movimentos
    219/220/221 da TPU) sobre centenas de milhares de processos. Não tem JEC no assunto 6226.

Uso:
  python jurimetria.py coletar [--de AAAA-MM-DD] [--ate AAAA-MM-DD] [--tema negativacao]
        sem datas: continua de onde parou (estado na base) até ontem. É o que a rotina diária roda.
  python jurimetria.py datajud [--tema negativacao]
        retrato da procedência por vara no DataJud (guarda a data do retrato).
  python jurimetria.py antes  --comarca Capital [--segmento jec|vara] [--tema negativacao]
        ANTES da distribuição: estado x comarca e a faixa entre os juízos da comarca.
  python jurimetria.py depois --orgao "2ª Vara Cível da Regional de Bangu" [--tema negativacao]
        DEPOIS da distribuição: o juízo sorteado contra a comarca e o estado, por juiz.
  python jurimetria.py reforma --juiz "NOME COMPLETO DO JUIZ" --de 2025-01-01 [--ate ...] [--refazer]
        taxa de reforma do JUIZ (não da vara): sentenças dele no DJEN x 2º grau no DataJud, por tipo
        de sentença e por órgão, separando no todo / em parte / anulada. Independe do --tema.
  python jurimetria.py exportar
        CSV das sentenças (BOM, ';') para o Excel ou para importar noutro sistema.
  python jurimetria.py rotina
        o que a tarefa agendada roda todo dia: coletar + DataJud mensal + exportar.
  python jurimetria.py reprocessar
        relê os textos guardados depois de ajustar uma regra (não baixa nada).

TEMA NOVO: acrescentar uma entrada em TEMAS (buscas, confirma, forte, assunto do DataJud) e rodar
  coletar --de 2025-10-01 para a carga inicial. A rotina diária passa a cobri-lo sozinha.

Base: jurimetria.sqlite ao lado deste arquivo (o texto da sentença vai comprimido, para
reclassificar depois sem baixar de novo).

LIMITES (dizer sempre ao usar o número):
  · DJEN só tem o que foi publicado (de 2023/2024 em diante). Sentença de processo sem
    advogado constituído pode não sair.
  · Valor do dano moral é extraído por regra; confiança 'baixa' = R$ achado na condenação sem a
    palavra "moral" por perto. Conferir uma amostra antes de usar número em peça.
  · Juiz: o eproc publica só o dispositivo, muitas vezes sem assinatura (juiz = vazio).
  · Mediana com n < 10 não é tendência. O relatório marca.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import socket
import sqlite3
import statistics as st
import sys
import time
import unicodedata
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
import urllib3.util.connection as _conn

# o IPv6 do comunicaapi não responde: o curl cai para v4 sozinho, o requests trava
_conn.allowed_gai_family = lambda: socket.AF_INET

BASE = Path(__file__).resolve().parent
DB = BASE / "jurimetria.sqlite"
RELATORIOS = BASE / "relatorios"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
DJEN = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
DATAJUD = "https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search"
DATAJUD_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
INICIO_PADRAO = "2025-10-01"     # primeira coleta sem estado: um ano para trás

# ── temas ─────────────────────────────────────────────────────────────────────
# buscas: termos do DJEN (a busca é literal, e o mesmo ato volta em vários termos: dedup por id)
# confirma: o texto tem de casar isto para entrar no tema
# forte: o caso É sobre o tema (sem isso a menção é lateral, ex. conta de água que cita
#        "possibilidade de negativação"). Medido no TEXTO TODO, nunca só no dispositivo: só a
#        procedente manda excluir o nome, e o filtro no dispositivo jogava fora as improcedentes.
TEMAS = {
    "negativacao": {
        "rotulo": "Negativação indevida",
        "buscas": ["negativação", "cadastros de inadimplentes", "cadastro de inadimplentes",
                   "cadastro restritivo", "cadastros restritivos", "inscrição indevida",
                   "proteção ao crédito"],
        "confirma": r"negativa[çc][ãa]o|cadastros? (restritivos?|de (inadimplentes|prote[çc][ãa]o"
                    r" ao cr[ée]dito|maus pagadores))|\bSPC\b|SERASA|SCPC|inscri[çc][ãa]o (indevida"
                    r"|restritiva|nos? cadastros?|do nome)|apontamento restritivo|nome negativado",
        "forte": r"(exclus[ãa]o|retirada|cancelamento|baixa|excluir|retirar|cancelar|abster)[^.]{0,120}"
                 r"(nome|inscri|apontamento|anota[çc]|restri|negativa|cadastr)"
                 r"|(inscri[çc][ãa]o|negativa[çc][ãa]o|apontamento)[^.]{0,40}indevid"
                 r"|cadastros? (restritivos?|de (inadimplentes|prote[çc][ãa]o ao cr[ée]dito))",
        "datajud_assuntos": [6226],
    },
}

# ── base ──────────────────────────────────────────────────────────────────────

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sentencas (
    djen_id INTEGER PRIMARY KEY,
    chave TEXT,                 -- processo + hash do texto: o mesmo ato sai a várias partes
    tema TEXT, tema_forte INTEGER,
    processo TEXT, data_pub TEXT,
    orgao TEXT, id_orgao INTEGER, comarca TEXT, segmento TEXT,
    classe TEXT, tipo_documento TEXT, sistema TEXT,
    resultado TEXT,             -- procedente | parcial | improcedente | acordo | sem_merito | outro
    dano_moral REAL, dm_confianca TEXT, dm_negado INTEGER,
    juiz TEXT, juiz_cargo TEXT, juiz_leigo TEXT,
    link TEXT, texto_z BLOB, coletado_em TEXT
);
CREATE INDEX IF NOT EXISTS ix_sent_chave ON sentencas(chave);
CREATE INDEX IF NOT EXISTS ix_sent_orgao ON sentencas(tema, orgao);
CREATE TABLE IF NOT EXISTS datajud_orgao (
    tema TEXT, retrato TEXT, codigo INTEGER, nome TEXT, chave_orgao TEXT,
    processos INTEGER, procedente INTEGER, parcial INTEGER, improcedente INTEGER, acordo INTEGER,
    PRIMARY KEY (tema, retrato, codigo)
);
CREATE TABLE IF NOT EXISTS estado (tema TEXT PRIMARY KEY, coletado_ate TEXT);
"""


def abrir() -> sqlite3.Connection:
    con = sqlite3.connect(DB, timeout=300)   # a coleta diária pode estar gravando
    con.executescript(ESQUEMA)
    return con


# ── normalização ──────────────────────────────────────────────────────────────

def _limpa(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


_PALAVRAS_TIPO = {"VARA", "VARAS", "CIVEL", "CIVEIS", "JUIZADO", "JUIZADOS", "ESPECIAL", "ESPECIAIS",
                  "ADJUNTO", "COMARCA", "REGIONAL", "DA", "DE", "DO", "DAS", "DOS", "E", "UNICA", "V",
                  "CIV", "NUC", "JUST", "JUS", "JUSTICA", "NUCLEO", "SECRETARIA", "CARTORIO"}


def chave_orgao(nome: str) -> str:
    """'2ª Vara Cível da Regional de Bangu' e 'BANGU REGIONAL 2 VARA CIVEL' → 'VC|2|BANGU'."""
    s = _sem_acento(nome or "").upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    tipo = ("JEC" if "JUIZADO ESPECIAL" in s and "CIV" in s else
            "N40" if "NUC" in s and "4 0" in s else
            "VC" if "VARA CIVEL" in s or re.search(r"\bV CIV\b", s) else
            "V" if "VARA" in s else "?")
    num = re.search(r"\b(\d{1,3})\b", s)
    local = sorted(w for w in s.split() if w not in _PALAVRAS_TIPO and not w.isdigit()
                   and len(w) > 1)
    return f"{tipo}|{num.group(1) if num else ''}|{' '.join(local)}"


def _mesmo_orgao(a: str, b: str) -> bool:
    ta, na, la = a.split("|")
    tb, nb, lb = b.split("|")
    if ta != tb or na != nb:
        return False
    sa, sb = set(la.split()), set(lb.split())
    return bool(sa) and bool(sb) and (sa <= sb or sb <= sa)


# regionais que pertencem a outra comarca (o resto das "Regional de X" é da Capital)
REGIONAL_DE_OUTRA = {"ALCANTARA": "São Gonçalo", "VILA INHOMIRIM": "Magé", "INHOMIRIM": "Magé",
                     "ITAIPAVA": "Petrópolis", "INOA": "Maricá", "REGIAO OCEANICA": "Niterói",
                     "OCEANICA": "Niterói", "PENDOTIBA": "Niterói"}


def comarca_de(orgao: str, texto: str) -> str:
    o = orgao or ""
    m = re.search(r"Regional (?:de |da |do )?([^,()\-–]+)", o)
    if m:
        reg = _sem_acento(m.group(1)).upper().strip()
        return REGIONAL_DE_OUTRA.get(reg, "Capital")
    m = re.search(r"Comarca (?:de |da |do )([^,()\-–]+)", o)
    if m:
        c = m.group(1).strip()
        return "Capital" if c.lower() == "capital" else c
    if "Capital" in o:
        return "Capital"
    m = re.search(r"Comarca (?:de |da |do )([A-ZÀ-Ü][^,()]{2,40}?)\s+(?:\d+[ªº]|Juizado|Vara|Cart)", texto[:600])
    if m:
        c = m.group(1).strip()
        return "Capital" if c.lower() == "capital" else c
    return ""


def segmento_de(orgao: str, classe: str) -> str:
    o, c = (orgao or "").upper(), (classe or "").upper()
    if "NÚCLEO DE JUSTIÇA 4.0" in o or "NUCLEO DE JUSTICA 4.0" in o:
        return "nucleo40"
    if "JUIZADO ESPECIAL" in o or "JUIZADO ESPECIAL" in c:
        return "jec"
    if "VARA" in o:
        return "vara"
    return "outro"


# ── leitura da sentença ───────────────────────────────────────────────────────

_DISPOSITIVO = re.compile(r"(ante o exposto|diante do exposto|pelo exposto|isto posto|posto isso|"
                          r"por todo o exposto|em face do exposto|dispositivo|do exposto|"
                          r"por essas raz[õo]es|por tais (raz[õo]es|fundamentos)|isso posto)", re.I)


def dispositivo(t: str) -> str:
    ms = list(_DISPOSITIVO.finditer(t))
    if ms:
        return t[ms[-1].start():]
    j = re.search(r"JULGO|HOMOLOGO|julgo|homologo", t)
    return t[j.start():] if j else t[-1500:]


# o texto do DJEN vem com palavras coladas ("JULGO PROCEDENTESos", "eJULGO"): nada de \b aqui
_JULG = r"JULG(?:O|AR|A|AM|ADOS?|UEI)?\s*(?:[A-Z]+\s+){0,4}?"


def _resultado(s: str) -> str:
    if re.search(_JULG + r"PARCIALMENTE\s*PROCEDENTE|(?<!IM)PROCEDENTES?\s*EM\s*PARTE|PARCIAL\s*PROCEDENCIA", s):
        return "parcial"
    proc = re.search(_JULG + r"(?<!IM)PROCEDENTE|ACOLHO\s*(?:[A-Z]+\s+){0,3}PEDIDO", s)
    # "JULGO EXTINTO ... quanto ao 1º réu, e IMPROCEDENTES OS PEDIDOS quanto ao 2º": sem JULGO colado
    improc = re.search(_JULG + r"IMPROCEDENTE|REJEITO\s*(?:[A-Z]+\s+){0,3}PEDIDO|IMPROCEDENTES?\s*O?S?\s*PEDIDOS?", s)
    if proc and improc:
        return "parcial"          # "procedente o pedido X e improcedente o pedido Y"
    if improc:
        return "improcedente"
    if proc:
        return "procedente"
    if re.search(r"HOMOLOG\w*\s*(?:\w+\s+){0,6}(ACORDO|TRANSACAO)", s):
        return "acordo"
    if re.search(r"SEM\s*(RESOLUCAO|JULGAMENTO)\s*D[OE]\s*MERITO|ART(IGO)?\.?\s*485|JULGO\s*EXTINT", s):
        return "sem_merito"
    return "outro"


def resultado_de(d: str, t: str = "") -> str:
    s = _sem_acento(d).upper()
    if re.search(r"EMBARGOS DE DECLARA", s[:400]) and not re.search(_JULG + r"(IM)?PROCEDENTE", s):
        return "outro"
    r = _resultado(s)
    if r == "outro" and t:        # o marcador do dispositivo errou: tenta o fim do texto
        r = _resultado(_sem_acento(t[-3000:]).upper())
    return r


_VALOR = re.compile(r"R\$\s*([\d.]{1,12},\d{2})")
# "compensação" sozinha não: "compensação adicional de R$ 271,07" (parcela condominial) virava dano moral.
# "compensação por danos morais" já cai em "morais".
_MORAL = re.compile(r"dano\w*\s+mora\w*|mora(l|is)\b|extrapatrimonia", re.I)
_NAO_DM = re.compile(r"honor[áa]ri|custas|valor da causa|multa|di[áa]ria|por dia|limitad|teto|"
                     r"patamar|m[áa]xim|astreinte|restitu|devolu|em dobro|repeti[çc]|material|"
                     r"d[ée]bito|d[íi]vida|fatura|parcela|contrato|inexig|declar|cobran|lan[çc]amento|"
                     r"cr[ée]dito tribut|recibo|desconto", re.I)


_EXCLUI = re.compile(r"honor[áa]ri|custas|multa|astreinte|di[áa]ria|valor da causa|limitad|patamar", re.I)


def _num(v: str) -> float:
    return float(v.replace(".", "").replace(",", "."))


def _clausula(antes: str, depois: str) -> tuple[str, str]:
    """Só a cláusula do valor: do último ';' ou fim de frase antes dele até o próximo depois."""
    a = re.split(r";|\.\s+(?=[A-ZÀ-Ü])|\b[a-z]\)\s|\b[IVX]+\)\s|\(\d{1,2}\)|\b\d{1,2}\)", antes)[-1]
    # itens "(4)pagar", "3)condenar": o texto do DJEN vem colado, sem espaço depois do parêntese
    b = re.split(r";|\.\s+(?=[A-ZÀ-Ü])", depois)[0]
    return a, b


def dano_moral_de(d: str, resultado: str) -> tuple[float | None, str, int]:
    """(valor, confiança, negado). Valor por autor: o primeiro R$ que a condenação liga a 'moral'."""
    if resultado not in ("procedente", "parcial"):
        return None, "", 0
    achados = []
    for m in _VALOR.finditer(d):
        antes, depois = _clausula(d[max(0, m.start() - 300):m.start()], d[m.end():m.end() + 160])
        if _NAO_DM.search(antes[-50:]) and not _MORAL.search(antes[-50:] + depois[:60]):
            continue              # "multa diária de R$", "débito de R$"
        # "honorários... em R$ 800,00, considerando a sucumbência no pedido de danos morais"
        ult_moral = max((x.end() for x in _MORAL.finditer(antes)), default=-1)
        ult_exclui = max((x.end() for x in _EXCLUI.finditer(antes)), default=-1)
        if ult_exclui > ult_moral:
            continue
        if ult_moral >= 0 or _MORAL.search(depois[:130]):
            achados.append((_num(m.group(1)), "alta"))
        elif re.search(r"conden|pagar|pagamento", antes, re.I) and not _NAO_DM.search(antes + depois[:60]):
            achados.append((_num(m.group(1)), "baixa"))
    altos = [v for v, c in achados if c == "alta" and 100 <= v <= 500_000]
    if altos:
        return altos[0], "alta", 0
    baixos = [v for v, c in achados if 100 <= v <= 50_000]
    if baixos:
        return baixos[0], "baixa", 0
    negado = 1 if re.search(r"(improcedente|rejeit|indefir)[^.;]{0,90}mora(l|is)|mora(l|is)[^.;]{0,60}"
                            r"(n[ãa]o configurad|inexist|improcedente|afast)|mero aborrecimento", d, re.I) else 0
    return None, "", negado


_JUIZ = re.compile(r"([A-ZÀ-Ü][A-Za-zÀ-ü'.]+(?:\s+(?:d[aeo]s?|e|[A-ZÀ-Ü][A-Za-zÀ-ü'.]+)){1,8})"
                   r"\s*[-–,]?\s*(Ju[íi]z[a]?\s+(?:de\s+Direito|Titular|Substitut[oa]|em\s+Exerc[íi]cio|"
                   r"Leig[oa]|Auxiliar|Tabelar|Designad[oa])|JU[ÍI]Z[A]?\s+(?:DE\s+DIREITO|TITULAR|"
                   r"SUBSTITUT[OA]|LEIG[OA]|EM\s+EXERC[ÍI]CIO|AUXILIAR))")
_LIXO_NOME = re.compile(r"\b(ARQUIVE|BAIXA|INTIMEM|PUBLIQUE|SENTEN|REGISTRAD|ASSINAD|DOCUMENTO|"
                        r"ELETR[ÔO]NIC|DIAS|CPC|DATA|TRÂNSITO)", re.I)


def juiz_de(t: str) -> tuple[str, str, str]:
    """(togado, cargo, leigo) — o último togado que assina; o juiz leigo à parte (JEC)."""
    togado, cargo, leigo = "", "", ""
    for m in _JUIZ.finditer(t[-2500:]):
        nome = m.group(1).strip()
        palavras = nome.split()
        # o regex pega o fim da frase anterior: fica com as últimas palavras capitalizadas
        while palavras and (_LIXO_NOME.search(palavras[0]) or palavras[0].lower() in ("e", "de", "da", "do")):
            palavras.pop(0)
        if len(palavras) < 2:
            continue
        nome = " ".join(palavras[-7:])
        # "Fulana Juiz Titular Juiz de Direito": o cargo repetido grudava no nome
        nome = re.sub(r"\s+Ju[íi]za?(\s+\S+)*$", "", nome, flags=re.I)
        if len(nome.split()) < 2:
            continue
        nome = " ".join(w.capitalize() if w.lower() not in ("da", "de", "do", "das", "dos", "e")
                        else w.lower() for w in nome.split())
        c = re.sub(r"\s+", " ", m.group(2)).strip().capitalize()
        if "leig" in c.lower():
            leigo = nome
        else:
            togado, cargo = nome, c
    return togado, cargo, leigo


# ── coleta (DJEN) ─────────────────────────────────────────────────────────────

def djen(texto: str, ini: str, fim: str) -> list:
    itens, pag = [], 1
    while True:
        for tentativa in range(7):   # o DJEN dá 504 em rajadas: espera crescente, ~7 min no total
            try:
                r = requests.get(DJEN, headers=UA, timeout=90, params={
                    "siglaTribunal": "TJRJ", "texto": texto, "itensPorPagina": 100, "pagina": pag,
                    "dataDisponibilizacaoInicio": ini, "dataDisponibilizacaoFim": fim})
                if r.status_code == 429 and tentativa < 6:
                    time.sleep(20 * (tentativa + 1))
                    continue
                r.raise_for_status()
                break
            except requests.RequestException:
                if tentativa == 6:
                    raise
                time.sleep(15 * (tentativa + 1))
        j = r.json()
        lote = j.get("items", [])
        itens += lote
        if len(lote) < 100 or len(itens) >= (j.get("count") or 0):
            return itens
        pag += 1
        time.sleep(0.6)


def forte_de(tema: str, t: str) -> int:
    cfg = TEMAS[tema]
    return 1 if (len(re.findall(cfg["confirma"], t, re.I)) >= 3
                 or re.search(cfg["forte"], t, re.I)) else 0


def eh_sentenca(it: dict, t: str) -> bool:
    tipo = (it.get("tipoDocumento") or "").lower()
    if any(x in tipo for x in ("acórdão", "acordao", "apelação", "agravo", "recurso", "ementa")):
        return False
    orgao = (it.get("nomeOrgao") or "").upper()
    if any(x in orgao for x in ("CÂMARA", "CAMARA", "TURMA", "CONSELHO RECURSAL", "SECRETARIA DA")):
        return False
    if "sentença" in tipo or "sentenca" in tipo:
        return True
    return bool(re.search(r"\bSENTEN[ÇC]A\b", t[:800])) and bool(re.search(r"JULGO|HOMOLOGO", t, re.I))


def ler_item(it: dict, tema: str) -> dict | None:
    cfg = TEMAS[tema]
    t = _limpa(it.get("texto"))
    if not eh_sentenca(it, t) or not re.search(cfg["confirma"], t, re.I):
        return None
    d = dispositivo(t)
    res = resultado_de(d, t)
    dm, conf, negado = dano_moral_de(d, res)
    togado, cargo, leigo = juiz_de(t)
    orgao = (it.get("nomeOrgao") or "").strip()
    link = it.get("link") or ""
    return {
        "djen_id": it["id"],
        "chave": f'{it.get("numero_processo")}:{hashlib.sha1(t[:3000].encode()).hexdigest()[:12]}',
        "tema": tema,
        "tema_forte": forte_de(tema, t),
        "processo": it.get("numeroprocessocommascara") or it.get("numero_processo"),
        "data_pub": it.get("data_disponibilizacao"),
        "orgao": orgao, "id_orgao": it.get("idOrgao"),
        "comarca": comarca_de(orgao, t), "segmento": segmento_de(orgao, it.get("nomeClasse")),
        "classe": it.get("nomeClasse"), "tipo_documento": it.get("tipoDocumento"),
        "sistema": "eproc" if "eproc" in link else "pje" if "pje" in link else "",
        "resultado": res, "dano_moral": dm, "dm_confianca": conf, "dm_negado": negado,
        "juiz": togado, "juiz_cargo": cargo, "juiz_leigo": leigo,
        "link": link, "texto_z": zlib.compress(t.encode("utf-8")),
        "coletado_em": datetime.now().isoformat(timespec="seconds"),
    }


def coletar(tema: str, de: str | None, ate: str | None) -> None:
    con = abrir()
    if not de:
        row = con.execute("SELECT coletado_ate FROM estado WHERE tema=?", (tema,)).fetchone()
        de = ((date.fromisoformat(row[0]) + timedelta(days=1)).isoformat() if row else INICIO_PADRAO)
    ate = ate or (date.today() - timedelta(days=1)).isoformat()
    if de > ate:
        print(f"[{tema}] nada a coletar (já até {ate})")
        return
    ini = date.fromisoformat(de)
    fim_total = date.fromisoformat(ate)
    total_novos = 0
    while ini <= fim_total:
        fim = min(ini + timedelta(days=6), fim_total)   # janelas de 7 dias: o DJEN não pagina além de 10 mil
        vistos, novos = set(), 0
        for termo in TEMAS[tema]["buscas"]:
            for it in djen(termo, ini.isoformat(), fim.isoformat()):
                if it["id"] in vistos:
                    continue
                vistos.add(it["id"])
                reg = ler_item(it, tema)
                if not reg:
                    continue
                cols = ", ".join(reg)
                cur = con.execute(f"INSERT OR IGNORE INTO sentencas ({cols}) VALUES "
                                  f"({', '.join('?' * len(reg))})", list(reg.values()))
                novos += cur.rowcount
            time.sleep(0.6)
        con.execute("INSERT OR REPLACE INTO estado VALUES (?, ?)", (tema, fim.isoformat()))
        con.commit()
        total_novos += novos
        print(f"[{tema}] {ini}..{fim}: {len(vistos)} publicações, {novos} sentenças novas", flush=True)
        ini = fim + timedelta(days=1)
    print(f"[{tema}] fim: {total_novos} sentenças novas; base com "
          f"{con.execute('SELECT COUNT(*) FROM sentencas WHERE tema=?', (tema,)).fetchone()[0]}")


def reprocessar(tema: str) -> None:
    """Relê o texto guardado com as regras atuais (depois de ajustar um regex)."""
    con = abrir()
    rows = con.execute("SELECT djen_id, orgao, classe, texto_z FROM sentencas WHERE tema=?", (tema,)).fetchall()
    for djen_id, orgao, classe, tz in rows:
        t = zlib.decompress(tz).decode("utf-8")
        d = dispositivo(t)
        res = resultado_de(d, t)
        dm, conf, negado = dano_moral_de(d, res)
        togado, cargo, leigo = juiz_de(t)
        con.execute("UPDATE sentencas SET resultado=?, dano_moral=?, dm_confianca=?, dm_negado=?, juiz=?, "
                    "juiz_cargo=?, juiz_leigo=?, tema_forte=?, comarca=?, segmento=? WHERE djen_id=?",
                    (res, dm, conf, negado, togado, cargo, leigo, forte_de(tema, t),
                     comarca_de(orgao, t), segmento_de(orgao, classe), djen_id))
    con.commit()
    print(f"[{tema}] {len(rows)} sentenças relidas")


# ── DataJud ───────────────────────────────────────────────────────────────────

def datajud(tema: str) -> None:
    body = {"size": 0, "query": {"bool": {"filter": [
                {"terms": {"assuntos.codigo": TEMAS[tema]["datajud_assuntos"]}},
                {"term": {"grau.keyword": "G1"}}]}},
            "aggs": {"org": {"terms": {"field": "orgaoJulgador.codigo", "size": 1500},
                     "aggs": {"nome": {"terms": {"field": "orgaoJulgador.nome.keyword", "size": 1}},
                              "proc": {"filter": {"term": {"movimentos.codigo": 219}}},
                              "improc": {"filter": {"term": {"movimentos.codigo": 220}}},
                              "parcial": {"filter": {"term": {"movimentos.codigo": 221}}},
                              "acordo": {"filter": {"terms": {"movimentos.codigo": [466, 442]}}}}}}}
    h = {"Authorization": f"APIKey {DATAJUD_KEY}", "Content-Type": "application/json"}
    for tentativa in range(4):
        r = requests.post(DATAJUD, headers=h, json=body, timeout=300)
        if r.status_code == 200:
            break
        time.sleep(10 * (tentativa + 1))
    r.raise_for_status()
    hoje = date.today().isoformat()
    con = abrir()
    n = 0
    for b in r.json()["aggregations"]["org"]["buckets"]:
        nome = b["nome"]["buckets"][0]["key"] if b["nome"]["buckets"] else ""
        nome = nome.replace("�", "º")
        con.execute("INSERT OR REPLACE INTO datajud_orgao VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (tema, hoje, b["key"], nome, chave_orgao(nome), b["doc_count"], b["proc"]["doc_count"],
                     b["parcial"]["doc_count"], b["improc"]["doc_count"], b["acordo"]["doc_count"]))
        n += 1
    con.commit()
    print(f"[{tema}] DataJud: retrato de {hoje} com {n} órgãos")


# ── relatórios ────────────────────────────────────────────────────────────────

def _pct(xs: list[float], q: float) -> float | None:
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    i = int(k)
    return xs[i] if i + 1 >= len(xs) else xs[i] + (xs[i + 1] - xs[i]) * (k - i)


def _brl(v: float | None) -> str:
    if v is None:
        return "—"
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def _sentencas(con, tema: str, so_forte: bool = True) -> list[dict]:
    """Uma linha por processo: a sentença de mérito mais recente (embargos e repetições fora)."""
    q = ("SELECT processo, data_pub, orgao, comarca, segmento, resultado, dano_moral, dm_confianca, "
         "dm_negado, juiz, juiz_cargo, link, sistema FROM sentencas WHERE tema=?" +
         (" AND tema_forte=1" if so_forte else "") + " ORDER BY data_pub")
    cols = ["processo", "data_pub", "orgao", "comarca", "segmento", "resultado", "dano_moral",
            "dm_confianca", "dm_negado", "juiz", "juiz_cargo", "link", "sistema"]
    por_proc = {}
    for row in con.execute(q, (tema,)):
        d = dict(zip(cols, row))
        if d["resultado"] == "outro":
            continue
        d["chave_orgao"] = chave_orgao(d["orgao"])   # PJe e eproc dão nomes diferentes à mesma vara
        por_proc[d["processo"]] = d
    return list(por_proc.values())


def _resumo(linhas: list[dict]) -> dict:
    merito = [x for x in linhas if x["resultado"] in ("procedente", "parcial", "improcedente")]
    ganho = [x for x in merito if x["resultado"] in ("procedente", "parcial")]
    dms = [x["dano_moral"] for x in ganho if x["dano_moral"]]
    com_dm = len(dms)
    return {
        "n": len(linhas), "merito": len(merito),
        "ganho_pct": 100 * len(ganho) / len(merito) if merito else None,
        "dm_n": com_dm,
        "dm_pct_ganho": 100 * com_dm / len(ganho) if ganho else None,
        "dm_mediana": _pct(dms, .5), "dm_p25": _pct(dms, .25), "dm_p75": _pct(dms, .75),
        "dm_media": st.mean(dms) if dms else None,
        # quanto vale, em média, um caso que chega a sentença de mérito
        "esperado": (_pct(dms, .5) or 0) * com_dm / len(merito) if merito and dms else None,
        "acordo": sum(1 for x in linhas if x["resultado"] == "acordo"),
    }


def _linha_resumo(rotulo: str, r: dict) -> str:
    aviso = " ⚠️ n<10" if r["dm_n"] < 10 else ""
    ganho = f'{r["ganho_pct"]:.0f}%' if r["ganho_pct"] is not None else "—"
    dmp = f'{r["dm_pct_ganho"]:.0f}%' if r["dm_pct_ganho"] is not None else "—"
    return (f"| {rotulo} | {r['merito']} | {ganho} | {dmp} | {r['dm_n']}{aviso} | {_brl(r['dm_mediana'])} | "
            f"{_brl(r['dm_p25'])} a {_brl(r['dm_p75'])} | {_brl(r['esperado'])} |")


_CAB = ("| Recorte | Sentenças de mérito | Ganha (total ou parcial) | Das ganhas, com dano moral | n c/ valor "
        "| Mediana DM | Faixa p25-p75 | Valor esperado* |\n|---|---|---|---|---|---|---|---|")
_NOTA_ESPERADO = ("\\* Valor esperado = mediana do dano moral × chance de sair com dano moral, sobre as "
                  "sentenças de mérito. É a régua para proposta de acordo, antes de custas, honorários e "
                  "tempo.")


def _datajud_do(con, tema: str, orgao: str) -> dict | None:
    ret = con.execute("SELECT MAX(retrato) FROM datajud_orgao WHERE tema=?", (tema,)).fetchone()[0]
    if not ret:
        return None
    k = chave_orgao(orgao)
    soma, nomes = [0, 0, 0, 0, 0], []
    # a mesma vara tem vários códigos no DataJud (antigos, com poucos processos): somar todos
    for row in con.execute("SELECT nome, processos, procedente, parcial, improcedente, acordo, chave_orgao "
                           "FROM datajud_orgao WHERE tema=? AND retrato=?", (tema, ret)):
        if _mesmo_orgao(k, row[6]):
            nomes.append(row[0])
            for i in range(5):
                soma[i] += row[i + 1]
    if not nomes:
        return None
    n, p, pa, i, a = soma
    m = p + pa + i
    return {"nome": nomes[0], "retrato": ret, "n": n, "merito": m,
            "ganho_pct": 100 * (p + pa) / m if m else None, "acordo": a}


def _datajud_comarca(con, tema: str, chaves: list[str]) -> dict | None:
    ret = con.execute("SELECT MAX(retrato) FROM datajud_orgao WHERE tema=?", (tema,)).fetchone()[0]
    if not ret:
        return None
    soma = [0, 0, 0, 0]
    for row in con.execute("SELECT procedente, parcial, improcedente, processos, chave_orgao FROM datajud_orgao "
                           "WHERE tema=? AND retrato=?", (tema, ret)):
        if any(_mesmo_orgao(k, row[4]) for k in chaves):
            for i in range(4):
                soma[i] += row[i]
    m = soma[0] + soma[1] + soma[2]
    return {"retrato": ret, "n": soma[3], "merito": m, "ganho_pct": 100 * (soma[0] + soma[1]) / m if m else None}


def _nome_bonito(xs: list[dict]) -> str:
    """O nome do PJe ('4ª Vara Cível da Regional de Bangu'), não o do eproc ('... - Cartório da ...')."""
    nomes = [x["orgao"] for x in xs]
    bons = [n for n in nomes if "Cartório" not in n]
    if bons:
        return max(set(bons), key=bons.count)
    n = max(set(nomes), key=nomes.count)   # só eproc: "Regional de Bangu- Cartório da 4ª Vara Cível" vira o nome do PJe
    m = re.match(r"(.+?)\s*-\s*Cartório d[aoe]s? (.+)$", n)
    return f"{m.group(2)} da {m.group(1)}" if m else n


def _cabecalho(con, tema: str, titulo: str) -> list[str]:
    datas = con.execute("SELECT MIN(data_pub), MAX(data_pub) FROM sentencas WHERE tema=?", (tema,)).fetchone()
    return [f"# {titulo}", "",
            f"Tema: **{TEMAS[tema]['rotulo']}** · TJRJ · sentenças publicadas no DJEN de "
            f"{datas[0]} a {datas[1]} · gerado em {date.today().isoformat()}", ""]


def _salvar(nome: str, linhas: list[str]) -> None:
    RELATORIOS.mkdir(exist_ok=True)
    arq = RELATORIOS / nome
    arq.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))
    print(f"\n(salvo em {arq})")


def antes(tema: str, comarca: str, segmento: str | None) -> None:
    con = abrir()
    todas = _sentencas(con, tema)
    if segmento:
        todas = [x for x in todas if x["segmento"] == segmento]
    da_comarca = [x for x in todas if x["comarca"].lower() == comarca.lower()]
    seg = {"jec": "Juizados Especiais Cíveis", "vara": "Varas Cíveis"}.get(segmento or "", "JEC + varas")
    out = _cabecalho(con, tema, f"Antes da distribuição: {comarca} ({seg})")
    out += [_CAB, _linha_resumo("TJRJ inteiro", _resumo(todas)),
            _linha_resumo(f"Comarca: {comarca}", _resumo(da_comarca)), "", _NOTA_ESPERADO, ""]
    # a faixa entre os juízos: é o risco do sorteio
    por_orgao: dict[str, list] = {}
    for x in da_comarca:
        por_orgao.setdefault(x["chave_orgao"], []).append(x)
    nomes = {k: _nome_bonito(xs) for k, xs in por_orgao.items()}
    linhas = [(nomes[k], _resumo(xs)) for k, xs in por_orgao.items()]
    linhas = [l for l in linhas if l[1]["merito"] >= 3]
    linhas.sort(key=lambda l: -(l[1]["esperado"] or 0))
    out += [f"## O risco do sorteio: os juízos de {comarca} (com 3+ sentenças de mérito)", "",
            "| Juízo | Mérito | Ganha | Mediana DM (n) | Esperado | DataJud: ganha (n mérito) |",
            "|---|---|---|---|---|---|"]
    for o, r in linhas:
        dj = _datajud_do(con, tema, o)
        djs = f'{dj["ganho_pct"]:.0f}% ({dj["merito"]})' if dj and dj["ganho_pct"] is not None else "—"
        g = f'{r["ganho_pct"]:.0f}%' if r["ganho_pct"] is not None else "—"
        out.append(f"| {o} | {r['merito']} | {g} | {_brl(r['dm_mediana'])} ({r['dm_n']}) | "
                   f"{_brl(r['esperado'])} | {djs} |")
    esperados = [r["esperado"] for _, r in linhas if r["esperado"] and r["dm_n"] >= 5]
    if esperados:
        out += ["", f"Entre os juízos com 5+ valores, o valor esperado vai de **{_brl(min(esperados))}** "
                    f"a **{_brl(max(esperados))}**. Essa distância é o que o sorteio decide."]
    sem_val = [k for k in por_orgao if all(not x["dano_moral"] for x in por_orgao[k])]
    out += ["", f"Juízos da comarca na base: {len(por_orgao)} ({len(sem_val)} sem nenhum valor de dano "
                f"moral extraído)."]
    slug = re.sub(r"\W+", "_", _sem_acento(f"{comarca}_{segmento or 'todos'}")).strip("_").lower()
    _salvar(f"{date.today().isoformat()}_{tema}_antes_{slug}.md", out)


def depois(tema: str, orgao_busca: str) -> None:
    con = abrir()
    todas = _sentencas(con, tema)
    k = chave_orgao(orgao_busca)
    do_orgao = [x for x in todas if _mesmo_orgao(k, x["chave_orgao"])]
    if not do_orgao:
        alvo = _sem_acento(orgao_busca).lower()
        do_orgao = [x for x in todas if alvo in _sem_acento(x["orgao"]).lower()]
    if not do_orgao:
        print(f"Nenhuma sentença de '{orgao_busca}' na base. Órgãos parecidos:")
        pal = set(_sem_acento(orgao_busca).lower().split())
        nomes = sorted({x["orgao"] for x in todas if pal & set(_sem_acento(x["orgao"]).lower().split())})
        print("\n".join("  " + n for n in nomes[:20]))
        return
    nome = _nome_bonito(do_orgao)
    comarca, seg = do_orgao[-1]["comarca"], do_orgao[-1]["segmento"]
    mesma = [x for x in todas if x["segmento"] == seg]
    da_comarca = [x for x in mesma if x["comarca"] == comarca]
    ro, rc, re_ = _resumo(do_orgao), _resumo(da_comarca), _resumo(mesma)
    out = _cabecalho(con, tema, f"Depois da distribuição: {nome}")
    out += [_CAB, _linha_resumo(f"**{nome}**", ro), _linha_resumo(f"Comarca: {comarca or '?'} ({seg})", rc),
            _linha_resumo(f"TJRJ ({seg})", re_), "", _NOTA_ESPERADO, ""]
    if ro["dm_mediana"] and rc["dm_mediana"]:
        dif = 100 * (ro["dm_mediana"] / rc["dm_mediana"] - 1)
        out.append(f"Mediana do dano moral **{dif:+.0f}%** em relação à comarca "
                   f"({_brl(ro['dm_mediana'])} contra {_brl(rc['dm_mediana'])}).")
    if ro["ganho_pct"] is not None and rc["ganho_pct"] is not None:
        out.append(f"Chance de ganhar (total ou parcial): **{ro['ganho_pct']:.0f}%** aqui contra "
                   f"{rc['ganho_pct']:.0f}% na comarca.")
    dj = _datajud_do(con, tema, nome)
    if dj and dj["ganho_pct"] is not None:
        out.append(f"DataJud (todo o histórico do assunto, retrato de {dj['retrato']}): {dj['n']} processos, "
                   f"{dj['merito']} sentenças de mérito, **{dj['ganho_pct']:.0f}%** ganhas, {dj['acordo']} "
                   f"acordos homologados.")
    # por juiz
    por_juiz: dict[str, list] = {}
    for x in do_orgao:
        por_juiz.setdefault(x["juiz"] or "(sem assinatura no DJEN)", []).append(x)
    out += ["", "## Por juiz que assinou", "",
            "| Juiz | Cargo | Mérito | Ganha | Mediana DM (n) | Faixa | Última |", "|---|---|---|---|---|---|---|"]
    for j, xs in sorted(por_juiz.items(), key=lambda kv: -len(kv[1])):
        r = _resumo(xs)
        cargo = next((x["juiz_cargo"] for x in reversed(xs) if x["juiz_cargo"]), "")
        g = f'{r["ganho_pct"]:.0f}%' if r["ganho_pct"] is not None else "—"
        out.append(f"| {j} | {cargo} | {r['merito']} | {g} | {_brl(r['dm_mediana'])} ({r['dm_n']}) | "
                   f"{_brl(r['dm_p25'])} a {_brl(r['dm_p75'])} | {xs[-1]['data_pub']} |")
    out += ["", "## Últimas sentenças", "", "| Data | Processo | Resultado | Dano moral | Juiz |",
            "|---|---|---|---|---|"]
    for x in sorted(do_orgao, key=lambda x: x["data_pub"], reverse=True)[:15]:
        dm = _brl(x["dano_moral"]) + (" (?)" if x["dm_confianca"] == "baixa" else "") if x["dano_moral"] else (
            "negado" if x["dm_negado"] else "—")
        out.append(f"| {x['data_pub']} | [{x['processo']}]({x['link']}) | {x['resultado']} | {dm} | {x['juiz']} |")
    out += ["", "(?) = valor achado na condenação sem a palavra \"moral\" por perto: conferir no link."]
    slug = re.sub(r"\W+", "_", _sem_acento(nome)).strip("_").lower()[:60]
    _salvar(f"{date.today().isoformat()}_{tema}_depois_{slug}.md", out)


# ── taxa de reforma por juiz ──────────────────────────────────────────────────
# O histórico da vara mistura juízes. Aqui o recorte é o JUIZ: as sentenças assinadas por ele no
# DJEN (busca pelo nome) e o que o 2º grau fez com cada uma no DataJud. Só conta acórdão posterior
# à sentença dele: o processo pode ter subido antes, contra sentença de outro juiz.
# TPU do 2º grau. Embargos de declaração (198, 200, 871) não entram: não decidem a apelação.
G2_PROVIMENTO = {237, 972}
G2_PARCIAL = {238}
G2_NAO_PROVIMENTO = {239, 242, 901}
G2_NAO_CONHECIDO = {235, 230}
G2_ANULACAO = {11373}
G2_ACORDO = {466}
G2_DECISAO = G2_PROVIMENTO | G2_PARCIAL | G2_NAO_PROVIMENTO | G2_NAO_CONHECIDO | G2_ANULACAO | G2_ACORDO
TIPO_SENTENCA = {219: "procedente", 220: "improcedente", 221: "parcial"}


def _datajud_post(body: dict) -> dict:
    """O cluster do CNJ dá 429/504 em rajadas (28/10/2026, o dia todo): espera longa e insiste."""
    h = {"Authorization": f"APIKey {DATAJUD_KEY}", "Content-Type": "application/json"}
    for tentativa in range(12):
        try:
            r = requests.post(DATAJUD, headers=h, json=body, timeout=120)
            if r.status_code == 200:
                return r.json()
            print(f"http {r.status_code}", end=" ", flush=True)
        except requests.RequestException:
            print("timeout", end=" ", flush=True)
        time.sleep(min(10 * (tentativa + 1), 90))
    raise SystemExit("DataJud não respondeu depois de 12 tentativas (o que já chegou está no cache: rode de novo)")


def _meses(de: str, ate: str):
    d, fim = date.fromisoformat(de).replace(day=1), date.fromisoformat(ate)
    while d <= fim:
        prox = (d + timedelta(days=32)).replace(day=1)
        yield d.isoformat(), min(prox - timedelta(days=1), fim).isoformat()
        d = prox


def _sentencas_do_juiz(juiz: str, de: str, ate: str) -> dict[str, tuple[str, str]]:
    """{número só com dígitos: (data da disponibilização, órgão)} das sentenças com o nome dele."""
    out: dict[str, tuple[str, str]] = {}
    for ini, fim in _meses(de, ate):
        for it in djen(juiz, ini, fim):
            org = it.get("nomeOrgao") or ""
            if "Senten" not in (it.get("tipoDocumento") or "") or not re.search(r"Vara|Cart", org):
                continue
            n = re.sub(r"\D", "", it.get("numeroprocessocommascara") or it.get("numero_processo") or "")
            if n:
                out.setdefault(n, ((it.get("data_disponibilizacao") or "")[:10], org))
        print(f"{ini[:7]}: {len(out)} sentenças", flush=True)
    return out


def _resultado_g2(movs: list[dict], desde: str) -> tuple[str, str]:
    """Primeira decisão do 2º grau a partir de `desde`; no mesmo dia, a anulação prevalece."""
    ms = sorted((m for m in movs if m.get("codigo") in G2_DECISAO and (m.get("dataHora") or "")[:10] >= desde),
                key=lambda m: m["dataHora"])
    if not ms:
        return "pendente", ""
    d = ms[0]["dataHora"][:10]
    cods = {m["codigo"] for m in ms if m["dataHora"][:10] == d}
    if cods & G2_ANULACAO:
        return "anulada", d
    if cods & G2_PROVIMENTO and not cods & G2_NAO_PROVIMENTO:
        return "provida", d
    if cods & (G2_PROVIMENTO | G2_PARCIAL):
        return "parcial", d
    if cods & G2_NAO_PROVIMENTO:
        return "mantida", d
    if cods & G2_ACORDO:
        return "acordo", d
    return "nao_conhecida", d


def _wilson(k: int, n: int) -> tuple[float, float]:
    if not n:
        return 0.0, 0.0
    z, p = 1.96, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return max(0.0, c - m), min(1.0, c + m)


def _linha_reforma(rotulo: str, rs: list[dict]) -> str:
    js = [x for x in rs if x["resultado"] in ("provida", "parcial", "anulada", "mantida")]
    n = len(js)
    if not n:
        return f"| {rotulo} | 0 | | | | | | |"
    c = {k: sum(1 for x in js if x["resultado"] == k) for k in ("provida", "parcial", "anulada", "mantida")}
    alguma = n - c["mantida"]
    lo, hi = _wilson(alguma, n)
    aviso = " ⚠️" if n < 10 else ""
    return (f"| {rotulo} | {n}{aviso} | {c['provida']} ({c['provida'] / n:.0%}) | {c['parcial']} | {c['anulada']} "
            f"| {c['mantida']} | **{alguma / n:.0%}** | {lo:.0%} a {hi:.0%} |")


def reforma(juiz: str, de: str, ate: str | None, refazer: bool = False) -> None:
    ate = ate or (date.today() - timedelta(days=1)).isoformat()
    slug = re.sub(r"[^a-z]+", "_", _sem_acento(juiz).lower()).strip("_")
    RELATORIOS.mkdir(exist_ok=True)
    cache = RELATORIOS / f"reforma_{slug}_djen.json"
    if cache.exists() and not refazer:
        sent = {k: tuple(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
        print(f"DJEN: {len(sent)} sentenças do cache ({cache.name}; --refazer baixa de novo)")
    else:
        sent = _sentencas_do_juiz(juiz, de, ate)
        cache.write_text(json.dumps(sent, ensure_ascii=False), encoding="utf-8")
    nums = sorted(sent)
    # cada lote vai para o cache assim que chega: se o DataJud cair no meio, a próxima rodada retoma
    cache_dj = RELATORIOS / f"reforma_{slug}_datajud.json"
    dj = json.loads(cache_dj.read_text(encoding="utf-8")) if cache_dj.exists() and not refazer else {}
    feitos = set(dj.get("feitos", []))
    g1: dict[str, list] = dj.get("G1", {})
    g2: dict[str, list] = dj.get("G2", {})
    print(f"DataJud ({len(feitos)} processos do cache):", end=" ", flush=True)
    faltam = [n for n in nums if n not in feitos]
    for i in range(0, len(faltam), 50):
        lote = faltam[i:i + 50]
        for grau, dest in (("G1", g1), ("G2", g2)):
            body = {"size": 400, "_source": ["numeroProcesso", "movimentos.codigo", "movimentos.dataHora"],
                    "query": {"bool": {"filter": [{"terms": {"numeroProcesso": lote}},
                                                  {"term": {"grau.keyword": grau}}]}}}
            for h in _datajud_post(body)["hits"]["hits"]:
                s = h["_source"]
                dest.setdefault(s["numeroProcesso"], []).extend(
                    {"codigo": m.get("codigo"), "dataHora": m.get("dataHora")} for m in s.get("movimentos") or [])
        feitos.update(lote)
        cache_dj.write_text(json.dumps({"feitos": sorted(feitos), "G1": g1, "G2": g2}), encoding="utf-8")
        print(i + len(lote), end=" ", flush=True)
    print()
    linhas_csv = []
    for n in nums:
        if n not in g2:
            continue
        data_sent, org = sent[n]
        resultado, data_ac = _resultado_g2(g2[n], data_sent)
        # tipo: o último 219/220/221 do 1º grau até a publicação (folga de 5 dias para o registro)
        lim = (date.fromisoformat(data_sent) + timedelta(days=5)).isoformat() if data_sent else "9999"
        ss = sorted(((m.get("dataHora") or "")[:10], m["codigo"]) for m in g1.get(n, [])
                    if m.get("codigo") in TIPO_SENTENCA and (m.get("dataHora") or "")[:10] <= lim)
        linhas_csv.append({"processo": n, "orgao": org, "data_sentenca": data_sent,
                           "tipo": TIPO_SENTENCA[ss[-1][1]] if ss else "?",
                           "resultado": resultado, "data_acordao": data_ac})
    arq_csv = RELATORIOS / f"reforma_{slug}_{date.today().isoformat()}.csv"
    with arq_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas_csv[0]) if linhas_csv else ["processo"], delimiter=";")
        w.writeheader()
        w.writerows(linhas_csv)
    cab = "| Recorte | Julgadas | Reformada no todo | Em parte | Anulada | Mantida | Alguma reforma | IC 95% |"
    sep = "|---|---|---|---|---|---|---|---|"
    orgaos = sorted({x["orgao"] for x in linhas_csv}, key=lambda o: -sum(1 for x in linhas_csv if x["orgao"] == o))
    out = [f"# Taxa de reforma: {juiz}", "",
           f"TJRJ · sentenças com o nome do juiz no DJEN de {de} a {ate} · 2º grau no DataJud · "
           f"gerado em {date.today().isoformat()}", "",
           f"- Sentenças achadas no DJEN: **{len(nums)}**; com registro no 2º grau: **{len(linhas_csv)}**",
           f"- Pendentes de julgamento: {sum(1 for x in linhas_csv if x['resultado'] == 'pendente')}; "
           f"não conhecidas: {sum(1 for x in linhas_csv if x['resultado'] == 'nao_conhecida')}; "
           f"acordo: {sum(1 for x in linhas_csv if x['resultado'] == 'acordo')} (fora da conta)", "",
           "## Por tipo de sentença", "", cab, sep,
           _linha_reforma("Todas", linhas_csv)]
    out += [_linha_reforma(t.capitalize(), [x for x in linhas_csv if x["tipo"] == t])
            for t in ("improcedente", "parcial", "procedente", "?")]
    out += ["", "## Por órgão", "", cab, sep]
    for o in orgaos:
        out.append(_linha_reforma(o, [x for x in linhas_csv if x["orgao"] == o]))
        out.append(_linha_reforma(f"↳ improcedências", [x for x in linhas_csv if x["orgao"] == o
                                                         and x["tipo"] == "improcedente"]))
    out += ["", "## Como ler",
            "- **O número que decide é a reforma no todo.** \"Em parte\" inclui ajuste de juros, honorários e "
            "valor, que não muda quem venceu.",
            "- Só entra o que foi apelado: quem recorre acha que vai ganhar (viés de seleção). O DataJud não diz "
            "quem apelou; na improcedência é, em regra, o autor.",
            "- \"?\" = o DataJud não tem o movimento da sentença (219/220/221) no 1º grau.",
            "- n < 10 (⚠️) não é tendência. O IC 95% (Wilson) mostra a faixa plausível.",
            f"- Processos e resultados em `{arq_csv.name}`."]
    _salvar(f"reforma_{slug}_{date.today().isoformat()}.md", out)


def rotina() -> None:
    """Tarefa agendada (diária): todos os temas até ontem; DataJud a cada 30 dias."""
    con = abrir()
    for tema in TEMAS:
        try:   # falha do DJEN num tema: o estado guarda a última semana boa e a próxima rodada retoma dali
            coletar(tema, None, None)
        except requests.RequestException as e:
            print(f"[{tema}] coleta interrompida: {e}")
        ret = con.execute("SELECT MAX(retrato) FROM datajud_orgao WHERE tema=?", (tema,)).fetchone()[0]
        if not ret or (date.today() - date.fromisoformat(ret)).days >= 30:
            datajud(tema)
    exportar()


def exportar() -> None:
    con = abrir()
    cols = ["djen_id", "tema", "tema_forte", "processo", "data_pub", "orgao", "id_orgao", "comarca", "segmento",
            "classe", "tipo_documento", "sistema", "resultado", "dano_moral", "dm_confianca", "dm_negado",
            "juiz", "juiz_cargo", "juiz_leigo", "link"]
    arq = BASE / "sentencas.csv"
    with arq.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cols)
        for row in con.execute(f"SELECT {', '.join(cols)} FROM sentencas ORDER BY data_pub"):
            w.writerow(["" if v is None else (f"{v:.2f}".replace(".", ",") if isinstance(v, float) else v)
                        for v in row])
    print(f"exportado: {arq}")


def main() -> int:
    # console do Windows em cp1252 quebra no ⚠️ do relatório (e `python -I` ignora PYTHONIOENCODING)
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("coletar", "datajud", "antes", "depois", "exportar", "reprocessar", "rotina"):
        p = sub.add_parser(nome)
        p.add_argument("--tema", default="negativacao", choices=sorted(TEMAS))
        if nome == "coletar":
            p.add_argument("--de")
            p.add_argument("--ate")
        if nome == "antes":
            p.add_argument("--comarca", required=True)
            p.add_argument("--segmento", choices=["jec", "vara", "nucleo40"])
        if nome == "depois":
            p.add_argument("--orgao", required=True)
    p = sub.add_parser("reforma")
    p.add_argument("--juiz", required=True, help="nome completo, como sai na assinatura")
    p.add_argument("--de", required=True)
    p.add_argument("--ate")
    p.add_argument("--refazer", action="store_true", help="baixa o DJEN de novo, ignorando o cache")
    a = ap.parse_args()
    if a.cmd == "reforma":
        reforma(a.juiz, a.de, a.ate, a.refazer)
    elif a.cmd == "coletar":
        coletar(a.tema, a.de, a.ate)
    elif a.cmd == "datajud":
        datajud(a.tema)
    elif a.cmd == "antes":
        antes(a.tema, a.comarca, a.segmento)
    elif a.cmd == "depois":
        depois(a.tema, a.orgao)
    elif a.cmd == "reprocessar":
        reprocessar(a.tema)
    elif a.cmd == "rotina":
        rotina()
    else:
        exportar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
