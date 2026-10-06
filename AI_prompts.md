# AI Prompts — Homework 4

A log of every prompt I typed into the vibe coder for this homework, verbatim, grouped by problem.

## Problem 1: Vibe Coder Prompts

> Today I will be working in folder for homework number 4 so put everything that I do in that folder today

> @"/Users/eliselehman/Downloads/data.zip"
> To begin, unzip this file. It has campus_customs.db with tables for the product catalogue, inventory by size, and users. product image paths are in the catalogue table. I'll ask you to use my PORTKEY_API_KEY for my agent AI calls. At the end, I will want to push the project to a public github repo and then I'll submit the repo URL. There are 13 questions for this assignment. Please create AI_prompts.md and update it with everything I type for each question. This prompt should go under Problem 1: Vibe Coder Prompts.

## Problem 2: Analyze the database

> Ok now Problem 2: Analyze the database. I want to look at data/campus_customs.db and understand each of the fields in each table. In a new file, output/harness.md, write down each table and its fields and one  line about why each one matters for the campus customs shop or the chatbot. This file will be added onto in later problems. At minimum, the fields should include catalogue, inventory, and users.

## Problem 3: Build the Campus Customs website

> Ok problem 3: Build the Campus Customs website. I want you to scaffold a React + Vite + TypeScript front end for Campus Customs (which I will call CC from now on). Put a navigation bar at the top of it that links out to the main pages which are: Home, Products, About Us, Log in, and Create Account. Please pull CC-style wording from this site: yalebulldogblue.com for the Home and About Us pages but write yourself (don't plagiarize!). Then, on the Products page, I want you to show product images from the catalogue using the image paths in the data, with basic info on the product so name, price, and a brief description. Make sure each product opens a single item page (with large image on one side, full product text on the other side -- description, price, sizes and stock when you have it too). So, clicking a card on Products pages should take the user there. Then, add a floating chat panel interface in the bottom right hand side of the site. It doesn't have to talk to an agent just yet, a stub that calls backend later is enough for now. I'll need to use a small API soon to read the data but for now its fine to start a simple FastAPI app in backend/main.py to serve products and images then will grow it into the agent backend in a later problem (5).

## Problem 4: Create account and Login

> Now onto Problem 4: Create account and Login. First build a normal create-account / login workflow. Create account - first and last name, email, password, and confirm password. Log in - email and password. New accounts should go into the users table and make sure to store the passwords safely so no one (humans or AI) can access them.
>
> Then, the seed databas has a test user we can use while building. Confirm that you can login as this user (email: test@campuscustoms.yale.edu and password: password) and that the account works. Update output/harness.md with how authorization works so what is stored for users and how they protect passwords here. Thanks!

> Also give me the url please.

> what should I do to fix the issue where the password is not correct?

> go ahead with option 1

## Problem 5: PydanticAI agent backend

> Ok it works for me now too. Now Problem 5: PydanticAI agent backend. We have to build the shop chatbot now as a PydanticAI agent behind FastAPI, plugged into the frontend chat widget. put the api app in backend/main.py which is the file to run with Uvicorn. make sure the agent keeps as these four files next to is: backend/prompts/prompt.md which is a system prompt we will grow later, backend/agent.py for agent entry and wiring, backend/tools.py which has the tools the agent is able to call, backend/models.py which has the PydanticAI structured types. then in main.py, expose a chat route so that a message from the site returns with a reply from the agent and whatever else we need for products/authorization. this will need the AI model API key for the agent.
>
> next, put CC voice and safety basics into prompts/prompt.md -- which will be expanded later. start or update types in models.py for chat replies and product cards as needed. in output/harness.md, write how the frontend talks to fastAPI and how agent is loaded (i.e. prompt file and model). make sure backend runs from backend/folder like: uvicorn main:app --reload --port 8000

## Problem 6: Tools: product info and stock

> Time for problem 6: Tools: product info and stock
>
> Provide the agent with tools that look up real info from campus_customs.db, so product description, price and how many are in stock and in what size when the customer asks. the agent has to use the database and should NOT invent prices or quantities. if a size is out of stock just say that explicitly.
>
> Then, expand promps/prompt.md so agent can call these tools for price and stock questions. add or update the return types in models.py. And in output/harness.md, list each tool and tell what model fields you chose for lookup results and little intuition about why you did that.

## Problem 7: Chat search that updates the page

> Ok time for Problem 7: Chat search that updates the page.
>
> Now we are going to add a feature to this website. what a customer asks about a type of item, like "what hoodies do you have" the agent should search the catalogue and the website will dynamically show those matching items as product cards so image, name, price and short information about the item. This is an API contract: the agent will return structured product matches and then frontend renders them on the site.
>
> Once the dynamic product cards are loaded, make sure the same single-item page behavior built in problem 3 still works. So each product card including the ones from the chat, should still open that detail view (large image with full information when clicked). Update prompts/prompt.md and output/harness.md so its obvious how the search results reach the webpage

## Problem 8: Customer memory

> Nice now Problem 8: Customer memory.
>
> when a shopper's logged in, save all their chat history in the database in an appropriate table and reload it whenever they return to the site. the agent should know who is chatting by name and email and put that in agent deps or an equivalent type of clear pattern and/or tools that the agent can call.  pass enough page context that if someone asks do you have this in pink while on a product page the agent should know which item the customer is talking about. here's a hint -- you can put code into the agent context.
>
> Guests can still chat but history needs to persist for users that are logged in. Then, document in output/harness.md: how user chat history is stored, what customer fields the agent can see and how page context is being passed.

## Problem 9: Usability improvements

> Ok time for Problem 9: Usability improvements.
>
> Let's improve by implementing 1 frontend usability improvement (things to make it easier to use for customers) and 1 backend or agent usability improvement to make the output more accurate or better in general. write output/usability.md before or as you build. for each of the improvements be sure to say what you added and why it helps a CC customer or in turn, the business. Ensure that all the improvements actually show up in the app.
>
> For the front end improvement, I want the website to have accessible color contrast so adjust to meet WCAG AA standards so users with visual impairments can read the content easily. For backend improvement, I want to implement fuzzy search logic so if the customer makes spelling or grammar errors in the chat and search features, the webpage should make logical assumptions and provide the customer with what they are looking for.

> And still for problem 9, we need to make two more improvements. So one more of each type. For front end, allow customers to peak at their password when they are typing it in. So add a button that looks like an eye to make sure that customers are typing it in correctly if they click on it. Make sense?
>
> For the second backend improvement, I want the system to search for results faster. So decrease the amount of time spent "thinking" when the customer asks something to the chatbot. Got it?

## Problem 10: Style the website

> Ok make sure all 4 of those are recorded in output/usability.md
>
> Now, Problem 10: Style the website. Add a creative element to the website so that it feels like a real CC storefront with fonts colors hierarchy motion product presentation and chat feel. Some things you should do if they look good are embrace the negative space so use negative space wisely so certain features and buttons pop. Adopt responsive grids so that depending on if I open this on a phone or tablet the website still looks good. Stick to only two types of font maximum. Incorporate meaningful images of Yale and the CC brand. This should look professional and not ugly. Feel free to take inspiration from https://www.zara.com/us/ and harvard's merch store: https://www.theharvardshop.com/?srsltid=AU7gw4WGrt46de2Y3a9CSfGWupLIHt0rWgU6btooBd6AToZ0U9UbVy8H.
>
> Write output/design.md to include what was changed and why it would help customers stay around and buy more things. Make sure its short and succint.

## Problem 11: Site Testing (app check)

> Now Problem 11: Site Testing (app check).
>
> Test the live site and document it in output/app_check.html which is a page that you should be able to double click to open. Include screenshots and captions for 1) chat checking the inventory level of an item with honest stock and price from the DB, 2) dynamic search result cards that appear after a category question (like hoodies for example), and 3) one of the 4 usability features i added in problem 9.
>
> make the html really easy to grade so heading for each check, screenshot, one or two sentences on what the screenshot proves. Make sure to put the screenshot pic files in output/app_check_images/ and then link them from app_check.html with their relative paths (so for example one might be app_check_images/inventory.png). Make sense?

## Problem 12: Audit trail, safety, finish harness

> Onto the next problem. Problem 12: Audit trail, safety, finish harness.
>
> Keep an append-only output/audit_trail.json of agent loop activity with time tool name, short args and result and stop reason. please do not wipe this between runs. and, add safety rules to give the agent and place them in prompts/prompt/md.
>
> Then, finish output/harness.md so it's clear how the system is working. model fields in models.py and why you chose each, tools and abilities, the safety rules, and specs so loop limits, result caps, models and how to run front and back

## Problem 13: Push to GitHub and submit the URL

> Now last problem 13: Push to GitHub and submit the URL
>
> Put all my code into a folder and name it hw4. push it to a public GitHub repo. Do not include my real .env, campus_customs.db, or product images in the GitHub repo. use .gitignore. include .env.example with placeholders only. the file layout should look something like this
>
> *(attached: screenshot of the target layout: `hw4/` with AI_prompts.md, requirements.txt, .env.example, .gitignore, README.md, frontend/, backend/ (main.py, agent.py, models.py, tools.py, prompts/prompt.md), output/ (harness.md, design.md, usability.md, app_check.html, app_check_images/, audit_trail.json); plus a local-only data pack `data/` with campus_customs.db and products/, not in git)*
>
> the agent itself should only be four files under backend/: prompts/prompt.md, agent.py, tools.py and models.py. README.md is where it should explain everything about how to run the frontend and backend after placing the data pack. any questions?

> *(answers to the assistant's two questions before publishing)*
> Repo name: **hw4 (Recommended)** · Commit email: **Keep Yale email**

**Submitted repo URL:** https://github.com/elehman28/hw4
