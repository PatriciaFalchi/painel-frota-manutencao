import sys, json
import pandas as pd
d = sys.argv[1]
v = pd.read_csv(f"{d}/dim_veiculo.csv"); m = pd.read_csv(f"{d}/fato_manutencao.csv", parse_dates=["data_abertura"])
km = pd.read_csv(f"{d}/fato_km_mensal.csv", parse_dates=["mes"]); ab = pd.read_csv(f"{d}/fato_abastecimento.csv", parse_dates=["data"])
ve = pd.read_csv(f"{d}/fato_vencimento.csv", parse_dates=["data_vencimento"]); of = pd.read_csv(f"{d}/dim_oficina.csv")
m["custo"] = m.custo_pecas + m.custo_mao_obra
m["ym"] = m.data_abertura.dt.strftime("%Y-%m")
km["ym"] = km.mes.dt.strftime("%Y-%m"); ab["ym"] = ab.data.dt.strftime("%Y-%m")
dias_mes = {ym: pd.Period(ym).days_in_month for ym in sorted(km.ym.unique())}
nveic = len(v)
H = {ym: nveic * dias_mes[ym] * 24 for ym in dias_mes}
tot_h = sum(H.values())
corr = m[m.tipo_manutencao == "Corretiva"]
res = {}
res["frota"] = nveic
res["os_total"] = len(m)
res["disp_pct"] = round(100 * (1 - m.horas_parada.sum() / tot_h), 2)
res["mtbf_h"] = round((tot_h - m.horas_parada.sum()) / len(corr), 1)
res["mttr_h"] = round(corr.horas_parada.mean(), 1)
res["km_total"] = int(km.km_rodados.sum())
res["custo_manut"] = round(m.custo.sum(), 2); res["custo_comb"] = round(ab.valor.sum(), 2)
res["custo_km"] = round((res["custo_manut"] + res["custo_comb"]) / res["km_total"], 3)
res["manut_km"] = round(res["custo_manut"] / res["km_total"], 3)
res["prev_pct"] = round(100 * (m.tipo_manutencao == "Preventiva").mean(), 1)
res["corr_pct"] = round(100 - res["prev_pct"], 1)
res["km_l"] = round(km.km_rodados.sum() / ab.litros.sum(), 2)
# mensal
mm = pd.DataFrame({"ym": sorted(dias_mes)})
mm["horas"] = mm.ym.map(H)
g = m.groupby("ym").horas_parada.sum(); mm["parada"] = mm.ym.map(g).fillna(0)
mm["disp"] = (100 * (1 - mm.parada / mm.horas)).round(2)
c = corr.groupby("ym").agg(n=("id_os", "count"), mttr=("horas_parada", "mean")); mm["n_corr"] = mm.ym.map(c.n).fillna(0).astype(int)
mm["mttr"] = mm.ym.map(c.mttr).round(1)
mm["mtbf"] = ((mm.horas - mm.parada) / mm.n_corr.replace(0, float("nan"))).round(0)
mm["custo_manut"] = mm.ym.map(m.groupby("ym").custo.sum()).round(0)
mm["custo_comb"] = mm.ym.map(ab.groupby("ym").valor.sum()).round(0)
mm["km"] = mm.ym.map(km.groupby("ym").km_rodados.sum())
mm["custo_km"] = ((mm.custo_manut + mm.custo_comb) / mm.km).round(3)
pv = m.groupby(["ym", "tipo_manutencao"]).size().unstack(fill_value=0)
mm["prev"] = mm.ym.map(pv.get("Preventiva")).fillna(0).astype(int); mm["corr"] = mm.ym.map(pv.get("Corretiva")).fillna(0).astype(int)
res["mensal"] = mm.fillna(0).to_dict("records")
# por tipo de veículo
mv = m.merge(v[["id_veiculo", "tipo", "placa", "modelo", "ano_fabricacao"]], on="id_veiculo")
kv = km.merge(v[["id_veiculo", "tipo"]], on="id_veiculo").groupby("tipo").km_rodados.sum()
t = mv.groupby("tipo").agg(os=("id_os", "count"), custo=("custo", "sum"), parada=("horas_parada", "sum"))
t["n_veic"] = v.groupby("tipo").size(); t["km"] = kv
t["disp"] = (100 * (1 - t.parada / (t.n_veic * 365 * 24))).round(2); t["custo_manut_km"] = (t.custo / t.km).round(3)
res["por_tipo"] = t.reset_index().round(2).to_dict("records")
# top veículos por custo
tv = mv.groupby(["id_veiculo", "placa", "tipo", "modelo", "ano_fabricacao"]).agg(custo=("custo", "sum"), os=("id_os", "count"),
                                                                                   corr=("tipo_manutencao", lambda s: (s == "Corretiva").sum()),
                                                                                   parada=("horas_parada", "sum")).reset_index()
tv = tv.merge(km.groupby("id_veiculo").km_rodados.sum().rename("km"), on="id_veiculo")
tv["custo_km"] = (tv.custo / tv.km).round(3)
res["top_custo"] = tv.sort_values("custo", ascending=False).head(8).round(1).to_dict("records")
res["media_custo_veic"] = round(tv.custo.mean(), 0)
# recorrência de falhas: sistema por veículo (>=3 corretivas mesmo sistema)
rec = corr.groupby(["id_veiculo", "sistema"]).size().reset_index(name="n")
rec = rec[rec.n >= 3].merge(v[["id_veiculo", "placa", "tipo", "ano_fabricacao"]], on="id_veiculo").sort_values("n", ascending=False)
res["recorrencia"] = rec.head(8).to_dict("records"); res["n_recorrentes"] = int(len(rec))
res["sistemas"] = corr.groupby("sistema").agg(n=("id_os", "count"), custo=("custo", "sum"), mttr=("horas_parada", "mean")).reset_index().round(1).sort_values("n", ascending=False).to_dict("records")
# oficinas
mo = m.merge(of, on="id_oficina").groupby("oficina").agg(os=("id_os", "count"), custo=("custo", "sum"), mttr=("horas_parada", "mean")).reset_index().round(1)
mo["custo_medio_os"] = (mo.custo / mo.os).round(0); res["oficinas"] = mo.sort_values("custo", ascending=False).to_dict("records")
# vencimentos
hoje = pd.Timestamp("2026-11-17"); ve["dias"] = (ve.data_vencimento - hoje).dt.days
res["venc_vencidos"] = int((ve.dias < 0).sum()); res["venc_30"] = int(((ve.dias >= 0) & (ve.dias <= 30)).sum()); res["venc_60"] = int(((ve.dias > 30) & (ve.dias <= 60)).sum())
vv = ve[ve.dias <= 30].merge(v[["id_veiculo", "placa", "tipo"]], on="id_veiculo").sort_values("dias").head(8)
vv["data_vencimento"] = vv.data_vencimento.dt.strftime("%d/%m/%Y"); res["venc_lista"] = vv[["placa", "tipo", "documento", "data_vencimento", "dias"]].to_dict("records")
# idade
res["idade_media"] = round(2026 - v.ano_fabricacao.mean(), 1)
json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=1, default=float)
for k in ["frota", "os_total", "disp_pct", "mtbf_h", "mttr_h", "km_total", "custo_manut", "custo_comb", "custo_km", "manut_km", "prev_pct", "corr_pct", "km_l", "venc_vencidos", "venc_30", "venc_60", "n_recorrentes", "idade_media", "media_custo_veic"]:
    print(k, res[k])
