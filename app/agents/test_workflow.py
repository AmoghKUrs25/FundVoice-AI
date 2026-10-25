
from app.agents.workflow import build_workflow


def run_test(user_request: str) -> None:
    workflow = build_workflow()

    initial_state = {
        "user_request": user_request,
        "verification_status": "PENDING",
        "report": "",
        "errors": [],
    }

    result = workflow.invoke(initial_state)

    print("\n" + "=" * 50)
    print("FundVoice AI Workflow Test")
    print("=" * 50)

    print("Request:", repr(user_request))
    print("Status:", result["verification_status"])
    print("Report:", result["report"])
    print("Errors:", result["errors"])


if __name__ == "__main__":
    # Test 1: Valid request
    run_test("Generate my mutual fund portfolio report")

    # Test 2: Empty request
    run_test("")
