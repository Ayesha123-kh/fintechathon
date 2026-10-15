# Overview
I want to build a robust and helpful agentic application that serves as a personal financial assistant and advisor to the user to help them with their savings.
# Techstack
1. Python (FastApi, sqlAlchemy, Alembic) for backend/
2. Integration logic for self-hosted headless Openmausbot deployed through docker separately in ai-ml/. Look at its [docs](https://github.com/milind-soni/OpenMausBot/blob/main/docs/self-hosting.md).
3. Tailwind NextJS for frontend/
4. Postgres for database, (dragonfly for caching if needed), (redpanda for message broking if needed)
5. Save all agent prompts as md files like: prompts/<agent_name>/SOUL.md
6. Global docker compose for dev deployment and individual dockerfiles and .env files for each subfolder.
7. Railways for prod deployment and final testing.
8. Thinking enabled qwen3.5-9b for llm, an stt model and a decision model all deployed on a remote server using vllm and its modules using OpenAI API compatible endpoints.
9. Openmausbot docker-compose. (Agents would be created as parts of teams, and for each user a group chat would be created with memory for that user only.)
# Features/Requirements
1. Progressive webapp mostly to be used on mobile phones but responsive enough for tablet, laptop and desktop screens.
2. SaaS based application with user login/signup, onboarding, dashboard and chat widget who can also send messages to the user without their invocation even if the app is closed as push notification.
3. Follow row level security and role base access control as user and admin. Also make admin dashboard. Don't need payment gateway integration for now but setup db so that it can be done afterwards.
4. Multiple investment advisor teams for different types of investments Gold & Silver, Domestic (Pakistani) Stocks, Foreign Stocks, Crypto Currencies, Pakistani Real Estate. With each team having independent researcher which pulls from credible and trustworthy sources, expert analyzers, separate watchers for each stock whose job is to generate signals.
5. Onboarding includes asking user all the banks where they have an active account, type of debit/credit card they have like `Visa Silver Card of Meezan Bank` so that we can suggest applicable discounts on cards, their saving goals like saving for `a car within a 6 months period with a salary of RS.100,000/month`, connecting their email inboxes to monitor all incoming and outgoing transactions and update the record of funds accordingly, ask how the savings should be separated from the expendable amount for each month and how to divide between multiple simultaneously active goals.
6. The onboarding must be a chat based feature and not form based and everything can be controlled by informing chatbot.
7. There must only be signup, signin, forget password, email connection, dashboard, goal details, bank details screens and a chatbot widget with popup chatbox. Use modular UI with rounded corners and following colors: `#B0E454`, `#224F10`, `#EAFFD0`, `#0D0D0D`.
8. Have a bank apps like login timeout and option for fingerprint or face recognition login.
9. An agentic team that crawls multiple sources to scrape all the deals and discounts in a country, their time limit, if they require a certain card or generic, their type like `fast food restaurant`, `women's apparel`, `men's footwear` etc and maintain a separate db.
10. An agentic financial advisor teams that study users spending habits, their proffered places for personalized discount advises, if they would opt for sadqah reminder. For every discount user avails suggested by the bot the saved amount goes to their savings.
11. User dashboard should have total expendable and savings money and bank wise breakdown about how much is in which bank. It should also show progress of each goal. The chatbot should also give motivational push notifications like `Great! you just saved x amount this week.` Also identify if user is using money for food, grocery, fuel, medicine, misc etc and have the breakdown on the dashboard.
12. The investment advisor board and feature should be optional and must provide a disclaimer if opted for.
13. If there are any changes like user got an increment and tells the chatbot, it should update in its memory and adjust future advises accordingly.
14. All the agents will be created on first startup like migration and then only updated if their soul or instruction files are updated. They would not have any memory except in a group chat to distinguish users. For agents that are not user specific like asset watchers and discount searchers the previous rules doesn't apply and they can have their own memory.