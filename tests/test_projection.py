from retirement_calculator import build_projection, get_insured_salary


def test_insured_salary_tier_caps_at_labor_insurance_maximum():
    assert get_insured_salary(50_000) == (11, 45_800)


def test_projection_returns_positive_retirement_values():
    result = build_projection(
        work_start_age=25,
        current_age=35,
        retirement_age=65,
        current_monthly_salary=50_000,
        past_growth_rate=0.02,
        future_growth_rate=0.02,
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
