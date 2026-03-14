from src.evals.pdf_signals import extract_academy_signals, extract_meal_signals, extract_pl_signals


def test_extract_pl_signals_parses_million_yen_series() -> None:
    text = """
    想定シナリオ FY26 FY27 FY28 FY29 FY30
    ①1 B2B 売上 58.1 551.7 1688.9 2697.1 5345.9
    売上原価 31.1 310.9 790.9 1251.8 2179.7
    粗利 56.8 240.8 898.0 1445.3 3166.2
    販売費及び一般管理費 371.1 524.7 650.6 1132.5 1847.1
    """

    result = extract_pl_signals(text)

    assert result["売上"] == [58_100_000.0, 551_700_000.0, 1_688_900_000.0, 2_697_100_000.0, 5_345_900_000.0]
    assert result["粗利"] == [56_800_000.0, 240_800_000.0, 898_000_000.0, 1_445_300_000.0, 3_166_200_000.0]
    assert result["事業運営費（OPEX）"] == [371_100_000.0, 524_700_000.0, 650_600_000.0, 1_132_500_000.0, 1_847_100_000.0]


def test_extract_academy_signals_parses_price_student_and_revenue_series() -> None:
    text = """
    受講単価はランクに応じて、C級7万円、B級10万円、A級30万円を想定。
    FY26:55、FY27:161、FY28：307、FY29：436、FY30：677を獲得。
    3 アカデミー 4.4 12.9 24.6 34.9 54.1
    """

    result = extract_academy_signals(text)

    assert result["academy_price"] == [70_000.0, 70_000.0, 70_000.0, 70_000.0, 70_000.0]
    assert result["academy_students"] == [55.0, 161.0, 307.0, 436.0, 677.0]
    assert result["academy_revenue"] == [4_400_000.0, 12_900_000.0, 24_600_000.0, 34_900_000.0, 54_100_000.0]


def test_extract_meal_signals_derives_unit_economics_from_meal_offer() -> None:
    text = """
    1. B2B（栄養コンサル＋ミールサービス）
    年間契約にて、1,500円/食×15食/人×20人/月を想定。
    """

    result = extract_meal_signals(text)

    assert result["price_per_item"] == [500.0, 500.0, 500.0, 500.0, 500.0]
    assert result["items_per_meal"] == [3.0, 3.0, 3.0, 3.0, 3.0]
    assert result["meals_per_year"] == [3600.0, 3600.0, 3600.0, 3600.0, 3600.0]
