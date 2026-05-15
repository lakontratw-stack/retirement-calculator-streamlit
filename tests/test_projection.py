from retirement_calculator import build_projection, get_insured_salary


def test_insured_salary_tier_caps_at_labor_insurance_maximum():
    assert get_insured_salary(50_000) == (11, 45_800)


def test_projection_returns_positive_retirement_values():
    result = build_projection(
        work_start_age=25,
        current_age=35,
        retirement_age=65,
        first_year_monthly_salary=30_000,
        first_year_insured_salary=30_300,
        current_monthly_salary=50_000,
        current_insured_salary=45_800,
        future_growth_rate=0.02,
        retirement_system="新制",
        old_system_years=0,
        retirement_average_wage=None,
        estimate_past_labor_pension=True,
        employer_contribution_rate=0.06,
        voluntary_contribution_rate=0.0,
        account_return_rate=0.02,
        existing_labor_pension_balance=0,
        claim_timing_years=0,
        life_expectancy_age=85,
        manual_avg_top_60_salary=None,
    )

    assert result.total_work_years == 40
    assert result.avg_top_60_insured_salary == 45_800
    assert result.monthly_labor_annuity > 0
    assert result.estimated_labor_pension_account > 0
    assert result.estimated_old_system_lump_sum == 0


def test_mixed_system_splits_old_and_new_benefits():
    result = build_projection(
        work_start_age=22,
        current_age=50,
        retirement_age=65,
        first_year_monthly_salary=25_000,
        first_year_insured_salary=29_500,
        current_monthly_salary=80_000,
        current_insured_salary=45_800,
        future_growth_rate=0.01,
        retirement_system="新舊制混合",
        old_system_years=10,
        retirement_average_wage=90_000,
        estimate_past_labor_pension=True,
        employer_contribution_rate=0.06,
        voluntary_contribution_rate=0.0,
        account_return_rate=0.02,
        existing_labor_pension_balance=500_000,
        claim_timing_years=0,
        life_expectancy_age=85,
        manual_avg_top_60_salary=None,
    )

    assert result.old_system_years == 10
    assert result.new_system_years == 33
    assert result.old_system_bases == 20
    assert result.estimated_old_system_lump_sum == 1_800_000
    assert result.estimated_labor_pension_account > 500_000


def test_known_labor_pension_balance_does_not_double_count_past_contributions():
    result = build_projection(
        work_start_age=25,
        current_age=35,
        retirement_age=65,
        first_year_monthly_salary=30_000,
        first_year_insured_salary=30_300,
        current_monthly_salary=50_000,
        current_insured_salary=45_800,
        future_growth_rate=0.0,
        retirement_system="新制",
        old_system_years=0,
        retirement_average_wage=None,
        estimate_past_labor_pension=False,
        employer_contribution_rate=0.06,
        voluntary_contribution_rate=0.0,
        account_return_rate=0.011473,
        existing_labor_pension_balance=300_000,
        claim_timing_years=0,
        life_expectancy_age=85,
        manual_avg_top_60_salary=None,
    )

    assert result.estimated_labor_pension_account < 2_000_000
    assert result.labor_pension_annuity_factor > 0
from retirement_calculator import build_projection, get_insured_salary


def test_insured_salary_tier_caps_at_labor_insurance_maximum():
    assert get_insured_salary(50_000) == (11, 45_800)


def test_projection_returns_positive_retirement_values():
    result = build_projection(
        work_start_age=25,
        current_age=35,
        retirement_age=65,
        first_year_monthly_salary=30_000,
        first_year_insured_salary=30_300,
        current_monthly_salary=50_000,
        current_insured_salary=45_800,
        future_growth_rate=0.02,
        retirement_system="新制",
        old_system_years=0,
        retirement_average_wage=None,
        employer_contribution_rate=0.06,
        voluntary_contribution_rate=0.0,
        account_return_rate=0.02,
        existing_labor_pension_balance=0,
        claim_timing_years=0,
        life_expectancy_age=85,
        manual_avg_top_60_salary=None,
    )

    assert result.total_work_years == 40
    assert result.avg_top_60_insured_salary == 45_800
    assert result.monthly_labor_annuity > 0
    assert result.estimated_labor_pension_account > 0
    assert result.estimated_old_system_lump_sum == 0


def test_mixed_system_splits_old_and_new_benefits():
    result = build_projection(
        work_start_age=22,
        current_age=50,
        retirement_age=65,
        first_year_monthly_salary=25_000,
        first_year_insured_salary=29_500,
        current_monthly_salary=80_000,
        current_insured_salary=45_800,
        future_growth_rate=0.01,
        retirement_system="新舊制混合",
        old_system_years=10,
        retirement_average_wage=90_000,
        employer_contribution_rate=0.06,
        voluntary_contribution_rate=0.0,
        account_return_rate=0.02,
        existing_labor_pension_balance=500_000,
        claim_timing_years=0,
        life_expectancy_age=85,
        manual_avg_top_60_salary=None,
    )

    assert result.old_system_years == 10
    assert result.new_system_years == 33
    assert result.old_system_bases == 20
    assert result.estimated_old_system_lump_sum == 1_800_000
    assert result.estimated_labor_pension_account > 500_000
