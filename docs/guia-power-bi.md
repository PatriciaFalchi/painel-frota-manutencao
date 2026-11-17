# Painel de Frota no Power BI — guia de montagem

Dados **100% fictícios** (gerados por `gera_frota.py`, seed 2026): 54 veículos, 470 ordens de serviço, nov/2025 a out/2026.

## 1. Importar
Power BI Desktop > Obter dados > Texto/CSV, os 7 arquivos da pasta `dados/`.
Confira os tipos no Power Query: datas como **Data** (`data_abertura`, `data_conclusao`, `data`, `mes`, `data_vencimento`), custos e horas como **Número decimal**.

## 2. Modelo (aba Modelo)
Todas as relações são 1 para muitos, filtro em uma direção (da dimensão para o fato).

| Dimensão | Fato |
|---|---|
| dim_veiculo[id_veiculo] | fato_manutencao, fato_km_mensal, fato_abastecimento, fato_vencimento |
| dim_oficina[id_oficina] | fato_manutencao |
| dim_calendario[data] | fato_manutencao[data_abertura], fato_abastecimento[data], fato_km_mensal[mes] |

Marque `dim_calendario` como tabela de datas. `fato_km_mensal[mes]` é sempre o dia 1 do mês.

## 3. Medidas DAX
Crie uma tabela vazia `_Medidas` (Inserir dados) e coloque tudo nela.

```DAX
Veículos = COUNTROWS(dim_veiculo)

Horas Calendário = [Veículos] * COUNTROWS(dim_calendario) * 24

Horas Parada = SUM(fato_manutencao[horas_parada])

Disponibilidade % =
DIVIDE([Horas Calendário] - [Horas Parada], [Horas Calendário])

Corretivas =
CALCULATE(COUNTROWS(fato_manutencao), fato_manutencao[tipo_manutencao] = "Corretiva")

Preventivas =
CALCULATE(COUNTROWS(fato_manutencao), fato_manutencao[tipo_manutencao] = "Preventiva")

% Preventiva = DIVIDE([Preventivas], [Preventivas] + [Corretivas])

MTBF (h) =
DIVIDE([Horas Calendário] - [Horas Parada], [Corretivas])

MTTR (h) =
CALCULATE(AVERAGE(fato_manutencao[horas_parada]), fato_manutencao[tipo_manutencao] = "Corretiva")

Custo Manutenção =
SUMX(fato_manutencao, fato_manutencao[custo_pecas] + fato_manutencao[custo_mao_obra])

Custo Combustível = SUM(fato_abastecimento[valor])

Km Rodados = SUM(fato_km_mensal[km_rodados])

Custo por km =
DIVIDE([Custo Manutenção] + [Custo Combustível], [Km Rodados])

Manutenção por km = DIVIDE([Custo Manutenção], [Km Rodados])

Km por Litro = DIVIDE([Km Rodados], SUM(fato_abastecimento[litros]))
```

Coluna calculada em `fato_vencimento` (a base foi montada tendo 17/11/2026 como referência; se abrir em outra data, os dias mudam):

```DAX
Dias para Vencer = DATEDIFF(TODAY(), fato_vencimento[data_vencimento], DAY)
```

```DAX
Docs Vencidos =
CALCULATE(COUNTROWS(fato_vencimento), fato_vencimento[Dias para Vencer] < 0)

Docs a Vencer 30d =
CALCULATE(COUNTROWS(fato_vencimento),
    fato_vencimento[Dias para Vencer] >= 0, fato_vencimento[Dias para Vencer] <= 30)
```

## 4. Conferência (sem filtros, os totais devem bater)
- 54 veículos, 470 OS, 1.368.015 km
- Disponibilidade 95,94% · MTBF 1.240 h · MTTR 49,8 h
- Custo de manutenção R$ 817.501,55 · combustível R$ 1.460.638,10 · custo por km ≈ R$ 1,67
- Preventivas 22,1% das OS

## 5. Páginas sugeridas
1. **Visão geral:** cartões (Disponibilidade, MTBF, MTTR, Custo por km, % Preventiva), linha de Disponibilidade por mês, colunas empilhadas Preventivas x Corretivas por mês, segmentação por tipo de veículo.
2. **Custos e recorrência:** barras de corretivas por `sistema`, tabela dos veículos por Custo Manutenção (com Custo por km e idade), matriz veículo x sistema para achar falhas repetidas.
3. **Vencimentos e oficinas:** cartões de Docs Vencidos e a Vencer 30d, tabela de documentos ordenada por Dias para Vencer, tabela de oficinas (OS, custo médio por OS, MTTR).

## 6. Conclusões
- 78% das manutenções são corretivas: a frota é reativa.
- 4 veículos antigos (2013 e 2014) concentram cerca de 25% do custo de manutenção: candidatos a renovação ou descarte.
- Motor e transmissão pesam no custo e na parada (MTTR alto): vale negociar prazo com a oficina diesel.
- Há documentos já vencidos: risco de multa e de seguro sem cobertura.
