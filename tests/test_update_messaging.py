from ephemeraldaddy.updates.messaging import STABLE_RELEASE_ASSURANCE


def test_stable_release_assurance_uses_approved_language():
    assert STABLE_RELEASE_ASSURANCE == (
        "This isn't a new and exciting invasion of privacy or a monetization step. "
        "It's just a bug fix and/or feature update I'm gonna go ahead and call 'a stable release'. "
        "With any luck, it will improve function without disrupting anything you currently enjoy. "
        "If you notice something amiss or yearn for something from a prior version, you can roll "
        "back safely & communicate with me on Github."
    )
