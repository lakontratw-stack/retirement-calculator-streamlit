from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean


LABOR_INSURANCE_TIERS = [
    (1, 29_500),
    (2, 30_300),
    (3, 31_800),
    (4, 33_300),
    (5, 34_800),
    (6, 36_300),
    (7, 38_200),
    (8, 40_100),
    (9, 42_000),
    (10, 43_900),
    (11, 45_800),
]

MIN_LABOR_PENSION_WAGE = 29_500
MAX_LABOR_PENSION_WAGE = 150_000
MONTHS_PER_YEAR = 12
LABOR_PENSION_ANNUITY_RATE = 0.011473


@dataclass(frozen=True)
class PensionProjection:
    retirement_system: str
    total_work_years: float
    old_system_years: float
    new_system_years: float
    future_work_years: float
    avg_top_60_insured_salary: int
    labor_annuity_a: int
    labor_annuity_b: int
    monthly_labor_annuity: int
    labor_annuity_formula: str
    monthly_labor_annuity_adjusted: int
    old_system_bases: float
    estimated_old_system_lump_sum: int
    estimated_labor_pension_account: int
    estimated_monthly_labor_pension_drawdown: int
    labor_pension_annuity_factor: float
    total_monthly_retirement_cashflow: int
    projected_lifetime_labor_annuity: int
    projected_lifetime_total_cashflow: int
    rows: list[dict]


def round_half_up(value: int | float | Decimal) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def money(value: int | float) -> str:
    amount = int(round_half_up(value))
    return f"NT$ {amount:,}"


def get_insured_salary(monthly_salary: float) -> tuple[int, int]:
    if monthly_salary <= 0:
        raise ValueError("月薪必須大於 0")
    for tier, salary in LABOR_INSURANCE_TIERS:
        if monthly_salary <= salary:
            return tier, salary
    return LABOR_INSURANCE_TIERS[-1]


def closest_insured_salary(value: int) -> int:
    if value <= 0:
        raise ValueError("投保薪資必須大於 0")
    return min(LABOR_INSURANCE_TIERS, key=lambda tier: abs(tier[1] - value))[1]


def estimate_labor_pension_wage(monthly_salary: float) -> int:
    """簡化估算勞退月提繳工資：以月薪為基礎，上下限用 115 年級距範圍控制。"""
    return round_half_up(min(max(monthly_salary, MIN_LABOR_PENSION_WAGE), MAX_LABOR_PENSION_WAGE))


def value_between_known_points(start_value: int, current_value: int, elapsed_years: int, year_index: int) -> float:
    if elapsed_years <= 0:
        return current_value
    growth = (current_value / start_value) ** (1 / elapsed_years) - 1
    return start_value * ((1 + growth) ** year_index)


def salary_at_age(
    age: int,
    work_start_age: int,
    current_age: int,
    first_year_monthly_salary: int,
    current_monthly_salary: int,
    future_growth_rate: float,
) -> float:
    year_index = age - work_start_age
    elapsed_years = current_age - work_start_age
    if age < current_age:
        return value_between_known_points(first_year_monthly_salary, current_monthly_salary, elapsed_years, year_index)
    years_after_now = age - current_age
    return current_monthly_salary * ((1 + future_growth_rate) ** years_after_now)


def insured_salary_at_age(
    age: int,
    work_start_age: int,
    current_age: int,
    first_year_insured_salary: int,
    current_insured_salary: int,
    estimated_salary: float,
) -> tuple[int, int]:
    if age < current_age:
        year_index = age - work_start_age
        elapsed_years = current_age - work_start_age
        value = value_between_known_points(first_year_insured_salary, current_insured_salary, elapsed_years, year_index)
        rounded = closest_insured_salary(round_half_up(value))
        tier, _ = get_insured_salary(rounded)
        return tier, rounded
    return get_insured_salary(estimated_salary)


def round_old_service_years(years: float) -> float:
    whole_years = int(years)
    remainder = years - whole_years
    if remainder == 0:
        return float(whole_years)
    if remainder < 0.5:
        return whole_years + 0.5
    return float(whole_years + 1)


def calculate_old_system_bases(years: float) -> float:
    rounded_years = round_old_service_years(max(0, years))
    first_block = min(rounded_years, 15) * 2
    second_block = max(0, rounded_years - 15)
    return min(first_block + second_block, 45)


def annuity_due_factor(years: int, annual_rate: float = LABOR_PENSION_ANNUITY_RATE) -> float:
    if years <= 0:
        raise ValueError("請領年限必須大於 0")
    if annual_rate <= 0:
        return float(years)
    return ((1 - (1 + annual_rate) ** -years) / annual_rate) * (1 + annual_rate)


def build_projection(
    work_start_age: int,
    current_age: int,
    retirement_age: int,
    first_year_monthly_salary: int,
    first_year_insured_salary: int,
    current_monthly_salary: int,
    current_insured_salary: int,
    future_growth_rate: float,
    retirement_system: str,
    old_system_years: float,
    retirement_average_wage: int | None,
    estimate_past_labor_pension: bool,
    employer_contribution_rate: float,
    voluntary_contribution_rate: float,
    account_return_rate: float,
    existing_labor_pension_balance: int,
    claim_timing_years: int,
    life_expectancy_age: int,
    manual_avg_top_60_salary: int | None,
) -> PensionProjection:
    if work_start_age >= retirement_age:
        raise ValueError("退休年齡必須大於開始工作年齡")
    if current_age < work_start_age:
        raise ValueError("目前年齡不能小於開始工作年齡")
    if retirement_age < current_age:
        raise ValueError("退休年齡不能小於目前年齡")
    if life_expectancy_age <= retirement_age:
        raise ValueError("預估領取到幾歲必須大於退休年齡")
    if first_year_monthly_salary <= 0 or current_monthly_salary <= 0:
        raise ValueError("第一年月薪與目前月薪必須大於 0")
    if retirement_system not in {"新制", "舊制", "新舊制混合"}:
        raise ValueError("退休制度選項不正確")

    rows: list[dict] = []
    monthly_insured_salaries: list[int] = []
    balance = Decimal(existing_labor_pension_balance)
    monthly_return = Decimal(str(account_return_rate)) / Decimal("12")
    total_work_years = retirement_age - work_start_age
    old_years = 0.0
    if retirement_system == "舊制":
        old_years = float(total_work_years)
    elif retirement_system == "新舊制混合":
        old_years = min(float(old_system_years), float(total_work_years))
    new_years = max(0.0, float(total_work_years) - old_years)

    for age in range(work_start_age, retirement_age):
        year_index = age - work_start_age
        salary = salary_at_age(
            age=age,
            work_start_age=work_start_age,
            current_age=current_age,
            first_year_monthly_salary=first_year_monthly_salary,
            current_monthly_salary=current_monthly_salary,
            future_growth_rate=future_growth_rate,
        )
        tier, insured_salary = insured_salary_at_age(
            age=age,
            work_start_age=work_start_age,
            current_age=current_age,
            first_year_insured_salary=first_year_insured_salary,
            current_insured_salary=current_insured_salary,
            estimated_salary=salary,
        )
        pension_wage = estimate_labor_pension_wage(salary)
        is_new_system_year = retirement_system == "新制" or (
            retirement_system == "新舊制混合" and year_index >= old_years
        )
        include_labor_pension_contribution = is_new_system_year and (
            estimate_past_labor_pension or age >= current_age
        )
        contribution = 0
        if include_labor_pension_contribution:
            contribution = round_half_up(pension_wage * (employer_contribution_rate + voluntary_contribution_rate))

        for _ in range(MONTHS_PER_YEAR):
            monthly_insured_salaries.append(insured_salary)
            if include_labor_pension_contribution:
                balance = (balance + Decimal(contribution)) * (Decimal("1") + monthly_return)

        rows.append(
            {
                "年齡": age,
                "估計月薪": round_half_up(salary),
                "退休制度": "新制" if is_new_system_year else "舊制",
                "勞保級距": tier,
                "月投保薪資": insured_salary,
                "勞退月提繳工資估算": pension_wage,
                "每月勞退提繳": contribution,
                "年底勞退帳戶估算": round_half_up(balance),
            }
        )

    top_60 = sorted(monthly_insured_salaries, reverse=True)[:60]
    avg_top_60 = manual_avg_top_60_salary or round_half_up(mean(top_60))
    future_work_years = max(0, retirement_age - current_age)

    # 勞保局給付標準：A、B兩式擇優。
    annuity_a = round_half_up(avg_top_60 * total_work_years * 0.00775 + 3_000)
    annuity_b = round_half_up(avg_top_60 * total_work_years * 0.0155)
    monthly_annuity = max(annuity_a, annuity_b)
    better_formula = "A 式" if annuity_a >= annuity_b else "B 式"

    timing_adjustment = 1 + (claim_timing_years * 0.04)
    timing_adjustment = min(max(timing_adjustment, 0.8), 1.2)
    adjusted_annuity = round_half_up(monthly_annuity * timing_adjustment)

    old_bases = calculate_old_system_bases(old_years)
    # 舊制基數：以退休前連續5年（或不足5年則取全部）平均月薪估算
    last_n_years = rows[-5:] if len(rows) >= 5 else rows
    avg_final_wages = [r["估計月薪"] for r in last_n_years]
    final_average_wage = retirement_average_wage or round_half_up(mean(avg_final_wages))
    old_lump_sum = round_half_up(final_average_wage * old_bases)

    drawdown_months = (life_expectancy_age - retirement_age) * MONTHS_PER_YEAR
    account_total = round_half_up(balance)
    drawdown_years = life_expectancy_age - retirement_age
    pension_factor = annuity_due_factor(drawdown_years)
    monthly_drawdown = round_half_up(account_total / pension_factor / MONTHS_PER_YEAR)
    total_monthly_cashflow = adjusted_annuity + monthly_drawdown
    projected_lifetime_annuity = adjusted_annuity * drawdown_months
    projected_lifetime_total = projected_lifetime_annuity + account_total + old_lump_sum

    return PensionProjection(
        retirement_system=retirement_system,
        total_work_years=total_work_years,
        old_system_years=old_years,
        new_system_years=new_years,
        future_work_years=future_work_years,
        avg_top_60_insured_salary=avg_top_60,
        labor_annuity_a=annuity_a,
        labor_annuity_b=annuity_b,
        monthly_labor_annuity=monthly_annuity,
        labor_annuity_formula=better_formula,
        monthly_labor_annuity_adjusted=adjusted_annuity,
        old_system_bases=old_bases,
        estimated_old_system_lump_sum=old_lump_sum,
        estimated_labor_pension_account=account_total,
        estimated_monthly_labor_pension_drawdown=monthly_drawdown,
        labor_pension_annuity_factor=pension_factor,
        total_monthly_retirement_cashflow=total_monthly_cashflow,
        projected_lifetime_labor_annuity=projected_lifetime_annuity,
        projected_lifetime_total_cashflow=projected_lifetime_total,
        rows=rows,
    )
