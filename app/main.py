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
            response = agent.respond(user_input)
            print(f"\nCompanion: {response}\n")

        except Exception as error:
            print(f"\nError: {error}\n")


if __name__ == "__main__":
    main()