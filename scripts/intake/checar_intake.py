# -*- coding: utf-8 -*-
r"""checar_intake.py — diz se o intake de um caso pode ser lido como a ficha do caso.

Passo 1 da skill /intake: antes de analisar, minutar ou opinar, abrir o intake e saber se ele
é real. Só leitura: não grava nada. Só biblioteca padrão do Python 3.10+.

O que confere:
  🔴 casca: `completo: false`, a marca de ficha criada por rotina automática ou menos de 1 KB
     → reconstruir pelos autos ANTES de minutar;
  🟡 sem o bloco "Dados cadastrais", sem CPF/CNPJ, campos de Processo vazios (vara, comarca,
     distribuição, parte adversa) quando há nº CNJ;
  🟡 `atualizado:` há mais de 30 dias (ficha velha contamina a peça);
  🟡 arquivo fora de UTF-8;
  marcadores abertos ([INSERIR], [COMPLETAR], [VERIFICAR]...) e pendências `- [ ]`.
Também lista os intakes das OUTRAS matérias do mesmo cliente, que podem ter avisos que valem
para o caso.

Acervo esperado: <raiz>\<Cliente>\[<Caso>\]intake.md. Pastas da raiz que começam com dígito e
ponto ("00. Inbox", "02. Modelos") ou com "_" não são clientes.

Uso:
  python checar_intake.py "<pasta do caso>"          # ou o próprio intake.md
  python checar_intake.py "Nome do Cliente"           # pasta do cliente na raiz do acervo
  python checar_intake.py --cnj 0000000-00.0000.0.00.0000
  ... --raiz "<acervo>"   (ou a variável INTAKE_ROOT; padrão: a pasta atual)   --json   --todas
"""
from __future__ import annotations

import os
import re
import sys
import json
import argparse
import datetime as dt
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RE_PULAR = re.compile(r"^(\d+\.|_)")
MARCA_CASCA = "criado automaticamente"
RE_MARCADOR = re.compile(r"\[(INSERIR|COMPLETAR|VERIFICAR|CONFERIR|CONFIRMAR|PEDIR|PREENCHER)\b[^\]]*\]")
RE_CPF_CNPJ = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
RE_CNJ = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
RE_ATUALIZADO = re.compile(r"^atualizado:\s*(\d{4}-\d{2}-\d{2})", re.M)
# `- **Rótulo:** valor`; [ \t]* e não \s*, senão um rótulo em branco pega a linha seguinte
RE_CAMPO = re.compile(r"^[ \t]*[-*][ \t]*\*\*(.+?)[ \t]*:[ \t]*\*\*[ \t]*(.*)$", re.M)
VAZIOS = {"", "-", "—", "[verificar]", "[inserir]", "(verificar)", "n/a", "na"}
# campos que um processo com nº CNJ precisa ter (rótulos aceitos, sem acento e minúsculos)
OBRIGATORIOS = {
    "Vara": ("vara", "juizo", "orgao julgador"),
    "Comarca": ("comarca",),
    "Data de distribuição": ("data de distribuicao", "distribuicao", "data de ajuizamento"),
    "Parte adversa": ("parte adversa", "adversario", "reu", "re", "autor", "requerido", "executado"),
}
DIAS_VELHO = 30
MAX_DETALHE = 4
MAX_RESUMO = 8


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn")).lower().strip()


def eh_casca(t: str) -> bool:
    if re.search(r"^completo:\s*false\s*$", t, re.M):
        return True
    if re.search(r"^completo:\s*true\s*$", t, re.M):
        return False
    return MARCA_CASCA in t or len(t.encode("utf-8")) < 1024


def campos(t: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in RE_CAMPO.finditer(t):
        out.setdefault(_norm(m.group(1)), m.group(2).strip())
    return out


def avaliar(p: Path, raiz: Path) -> dict:
    alertas: list[str] = []
    try:
        p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        alertas.append("🟡 arquivo fora de UTF-8: regravar em UTF-8")
    t = p.read_text(encoding="utf-8", errors="replace")
    casca = eh_casca(t)
    if casca:
        alertas.append("🔴 CASCA: não minutar a partir dela; reconstruir pela inicial, procuração e autos")
    elif "Dados cadastrais" not in t:
        alertas.append("🟡 sem o bloco 'Dados cadastrais'")
    if not RE_CPF_CNPJ.search(t):
        alertas.append("🟡 nenhum CPF/CNPJ na ficha: qualificação incompleta")
    f = campos(t)
    processo = f.get("processo", "")
    if RE_CNJ.search(processo):
        faltam = [rot for rot, chaves in OBRIGATORIOS.items()
                  if not any(_norm(f.get(k, "")).strip("*: ") not in VAZIOS for k in chaves)]
        if faltam:
            alertas.append("🟡 Processo sem: " + ", ".join(faltam))
    m = RE_ATUALIZADO.search(t)
    atualizado = m.group(1) if m else None
    dias = (dt.date.today() - dt.date.fromisoformat(atualizado)).days if atualizado else None
    if dias is None:
        alertas.append("🟡 sem `atualizado:` no frontmatter")
    elif dias > DIAS_VELHO:
        alertas.append(f"🟡 atualizado há {dias} dias: conferir os andamentos antes de confiar")
    try:
        pasta = str(p.parent.relative_to(raiz))
    except ValueError:
        pasta = str(p.parent)
    return {
        "intake": str(p), "pasta": pasta, "bytes": len(t.encode("utf-8")), "casca": casca,
        "atualizado": atualizado, "dias_desde_atualizacao": dias,
        "marcadores_abertos": len(RE_MARCADOR.findall(t)),
        "pendencias_abertas": len(re.findall(r"^\s*- \[ \]", t, re.M)),
        "processo": processo, "alertas": alertas,
        "veredito": "reconstruir antes de minutar" if casca else
                    ("ler e completar no mesmo ato" if alertas else "ok para ler"),
    }


def _pasta_cliente(p: Path, raiz: Path) -> Path | None:
    try:
        rel = p.resolve().relative_to(raiz)
    except ValueError:
        return None
    return raiz / rel.parts[0] if rel.parts and not RE_PULAR.match(rel.parts[0]) else None


def _cliente_por_nome(nome: str, raiz: Path) -> Path | None:
    alvo = _norm(nome)
    pastas = [d for d in raiz.iterdir() if d.is_dir() and not RE_PULAR.match(d.name)]
    exatos = [d for d in pastas if _norm(d.name) == alvo]
    if exatos:
        return exatos[0]
    parecidos = [d for d in pastas if alvo in _norm(d.name)]
    if len(parecidos) > 1:
        raise SystemExit("mais de uma pasta casa com o nome: " + "; ".join(d.name for d in parecidos))
    return parecidos[0] if parecidos else None


def _por_cnj(cnj: str, raiz: Path) -> list[Path]:
    dig = re.sub(r"\D", "", cnj)
    achados = []
    for p in raiz.rglob("intake.md"):
        if RE_PULAR.match(p.relative_to(raiz).parts[0]):
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        if dig in re.sub(r"\D", "", t) or dig in re.sub(r"\D", "", str(p.parent)):
            achados.append(p)
    return achados


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Confere se o intake do caso é real (só leitura).")
    ap.add_argument("alvo", nargs="?", help="pasta do caso, intake.md ou nome do cliente")
    ap.add_argument("--cnj")
    ap.add_argument("--raiz", default=os.environ.get("INTAKE_ROOT", "."), help="raiz do acervo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--todas", action="store_true", help="lista todas as outras fichas do cliente")
    a = ap.parse_args(argv)
    if not a.alvo and not a.cnj:
        ap.error("informe a pasta, o cliente ou --cnj")
    raiz = Path(a.raiz).resolve()

    if a.cnj:
        principais = _por_cnj(a.cnj, raiz)
        cli = _pasta_cliente(principais[0], raiz) if principais else None
    elif Path(a.alvo).exists():
        p = Path(a.alvo)
        principais = [p] if p.is_file() else ([p / "intake.md"] if (p / "intake.md").exists() else [])
        cli = _pasta_cliente(p, raiz) or (p if p.is_dir() else None)
    else:
        principais, cli = [], _cliente_por_nome(a.alvo, raiz)
        if not cli:
            raise SystemExit(f"não achei pasta nem cliente: {a.alvo}")
    principais = [p.resolve() for p in principais]
    outros = [p.resolve() for p in sorted(cli.rglob("intake.md"))] if cli else []
    outros = [p for p in outros if p not in principais]

    if not principais and not outros:
        msg = "Nenhum intake.md. Caso sem ficha: criar com criar_intake.py e preencher pelos autos ANTES de minutar."
        print(json.dumps({"intakes": [], "aviso": msg}, ensure_ascii=False) if a.json else msg)
        return 0
    res = {"principal": [avaliar(p, raiz) for p in principais],
           "outras_materias": [avaliar(p, raiz) for p in outros]}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    detalhar = res["principal"] or res["outras_materias"][:MAX_DETALHE]
    print("== Intake do caso ==" if res["principal"] else "== Intakes do cliente ==")
    for r in detalhar:
        print(f"• {r['pasta']}  ({r['bytes']} B, atualizado {r['atualizado'] or '?'}, "
              f"{r['marcadores_abertos']} marcador(es), {r['pendencias_abertas']} pendência(s))")
        print(f"    → {r['veredito'].upper()}")
        for al in r["alertas"]:
            print(f"    {al}")
    resto = [r for r in res["outras_materias"] if r not in detalhar]
    if resto:
        print(f"\n== Outras fichas do cliente ({len(resto)}): ler as da MESMA história ==")
        for r in resto[: (None if a.todas else MAX_RESUMO)]:
            print(f"  {'🔴' if r['casca'] else '🟡' if r['alertas'] else '✅'} {r['pasta']} — {r['veredito']}")
        if not a.todas and len(resto) > MAX_RESUMO:
            print(f"  (+{len(resto) - MAX_RESUMO}; --todas para listar)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
