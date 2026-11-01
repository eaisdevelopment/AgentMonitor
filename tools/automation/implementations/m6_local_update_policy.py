"""Pure admission checks shared by the local dashboard update routine."""


def update_preflight(
    baseline: tuple[str, str],
    current: tuple[str, str],
    candidate: tuple[str, str],
    verified_candidate: tuple[str, str],
    exclusive_and_quiescent: bool,
) -> bool:
    """Require independently verified, unchanged and distinct source trees."""
    return (
        exclusive_and_quiescent
        and all(baseline)
        and all(candidate)
        and baseline == current
        and candidate == verified_candidate
        and baseline[0] != candidate[0]
    )
