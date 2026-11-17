"""Gera base FICTÍCIA de frota (seed fixa) para o projeto de portfólio.
Uso: python3 -I gera_frota.py <pasta_saida>
Todos os dados são sintéticos."""
import sys, os, random
from datetime import date, timedelta
import csv

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(2026)

INI, FIM = date(2025, 11, 1), date(2026, 10, 31)  # 12 meses
DIAS = (FIM - INI).days + 1

# ---------- dim_veiculo ----------
tipos = [
    ("Utilitário leve", "Fiat Fiorino", 14, 0.18, 24),
    ("Van", "Renault Master", 9, 0.28, 22),
    ("Caminhonete", "Toyota Hilux", 10, 0.30, 26),
    ("Caminhão leve", "VW Delivery", 7, 0.45, 28),
    ("Ônibus de apoio", "Mercedes OF-1519", 6, 0.55, 30),
    ("Carro de passeio", "Chevrolet Onix", 8, 0.12, 20),
]
veic = []
n = 1
for tipo, modelo, qtd, base_custo, anos_max in tipos:
    for _ in range(qtd):
        ano = random.randint(2012, 2024)
        veic.append(dict(
            id_veiculo=f"V{n:03d}", placa=f"{random.choice('ABCDEFGHJKLMNPRSTUVXZ')}{random.choice('ABCDEFGHJKLMNPRSTUVXZ')}{random.choice('ABCDEFGHJKLMNPRSTUVXZ')}{random.randint(1,9)}{random.choice('ABCDEFGHJ')}{random.randint(10,99)}",
            tipo=tipo, modelo=modelo, ano_fabricacao=ano,
            area=random.choice(["Manutenção de via", "Estações", "Logística", "Administrativo", "Segurança"]),
            combustivel=random.choice(["Diesel", "Diesel"]) if tipo in ("Caminhão leve", "Ônibus de apoio", "Van") else random.choice(["Flex", "Flex", "Diesel"]) if tipo == "Caminhonete" else "Flex",
            km_inicial=random.randint(15000, 220000) + (2025 - ano) * 6000,
            fator_desgaste=round(1 + (2025 - ano) * 0.07 + random.uniform(-0.15, 0.25), 2),
            km_dia=base_custo,  # só auxiliar
        ))
        n += 1
# 4 "limões" com muitas falhas
limoes = random.sample([v["id_veiculo"] for v in veic if v["ano_fabricacao"] <= 2017], 4)
for v in veic:
    if v["id_veiculo"] in limoes:
        v["fator_desgaste"] = round(v["fator_desgaste"] * 2.4, 2)

# ---------- dim_oficina ----------
oficinas = [
    ("OF01", "Auto Center Tietê", "Mecânica geral", 1.00),
    ("OF02", "Diesel Norte Serviços", "Diesel/pesados", 0.95),
    ("OF03", "Concessionária Zona Norte", "Concessionária", 1.35),
    ("OF04", "Elétrica Santana", "Elétrica", 0.90),
    ("OF05", "Pneus & Freios Armênia", "Pneus/freios", 0.85),
    ("OF06", "Funilaria Paulistana", "Funilaria", 1.10),
]
with open(f"{out}/dim_oficina.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id_oficina", "oficina", "especialidade"])
    for o in oficinas: w.writerow(o[:3])

# ---------- fato_manutencao ----------
sistemas_corr = [("Motor", 0.20, 2800, 60), ("Freios", 0.18, 900, 24), ("Suspensão", 0.14, 1100, 30),
                 ("Elétrica", 0.16, 650, 20), ("Pneus", 0.12, 1500, 14), ("Transmissão", 0.08, 4200, 90),
                 ("Arrefecimento", 0.07, 750, 22), ("Funilaria", 0.05, 1800, 70)]
manut = []
os_id = 1
km_atual = {v["id_veiculo"]: v["km_inicial"] for v in veic}
km_mes = []  # fato_km
ultima_prev_km = {v["id_veiculo"]: v["km_inicial"] - random.randint(0, 9000) for v in veic}

def add_os(v, d, tipo_m, sistema, horas_parada, c_peca, c_mo, of):
    global os_id
    manut.append(dict(
        id_os=f"OS{os_id:05d}", id_veiculo=v["id_veiculo"], id_oficina=of[0],
        data_abertura=d.isoformat(), data_conclusao=(d + timedelta(hours=horas_parada)).date().isoformat() if False else (d + timedelta(days=max(0, int(horas_parada // 24)))).isoformat(),
        tipo_manutencao=tipo_m, sistema=sistema, horas_parada=round(horas_parada, 1),
        custo_pecas=round(c_peca, 2), custo_mao_obra=round(c_mo, 2),
        km_na_os=round(km_atual[v["id_veiculo"]])))
    os_id += 1

for v in veic:
    vid = v["id_veiculo"]
    ritmo = {"Utilitário leve": 70, "Van": 85, "Caminhonete": 80, "Caminhão leve": 95, "Ônibus de apoio": 110, "Carro de passeio": 45}[v["tipo"]]
    ritmo = ritmo * random.uniform(0.8, 1.2)  # km/dia
    intervalo_prev = 10000 if v["combustivel"] != "Diesel" else 15000
    mes_ref = None
    km_mes_acum = 0
    d = INI
    prox_corr = d + timedelta(days=int(random.expovariate(1 / (95 / v["fator_desgaste"]))))
    while d <= FIM:
        km_dia = max(0, random.gauss(ritmo, ritmo * 0.35)) if d.weekday() < 6 else max(0, random.gauss(ritmo * 0.25, 8))
        km_atual[vid] += km_dia
        km_mes_acum += km_dia
        # preventiva por km
        if km_atual[vid] - ultima_prev_km[vid] >= intervalo_prev:
            of = random.choice([o for o in oficinas if o[2] in ("Mecânica geral", "Diesel/pesados", "Concessionária")])
            h = random.uniform(5, 14)
            add_os(v, d, "Preventiva", random.choice(["Revisão periódica", "Troca de óleo e filtros", "Revisão periódica"]),
                   h, random.uniform(350, 900) * of[3], random.uniform(180, 420) * of[3], of)
            ultima_prev_km[vid] = km_atual[vid]
        # corretiva
        if d >= prox_corr:
            sis = random.choices(sistemas_corr, weights=[s[1] for s in sistemas_corr])[0]
            esp = {"Motor": "Diesel/pesados", "Freios": "Pneus/freios", "Suspensão": "Mecânica geral", "Elétrica": "Elétrica",
                   "Pneus": "Pneus/freios", "Transmissão": random.choice(["Concessionária", "Diesel/pesados"]),
                   "Arrefecimento": "Mecânica geral", "Funilaria": "Funilaria"}[sis[0]]
            of = random.choice([o for o in oficinas if o[2] == esp])
            horas = random.lognormvariate(0, 0.55) * sis[3] * (0.9 + 0.1 * v["fator_desgaste"])
            custo_p = random.lognormvariate(0, 0.45) * sis[2] * 0.70 * of[3] * (0.85 + 0.15 * v["fator_desgaste"])
            custo_m = custo_p * random.uniform(0.25, 0.5)
            add_os(v, d, "Corretiva", sis[0], horas, custo_p, custo_m, of)
            prox_corr = d + timedelta(days=int(max(5, random.expovariate(1 / (95 / v["fator_desgaste"])))) + int(horas // 24))
        # fecha mês
        if (d + timedelta(days=1)).month != d.month or d == FIM:
            km_mes.append(dict(id_veiculo=vid, mes=d.replace(day=1).isoformat(), km_rodados=round(km_mes_acum)))
            km_mes_acum = 0
        d += timedelta(days=1)

# ---------- fato_abastecimento ----------
abast = []
cons_base = {"Utilitário leve": 11.5, "Van": 8.0, "Caminhonete": 8.5, "Caminhão leve": 5.5, "Ônibus de apoio": 3.2, "Carro de passeio": 12.5}
preco = {"Diesel": 6.15, "Flex": 5.89}
kmmap = {(r["id_veiculo"], r["mes"]): r["km_rodados"] for r in km_mes}
for v in veic:
    cons_v = cons_base[v["tipo"]] * random.uniform(0.9, 1.08) / (1 + (v["fator_desgaste"] - 1) * 0.12)
    for m in range(12):
        ano = INI.year + (INI.month - 1 + m) // 12
        mes = (INI.month - 1 + m) % 12 + 1
        mes_d = date(ano, mes, 1)
        km = kmmap[(v["id_veiculo"], mes_d.isoformat())]
        litros_tot = km / cons_v
        n_ab = max(1, int(litros_tot / 40))
        for i in range(n_ab):
            dia = mes_d + timedelta(days=random.randint(0, 26))
            lit = litros_tot / n_ab
            p = preco[v["combustivel"]] * (1 + 0.0045 * m) * random.uniform(0.97, 1.04)
            abast.append(dict(id_veiculo=v["id_veiculo"], data=dia.isoformat(), litros=round(lit, 1),
                              valor=round(lit * p, 2), combustivel=v["combustivel"]))

# ---------- fato_vencimento ----------
HOJE = date(2026, 11, 17)
venc = []
for v in veic:
    for item, dias_ciclo in [("Licenciamento", 365), ("Seguro", 365), ("Inspeção veicular", 365)]:
        # distribui vencimentos: alguns vencidos, alguns próximos
        delta = int(random.choice([-12, -3, 8, 15, 22, 28, 45, 60, 90, 130, 200, 250, 300, 340]) + random.randint(-4, 4))
        venc.append(dict(id_veiculo=v["id_veiculo"], documento=item, data_vencimento=(HOJE + timedelta(days=delta)).isoformat()))

# ---------- dim_calendario ----------
meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
with open(f"{out}/dim_calendario.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["data", "ano", "mes_num", "mes_nome", "ano_mes"])
    d = INI
    while d <= FIM:
        w.writerow([d.isoformat(), d.year, d.month, meses[d.month - 1], f"{d.year}-{d.month:02d}"]); d += timedelta(days=1)

def dump(nome, rows, campos):
    with open(f"{out}/{nome}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos); w.writeheader()
        for r in rows: w.writerow({k: r[k] for k in campos})

dump("dim_veiculo", veic, ["id_veiculo", "placa", "tipo", "modelo", "ano_fabricacao", "area", "combustivel", "km_inicial"])
dump("fato_manutencao", manut, ["id_os", "id_veiculo", "id_oficina", "data_abertura", "data_conclusao", "tipo_manutencao", "sistema", "horas_parada", "custo_pecas", "custo_mao_obra", "km_na_os"])
dump("fato_km_mensal", km_mes, ["id_veiculo", "mes", "km_rodados"])
dump("fato_abastecimento", abast, ["id_veiculo", "data", "litros", "valor", "combustivel"])
dump("fato_vencimento", venc, ["id_veiculo", "documento", "data_vencimento"])
print("ok", len(veic), "veículos;", len(manut), "OS;", len(abast), "abastecimentos;", len(venc), "vencimentos")
