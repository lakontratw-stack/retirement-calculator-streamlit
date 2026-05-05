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


@dataclass(frozen=True)
class PensionProjection:
    total_work_years: float
    future_work_years: float
    avg_top_60_insured_salary: int
    labor_annuity_a: int
    labor_annuity_b: int
    monthly_labor_annuity: int
    labor_annuity_formula: str
    monthly_labor_annuity_adjusted: int
    estimated_labor_pension_account: int
    estimated_monthly_labor_pension_drawdown: int
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


def estimate_labor_pension_wage(monthly_salary: float) -> int:
    """簡化估算勞退月提繳工資：以月薪為基礎，上下限用 115 年級距範圍控制。"""
    return round_half_up(min(max(monthly_salary, MIN_LABOR_PENSION_WAGE), MAX_LABOR_PENSION_WAGE))


def salary_at_age(
    age: int,
    current_age: int,
    current_monthly_salary: int,
    past_growth_rate: float,
    future_growth_rate: float,
) -> float:
    if age < current_age:
        years_before_now = current_age - age
        return current_monthly_salary / ((1 + past_growth_rate) ** years_before_now)
    years_after_now = age - current_age
    return current_monthly_salary * ((1 + future_growth_rate) ** years_after_now)


def build_projection(
    work_start_age: int,
    current_age: int,
    retirement_age: int,
    current_monthly_salary: int,
    past_growth_rate: float,
    future_growth_rate: float,
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

    rows: list[dict] = []
    monthly_insured_salaries: list[int] = []
    balance = Decimal(existing_labor_pension_balance)
    monthly_return = Decimal(str(account_return_rate)) / Decimal("12")

    for age in range(work_start_age, retirement_age):
        salary = salary_at_age(
            age=age,
            current_age=current_age,
            current_monthly_salary=current_monthly_salary,
            past_growth_rate=past_growth_rate,
            future_growth_rate=future_growth_rate,
        )
        tier, insured_salary = get_insured_salary(salary)
        pension_wage = estimate_labor_pension_wage(salary)
        contribution = round_half_up(pension_wage * (employer_contribution_rate + voluntary_contribution_rate))

        for _ in range(MONTHS_PER_YEAR):
            monthly_insured_salaries.append(insured_salary)
            balance = (balance + Decimal(contribution)) * (Decimal("1") + monthly_return)

        rows.append(
            {
                "年齡": age,
                "估計月薪": round_half_up(salary),
                "勞保級距": tier,
                "月投保薪資": insured_salary,
                "勞退月提繳工資估算": pension_wage,
                "每月勞退提繳": contribution,
                "年底勞退帳戶估算": round_half_up(balance),
            }
        )

    top_60 = sorted(monthly_insured_salaries, reverse=True)[:60]
    avg_top_60 = manual_avg_top_60_salary or round_half_up(mean(top_60))
    total_work_years = len(monthly_insured_salaries) / MONTHS_PER_YEAR
    future_work_years = max(0, retirement_age - current_age)

    annuity_a = round_half_up(avg_top_60 * total_work_years * 0.00775 + 3_000)
    annuity_b = round_half_up(avg_top_60 * total_work_years * 0.0155)
    monthly_annuity = max(annuity_a, annuity_b)
    better_formula = "A 式" if annuity_a >= annuity_b else "B 式"

    timing_adjustment = 1 + (claim_timing_years * 0.04)
    timing_adjustment = min(max(timing_adjustment, 0.8), 1.2)
    adjusted_annuity = round_half_up(monthly_annuity * timing_adjustment)

    drawdown_months = (life_expectancy_age - retirement_age) * MONTHS_PER_YEAR
    account_total = round_half_up(balance)
    monthly_drawdown = round_half_up(account_total / drawdown_months)
    total_monthly_cashflow = adjusted_annuity + monthly_drawdown
    projected_lifetime_annuity = adjusted_annuity * drawdown_months
    projected_lifetime_total = projected_lifetime_annuity + account_total

    return PensionProjection(
        total_work_years=total_work_years,
        future_work_years=future_work_years,
        avg_top_60_insured_salary=avg_top_60,
        labor_annuity_a=annuity_a,
        labor_annuity_b=annuity_b,
        monthly_labor_annuity=monthly_annuity,
        labor_annuity_formula=better_formula,
        monthly_labor_annuity_adjusted=adjusted_annuity,
        estimated_labor_pension_account=account_total,
        estimated_monthly_labor_pension_drawdown=monthly_drawdown,
        total_monthly_retirement_cashflow=total_monthly_cashflow,
        projected_lifetime_labor_annuity=projected_lifetime_annuity,
        projected_lifetime_total_cashflow=projected_lifetime_total,
        rows=rows,
    )
