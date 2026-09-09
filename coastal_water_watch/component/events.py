"""Pure transition detection for Home Assistant overflow events."""

from dataclasses import dataclass

from .const import EVENT_OVERFLOW_ENDED, EVENT_OVERFLOW_STARTED
from .models import OverflowReport, OverflowState


@dataclass(frozen=True, slots=True)
class OverflowTransition:
    """One confirmed state transition for a known national overflow asset."""

    event_type: str
    report: OverflowReport


def overflow_transitions(
    previous: tuple[OverflowReport, ...],
    current: tuple[OverflowReport, ...],
) -> tuple[OverflowTransition, ...]:
    """Find starts and ends without treating missing assets as confirmed changes."""
    previous_by_id = {report.asset_id: report for report in previous if report.asset_id}
    transitions: list[OverflowTransition] = []
    for report in current:
        prior = previous_by_id.get(report.asset_id)
        if prior is None:
            continue
        if (
            report.state is OverflowState.ACTIVE
            and prior.state is not OverflowState.ACTIVE
        ):
            transitions.append(OverflowTransition(EVENT_OVERFLOW_STARTED, report))
        elif (
            prior.state is OverflowState.ACTIVE
            and report.state is not OverflowState.ACTIVE
        ):
            transitions.append(OverflowTransition(EVENT_OVERFLOW_ENDED, report))
    return tuple(transitions)
