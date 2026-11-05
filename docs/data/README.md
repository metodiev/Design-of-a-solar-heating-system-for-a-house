# Изходни данни и изчислителни модели

Тази папка съдържа данните, с които са получени всички числа в проекта.
Те са свалени от **PVGIS v5.3** (European Commission, JRC) на 05.11.2026 г.

| Файл | Съдържание |
|---|---|
| `pvgis_mr.json` | месечна хоризонтална радиация, 2005–2020, 42,545° N / 22,962° E |
| `series55.json` | почасова серия 2018–2020 за равнина 55° / юг: Gb(i), Gd(i), Gr(i), T2m |
| `pv_90.json` | месечна радиация на вертикална южна стена (за прозоречните печалби) |
| `model_results.json` | резултати от `tools/system_model.py` за всички варианти (вкл. часове на стагнация и суха температура) |
| `power_daily.json` | дневна слънчева радиация на хоризонтала и при ясно небе, **NASA POWER / MERRA-2**, 2005–2026 – за слънчевите дни |

## Как се възпроизвеждат резултатите

```bash
python3 tools/system_model.py   # почасов модел -> docs/data/model_results.json
python3 tools/make_tables.py    # markdown таблици за документа
python3 tools/economics.py      # количествена сметка и икономика
python3 tools/tube_variant.py   # вакуумно-тръбен вариант: енергия, LCOE, стагнация
python3 tools/sunny_days.py     # слънчеви дни по месеци и години (таблици за README)
python3 tools/make_images.py    # всички SVG схеми и визуализации
```

## Данни за слънчевите дни (NASA POWER)

```bash
curl "https://power.larc.nasa.gov/api/temporal/daily/point?\
parameters=ALLSKY_SFC_SW_DWN,CLRSKY_SFC_SW_DWN&community=RE&\
longitude=22.962&latitude=42.545&start=20050101&end=20261101&format=JSON"
```

## Проверка на данните с PVGIS API

```bash
curl "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc?lat=42.545&lon=22.962\
&peakpower=1&loss=14&angle=55&aspect=0&outputformat=json"
```

## Ограничения на модела

- едновъзлов буфер с фиксирана стратификация (±8 K);
- топлообменникът е моделиран с коефициент 0,92;
- профилът на БГВ е типов, не измерен;
- пелетният уред е моделиран като източник с мощност до 15 kW;
- резултатите са с точност ±10 % – достатъчна за концепция, недостатъчна за
  гарантиране на добив.
