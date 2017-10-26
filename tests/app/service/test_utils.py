from app.service.utils import get_current_financial_year_start_year
from freezegun import freeze_time


# see get_financial_year for conversion of financial years.
@freeze_time("2001-03-31 22:59:59.999999")
def test_get_current_financial_year_start_year_before_march():
    current_fy = get_current_financial_year_start_year()
    assert current_fy == 2000


@freeze_time("2001-03-31 23:00:00.000000")
def test_get_current_financial_year_start_year_after_april():
    current_fy = get_current_financial_year_start_year()
    assert current_fy == 2001
