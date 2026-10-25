from app.agents.workflow import build_workflow


def main():
    workflow = build_workflow()

    initial_state = {
        "user_request": "Generate my mutual fund portfolio report",
        "verification_status": "PENDING",
        "report": "",
        "errors": [],
    }

    result = workflow.invoke(initial_state)

    print("\n--- FundVoice AI Workflow Result ---")
    print("Status:", result["verification_status"])
    print("Report:", result["report"])
    print("Errors:", result["errors"])


if __name__ == "__main__":
    main()