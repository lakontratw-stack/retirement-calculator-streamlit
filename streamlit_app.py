from __future__ import annotations

import importlib

import streamlit as st

import retirement_calculator as calculator

calculator = importlib.reload(calculator)
PensionProjection = calculator.PensionProjection
build_projection = calculator.build_projection
get_insured_salary = calculator.get_insured_salary
money = calculator.money


APP_TITLE = "自我工作到退休金試算工具"
DATA_VERSION = "資料基準：民國 115 年（2026-01-01 起適用）"
DISCLAIMER = (
    "本工具為情境試算，方便你理解變數如何影響退休金。實際金額、年資、平均月投保薪資、"
    "勞退個人專戶收益與請領資格，仍以勞保局及勞動部勞工退休金個人專戶資料核定為準。"
)

def render_sidebar_inputs() -> dict:
    st.sidebar.header("試算變數")
    current_age = st.sidebar.number_input("目前年齡", 15, 75, 35, 1)
    work_start_age = st.sidebar.number_input("開始工作年齡", 15, 75, 25, 1)
    retirement_age = st.sidebar.number_input("預計退休年齡", 50, 75, 65, 1)
    life_expectancy_age = st.sidebar.number_input("想估算領到幾歲", 60, 110, 85, 1)

    st.sidebar.divider()
    first_year_monthly_salary = st.sidebar.number_input("工作第一年月薪資總額", 1_000, 500_000, 30_000, 1_000)
    current_monthly_salary = st.sidebar.number_input("目前月薪資總額", 1_000, 500_000, 50_000, 1_000)
    first_default_insured = get_insured_salary(first_year_monthly_salary)[1]
    current_default_insured = get_insured_salary(current_monthly_salary)[1]
    first_year_insured_salary = st.sidebar.number_input(
        "工作第一年勞就保月投保薪資",
        1_000,
        45_800,
        int(first_default_insured),
        100,
        help="如果你手邊有第一年的投保薪資，請直接填；不知道可先用系統依薪資推估的值。",
    )
    current_insured_salary = st.sidebar.number_input(
        "目前勞就保月投保薪資",
        1_000,
        45_800,
        int(current_default_insured),
        100,
        help="用來讓最高 60 個月平均月投保薪資更貼近實際。",
    )
    future_growth_rate = st.sidebar.slider("未來薪資年成長率估算", 0.0, 0.08, 0.02, 0.005)

    st.sidebar.divider()
    retirement_system = st.sidebar.radio("勞退制度", ["新制", "舊制", "新舊制混合"], horizontal=False)
    old_system_years = 0.0
    if retirement_system == "新舊制混合":
        old_system_years = st.sidebar.number_input("保留舊制年資", 0.0, 45.0, 5.0, 0.5)
    elif retirement_system == "舊制":
        st.sidebar.caption("舊制會用全部工作年資估算雇主一次給付退休金。")

    retirement_average_wage = None
    use_manual_retirement_wage = st.sidebar.checkbox("我知道退休前平均工資（舊制基數用）")
    if use_manual_retirement_wage:
        retirement_average_wage = st.sidebar.number_input("退休前平均工資", 1_000, 500_000, int(current_monthly_salary), 1_000)

    st.sidebar.divider()
    employer_contribution_rate = st.sidebar.slider("雇主勞退提繳率", 0.06, 0.15, 0.06, 0.01)
    voluntary_contribution_rate = st.sidebar.slider("個人自願提繳率", 0.0, 0.06, 0.0, 0.01)
    account_return_rate = st.sidebar.slider("勞退帳戶年化收益率假設", 0.0, 0.06, 0.02, 0.005)
    existing_labor_pension_balance = st.sidebar.number_input("目前已累積勞退個人專戶餘額", 0, 50_000_000, 0, 10_000)

    st.sidebar.divider()
    claim_timing_years = st.sidebar.slider("年金請領時間調整", -5, 5, 0, 1)
    use_manual_avg = st.sidebar.checkbox("我知道自己的最高 60 個月平均月投保薪資")
    manual_avg_top_60_salary = None
    if use_manual_avg:
        manual_avg_top_60_salary = st.sidebar.number_input("手動輸入最高 60 個月平均月投保薪資", 1_000, 45_800, 45_800, 100)

    return {
        "work_start_age": int(work_start_age),
        "current_age": int(current_age),
        "retirement_age": int(retirement_age),
        "first_year_monthly_salary": int(first_year_monthly_salary),
        "first_year_insured_salary": int(first_year_insured_salary),
        "current_monthly_salary": int(current_monthly_salary),
        "current_insured_salary": int(current_insured_salary),
        "future_growth_rate": float(future_growth_rate),
        "retirement_system": retirement_system,
        "old_system_years": float(old_system_years),
        "retirement_average_wage": int(retirement_average_wage) if retirement_average_wage else None,
        "employer_contribution_rate": float(employer_contribution_rate),
        "voluntary_contribution_rate": float(voluntary_contribution_rate),
        "account_return_rate": float(account_return_rate),
        "existing_labor_pension_balance": int(existing_labor_pension_balance),
        "claim_timing_years": int(claim_timing_years),
        "life_expectancy_age": int(life_expectancy_age),
        "manual_avg_top_60_salary": int(manual_avg_top_60_salary) if manual_avg_top_60_salary else None,
    }


def render_projection(projection: PensionProjection, inputs: dict) -> None:
    import pandas as pd

    st.subheader("退休後每月可領估算")
    col1, col2, col3 = st.columns(3)
    col1.metric("勞保老年年金（月領）", money(projection.monthly_labor_annuity_adjusted))
    col2.metric("勞退專戶平均攤提（月）", money(projection.estimated_monthly_labor_pension_drawdown))
    col3.metric("合計每月現金流", money(projection.total_monthly_retirement_cashflow))

    st.subheader("累積總額估算")
    col1, col2, col3 = st.columns(3)
    col1.metric("退休時勞退個人專戶", money(projection.estimated_labor_pension_account))
    col2.metric("舊制一次退休金估算", money(projection.estimated_old_system_lump_sum))
    col3.metric("年金 + 勞退 + 舊制總額", money(projection.projected_lifetime_total_cashflow))

    st.caption(
        f"估算總年資 {projection.total_work_years:.1f} 年；舊制 {projection.old_system_years:.1f} 年、"
        f"新制 {projection.new_system_years:.1f} 年；退休後以領到 "
        f"{inputs['life_expectancy_age']} 歲估算。"
    )

    with st.expander("勞保老年年金公式明細", expanded=True):
        st.write(
            f"最高 60 個月平均月投保薪資：{money(projection.avg_top_60_insured_salary)}；"
            f"A 式 {money(projection.labor_annuity_a)}，B 式 {money(projection.labor_annuity_b)}，"
            f"擇優採 {projection.labor_annuity_formula}。"
        )
        if inputs["claim_timing_years"] != 0:
            direction = "展延" if inputs["claim_timing_years"] > 0 else "提前"
            st.write(f"已套用{direction}請領 {abs(inputs['claim_timing_years'])} 年，每年 4% 調整。")

    with st.expander("勞退新舊制明細", expanded=True):
        st.write(
            f"制度：{projection.retirement_system}；舊制年資 {projection.old_system_years:.1f} 年，"
            f"舊制退休金基數 {projection.old_system_bases:g} 個，"
            f"舊制一次退休金估算 {money(projection.estimated_old_system_lump_sum)}。"
        )
        st.write(
            f"新制年資 {projection.new_system_years:.1f} 年，退休時勞退個人專戶估算 "
            f"{money(projection.estimated_labor_pension_account)}。"
        )

    df = pd.DataFrame(projection.rows)
    st.subheader("逐年估算表")
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "估計月薪": st.column_config.NumberColumn(format="NT$ %d"),
            "月投保薪資": st.column_config.NumberColumn(format="NT$ %d"),
            "勞退月提繳工資估算": st.column_config.NumberColumn(format="NT$ %d"),
            "每月勞退提繳": st.column_config.NumberColumn(format="NT$ %d"),
            "年底勞退帳戶估算": st.column_config.NumberColumn(format="NT$ %d"),
        },
    )
    st.line_chart(df.set_index("年齡")[["估計月薪", "月投保薪資", "年底勞退帳戶估算"]])


def render_variables_reference() -> None:
    st.subheader("你需要選填的變數")
    st.write("最少輸入 7 個，完整試算建議 15 個。")
    st.markdown(
        """
| 變數 | 用途 | 不知道時可怎麼填 |
|---|---|---|
| 開始工作年齡 | 推估總勞保年資 | 用第一份正職加保年齡 |
| 目前年齡 | 分開已工作與未來工作期間 | 用實歲 |
| 預計退休年齡 | 決定年資與勞退累積期 | 可先填 65 |
| 工作第一年月薪資總額 | 建立過去薪資起點 | 用第一份正職常態月薪 |
| 工作第一年勞就保月投保薪資 | 建立過去投保薪資起點 | 有勞保紀錄就直接填 |
| 目前月薪資總額 | 對應月投保薪資與勞退提繳 | 用固定月薪加常態津貼 |
| 目前勞就保月投保薪資 | 建立目前投保薪資錨點 | 有勞保紀錄就直接填 |
| 未來薪資年成長率 | 推估退休前最高 60 個月 | 保守可填 1%-2% |
| 勞退制度 | 區分新制、舊制、新舊制混合 | 94 年 7 月後新工作多為新制 |
| 保留舊制年資 | 混合制下估算舊制退休金 | 需同一雇主承認或保留的舊制年資 |
| 退休前平均工資 | 舊制基數乘數基礎 | 不知道時由退休前估計月薪代入 |
| 目前已累積勞退專戶餘額 | 計入已累積本金 | 可到勞保局 e 化服務查詢 |
| 雇主勞退提繳率 | 預設至少 6% | 通常填 6% |
| 個人自願提繳率 | 估算自提對專戶的影響 | 沒有自提填 0% |
| 勞退帳戶年化收益率 | 推估專戶投資收益 | 保守可填 1%-2% |
| 年金請領時間調整 | 提前或展延請領 | 正常退休填 0 |
| 預估領到幾歲 | 估算終身總額與月攤提 | 可填 85 或 90 |
| 最高 60 個月平均月投保薪資 | 讓勞保年金更接近實際 | 知道時手動輸入；不知道由工具估 |
"""
    )


def render_sources() -> None:
    st.subheader("目前採用的規則")
    st.markdown(
        """
- 勞保老年年金：A = 平均月投保薪資 × 年資 × 0.775% + 3,000；B = 平均月投保薪資 × 年資 × 1.55%，兩式擇優。
- 平均月投保薪資：以加保期間最高 60 個月之月投保薪資平均估算。
- 提前或展延請領：最多 5 年，每年 4% 減給或增給。
- 勞保投保薪資分級表：採 115 年 1 月 1 日起適用級距，最高月投保薪資 45,800。
- 勞退新制：預設雇主提繳 6%，可加上個人自願提繳；本工具用月薪估算月提繳工資，非逐級精算。
- 勞退舊制：依勞基法第 55 條估算，前 15 年每年 2 個基數，超過 15 年每年 1 個基數，最高 45 個基數；基數以退休前平均工資估算。
- 新舊制混合：舊制年資估算一次退休金，新制年資估算個人專戶；舊制年資是否成立仍取決於實際雇主、保留年資與個案資料。
"""
    )
    st.info(DISCLAIMER)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="💰", layout="wide")
    st.title(APP_TITLE)
    st.caption(DATA_VERSION)

    inputs = render_sidebar_inputs()
    tab_projection, tab_variables, tab_rules = st.tabs(["退休金試算", "變數說明", "規則與限制"])

    with tab_projection:
        try:
            projection = build_projection(**inputs)
            render_projection(projection, inputs)
        except ValueError as exc:
            st.error(str(exc))

    with tab_variables:
        render_variables_reference()

    with tab_rules:
        render_sources()


if __name__ == "__main__":
    main()
