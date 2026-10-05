from ai.agent import CompanionAgent


def main():

    agent = CompanionAgent()

    print("================================")
    print("       AI Companion")
    print("================================")
    print("Type 'exit' to quit.\n")

    while True:

        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            break

        try:
            result = agent.respond(user_input)

            print(f"\nCompanion: {result.response}")
            print(f"State: {result.state.value}")
            print(f"Intent: {result.intent.value}")
            print(
                f"Permission required: "
                f"{result.permission_required}"
            )
            print()

        except Exception as error:
            print(f"\nError: {error}\n")


if __name__ == "__main__":
    main()