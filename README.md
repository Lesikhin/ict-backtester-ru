# ICT-Backtester-RU

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/Code%20Style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)
[![MOEX ISS](https://img.shields.io/badge/Data-MOEX%20ISS-0073D1?style=for-the-badge)](https://www.moex.com/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=for-the-badge&logo=pandas)](https://pandas.pydata.org/)
[![Plotly](https://img.shields.io/badge/Plotly-5.18+-3F4F75?style=for-the-badge&logo=plotly)](https://plotly.com/)

Алгоритмический бэктестер ICT-стратегий (Inner Circle Trader / Smart Money Concepts) для российского фондового рынка. Автоматическая детекция паттернов, кластеризация уровней ликвидности и историческое тестирование торговых гипотез.

---

## О проекте

Фреймворк реализует полный цикл количественного исследования: от загрузки рыночных данных через официальный API Московской биржи до визуализации результатов бэктеста в интерактивном HTML. Архитектура построена по принципам SOLID с чётким разделением ответственности между слоями данных, аналитики, стратегий и визуализации.

### Ключевые возможности

- Загрузка исторических данных через MOEX ISS API с автоматической пагинацией
- Детекция ICT-паттернов: Swing High/Low, Fair Value Gap (FVG), Market Structure Shift (MSS), Liquidity Sweep
- Кластеризация уровней поддержки/сопротивления с помощью DBSCAN
- Три торговые стратегии: Sweep+MSS+FVG, Power of 3 (AMD), Market Maker Model (MMXM)
- Бэктест-движок с учётом комиссий, проскальзывания и специфики фьючерсов MOEX
- Интерактивная визуализация на базе Plotly с разметкой паттернов и точек входа

---

## Стек технологий

| Библиотека     | Версия    | Назначение                                    |
|----------------|-----------|-----------------------------------------------|
| `pandas`       | >= 2.0.0  | Обработка временных рядов и финансовых данных |
| `numpy`        | >= 1.24.0 | Математические вычисления и векторизация      |
| `requests`     | >= 2.31.0 | HTTP-клиент для работы с MOEX ISS API         |
| `scikit-learn` | >= 1.3.0  | Кластеризация уровней ликвидности (DBSCAN)    |
| `plotly`       | >= 5.18.0 | Интерактивная визуализация результатов        |
| `pyyaml`       | >= 6.0    | Конфигурация проекта                          |
| `pyarrow`      | >= 14.0.0 | Кэширование данных в формате Parquet          |
| `pytest`       | >= 7.4.0  | Юнит-тестирование детекторов                  |

---

## Результаты тестирования

Стратегия **Sweep+MSS+FVG (Scaled)** протестирована на фьючерсе IMOEXF за 1 год (4908 часовых свечей). Внедрение фильтра зон проторговки и частичной фиксации прибыли (Scaling Out) позволило оптимизировать профиль риска.

| Метрика          | Базовая стратегия | Scaled + Фильтр | Улучшение                         |
|------------------|-------------------|-----------------|-----------------------------------|
| Всего сделок     | 299               | **168**         | Отсеяно 44% шумовых входов        |
| Win Rate         | 45.8%             | 44.6%           | Стабильность качества сигналов    |
| Profit Factor    | 1.50              | **1.50**        | Мат. ожидание сохранено           |
| Total Return     | +12.23%           | +4.93%          | Консервативный рост               |
| **Max Drawdown** | 2.48%             | **1.15%**       | Снижение риска в 2.1 раза**       |
| Expectancy       | 409 руб.          | 293 руб.        | Стабильная прибыль на сделку      |

**Вывод:** Внедрение фильтра консолидации и частичного выхода (50% на TP1, 50% на TP2) не снизило Profit Factor, но **сократило максимальную просадку более чем в два раза**, сделав кривую капитала значительно более устойчивой к рыночному шуму.



---

## Установка

```bash
# Клонирование репозитория
git clone https://github.com/your-username/ict-backtester-ru.git
cd ict-backtester-ru

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / macOS

# Установка зависимостей
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## Использование

### Базовый запуск (с настройками из `configs/config.yaml`)

```bash
python main.py
```

### Запуск с параметрами

```bash
python main.py --ticker SBER --interval 1h --days 365 --strategy sweep_mss
```

### Параметры командной строки

| Параметр     | Описание               | Примеры                           |
|--------------|------------------------|-----------------------------------|
| `--config`   | Путь к конфигу         | `configs/config.yaml`             |
| `--ticker`   | Тикер инструмента      | `IMOEXF`, `SBER`, `LKOH`          |
| `--interval` | Таймфрейм              | `1min`, `10min`, `1h`, `1d`       |
| `--days`     | Глубина истории в днях | `365`                             |
| `--strategy` | Название стратегии     | `sweep_mss`, `power_of_3`, `mmxm` |

### Поддерживаемые тикеры

**Фьючерсы (FORTS):**
- `IMOEXF` — Индекс МосБиржи
- `RIMIXF` — Индекс РТС
- `SBERF` — Сбербанк
- `BRF5`, `SiH5`, `EDF5` — сырьевые и валютные фьючерсы

**Акции (TQBR):**
- `SBER`, `GAZP`, `LKOH`, `VTBR`, `YAND`, `MGNT`, `ROSN`

**Индексы:**
- `IMOEX`, `RTSI`

---

## ICT-паттерны

### Swing High / Swing Low
Локальные экстремумы, подтверждаемые определённым количеством свечей слева и справа. Используются как точки отсчёта для определения структуры рынка.

### Fair Value Gap (FVG)
Ценовой дисбаланс между тенью первой и третьей свечи. Служит зоной интереса (POI) для входа в позицию.

### Market Structure Shift (MSS / BOS)
Слом рыночной структуры при пробое значимого свинга. Сигнализирует о смене направления движения.

### Liquidity Sweep
Снятие ликвидности — пробой уровня тенью с возвратом тела свечи. Классическая манипуляция Smart Money для сбора стоп-лоссов розничных трейдеров.

---

## Метрики бэктеста

- **Total Return** — общая доходность стратегии
- **Win Rate** — процент прибыльных сделок
- **Profit Factor** — отношение валовой прибыли к валовому убытку
- **Max Drawdown** — максимальная просадка капитала от пика
- **Sharpe Ratio** — коэффициент Шарпа (доходность с поправкой на риск)
- **Expectancy** — математическое ожидание на одну сделку

---

## Структура проекта

```
ict-backtester-ru/
├── configs/              # Конфигурация (YAML)
├── src/
│   ├── data/            # Провайдеры данных и модели
│   │   ├── models.py    # Dataclass-модели (OHLCV, SwingPoint, FVG, Trade)
│   │   └── provider.py  # MOEX ISS API клиент с пагинацией
│   ├── analysis/        # Детекторы паттернов
│   │   ├── detectors.py # Swing, FVG, MSS, Sweep
│   │   └── levels.py    # Кластеризация уровней (DBSCAN)
│   ├── strategies/      # Торговые стратегии
│   │   ├── base.py      # Абстрактный базовый класс
│   │   ├── sweep_mss.py # Sweep + MSS + FVG
│   │   ├── power_of_3.py# Power of 3 (AMD)
│   │   └── mmxm.py      # Market Maker Model
│   ├── backtest/        # Бэктест-движок
│   │   ├── engine.py    # Симуляция торговли
│   │   └── metrics.py   # Расчёт метрик
│   └── visualization/   # Визуализация
│       └── chart.py     # Plotly-рендерер
├── tests/               # Юнит-тесты (pytest)
├── data/                # Кэш данных (Parquet)
├── main.py              # Точка входа
├── requirements.txt     # Зависимости
└── pyproject.toml       # Конфигурация инструментов
```

---

## Тестирование

```bash
# Запуск всех тестов
pytest

# С отчётом о покрытии
pytest --cov=src --cov-report=html
```

---

## Лицензия

MIT License. См. файл `LICENSE` для подробностей.

---

## Автор

Проект создан для демонстрации компетенций в областях:
- Алгоритмическая торговля и количественный анализ
- Python-разработка (dataclasses, ABC, SOLID)
- Работа с финансовыми API и временными рядами
- Машинное обучение (кластеризация DBSCAN)
- Интерактивная визуализация данных