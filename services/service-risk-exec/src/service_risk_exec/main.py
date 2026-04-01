"""Risk execution service skeleton with shared risk authority wiring."""

from gb_core.risk import RiskExecutionAuthority
from gb_core.schemas import ExecutionDecision, StrategyIntent


authority = RiskExecutionAuthority()


def consume_strategy_intent(intent: StrategyIntent) -> ExecutionDecision:
    """Consume a strategy intent event and emit an execution decision."""
    return authority.consume_intent(intent)


def main() -> None:
    """Run the service_risk_exec placeholder entrypoint."""
    print("service_risk_exec service skeleton")


if __name__ == "__main__":
    main()
