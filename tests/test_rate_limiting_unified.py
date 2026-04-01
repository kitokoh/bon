
import sys
import pathlib
from datetime import datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from libs.database import BONDatabase

def test_rate_limiting():
    db = BONDatabase(":memory:")
    account_name = "test_account"
    db.create_account(account_name)

    # 1. Test daily limit
    db._exec("UPDATE accounts SET max_groups_per_day = 2 WHERE name = ?", (account_name,))

    # Check initially OK
    can, reason = db.can_account_post(account_name)
    assert can is True, f"Should be OK, but got: {reason}"

    # Record 2 successful posts
    db.record_publication(account_name, "http://group1.com", status="success")
    db.record_publication(account_name, "http://group2.com", status="success")

    # Should be blocked now (daily limit)
    can, reason = db.can_account_post(account_name)
    assert can is False
    assert "Limite quotidienne atteinte" in reason
    print("✓ Daily limit test passed")

    # Reset daily limit for next test
    db._exec("UPDATE accounts SET max_groups_per_day = 10 WHERE name = ?", (account_name,))

    # 2. Test hourly limit
    # We already have 2 posts in the last hour from above.
    # Add 3 more to reach 5.
    db.record_publication(account_name, "http://group3.com", status="success")
    db.record_publication(account_name, "http://group4.com", status="success")
    db.record_publication(account_name, "http://group5.com", status="success")

    # Should be blocked now (hourly limit)
    can, reason = db.can_account_post(account_name)
    assert can is False
    assert "Limite horaire atteinte" in reason
    print("✓ Hourly limit test passed")

    # 3. Test failed posts don't count towards hourly limit
    db = BONDatabase(":memory:") # New DB to be clean
    db.create_account(account_name)
    for i in range(10):
        db.record_publication(account_name, f"http://fail{i}.com", status="failed")

    can, reason = db.can_account_post(account_name)
    assert can is True, f"Failed posts should not block: {reason}"
    print("✓ Failed posts don't block test passed")

if __name__ == "__main__":
    test_rate_limiting()
