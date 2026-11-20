"""Deterministic publishing domain fixtures for MockAIProvider."""

DEFAULT_PLANNING_FIXTURES = {
    "coloring": {
        "title_options": [
            "Limona: Cute Animals Coloring Book for Kids",
            "My First Big Book of Cute Animals to Color",
            "Adorable Animal Friends: A Simple Coloring Book for Kids",
        ],
        "subtitle_options": [
            "50 Easy Animal Designs for Little Artists Ages 4-8",
            "Big Bold Pictures with Farm, Forest, Safari and Ocean Animals",
            "A Fun First Coloring Adventure with 50 Friendly Creatures",
        ],
        "target_reader_avatar": "Children aged 4-8 who enjoy simple animal pictures, with parents and caregivers looking for age-appropriate, easy-to-color activities.",
        "front_matter_pages": 4,
        "back_matter_pages": 2,
        "chapters": [
            {
                "chapter_number": 1,
                "title": "Woodland and Forest Friends",
                "summary": "Nine friendly forest animals such as foxes, bears, deer, squirrels, hedgehogs, owls, raccoons, rabbits and wolves. Give each design bold closed outlines, large open spaces and a simple background. Pair every coloring page with a blank reverse page.",
                "key_takeaways": ["9 animal designs", "Bold, closed outlines", "One blank reverse page per design"],
                "estimated_word_count": 100,
                "allocated_pages": 18,
            },
            {
                "chapter_number": 2,
                "title": "Farmyard Friends",
                "summary": "Nine easy farm animal designs including cows, pigs, sheep, horses, chickens, ducks, goats, donkeys and friendly farm dogs. Keep each animal centered, cheerful and simple for young colorists, with a blank reverse page.",
                "key_takeaways": ["9 animal designs", "Simple recognizable farm animals", "Single-sided coloring pages"],
                "estimated_word_count": 100,
                "allocated_pages": 18,
            },
            {
                "chapter_number": 3,
                "title": "Safari and Jungle Animals",
                "summary": "Nine cute safari and jungle animals such as lions, elephants, giraffes, zebras, monkeys, hippos, crocodiles, pandas and tigers. Use large shapes, friendly expressions and uncluttered scenes, with a blank reverse page after each design.",
                "key_takeaways": ["9 animal designs", "Friendly expressions", "Large coloring areas"],
                "estimated_word_count": 100,
                "allocated_pages": 18,
            },
            {
                "chapter_number": 4,
                "title": "Ocean and Polar Pals",
                "summary": "Nine approachable sea and cold-climate creatures including dolphins, whales, turtles, octopuses, starfish, penguins, seals, polar bears and sea otters. Use thick outlines and avoid tiny details; pair each illustration with a blank reverse page.",
                "key_takeaways": ["9 animal designs", "Ocean and polar variety", "No intricate tiny details"],
                "estimated_word_count": 100,
                "allocated_pages": 18,
            },
            {
                "chapter_number": 5,
                "title": "Pets and Playful Companions",
                "summary": "Seven familiar pets such as kittens, puppies, rabbits, guinea pigs, parrots, hamsters and goldfish. Make every pose warm and easy to recognize, with one blank reverse page per coloring design.",
                "key_takeaways": ["7 pet designs", "Familiar home companions", "One-sided coloring artwork"],
                "estimated_word_count": 100,
                "allocated_pages": 14,
            },
            {
                "chapter_number": 6,
                "title": "Birds, Bugs and Tiny Creatures",
                "summary": "Seven cheerful small creatures such as butterflies, ladybugs, bees, caterpillars, songbirds, frogs and snails. Keep shapes bold and uncomplicated, and include a blank reverse page after every coloring page.",
                "key_takeaways": ["7 small-creature designs", "Bold beginner-friendly shapes", "Blank reverse pages"],
                "estimated_word_count": 100,
                "allocated_pages": 14,
            },
        ],
    },
    "finance": {
        "title_options": [
            "The 30-Day Money Reset",
            "Smart Money Habits for Beginners",
            "Zero to Invested: The Simple Wealth Playbook",
        ],
        "subtitle_options": [
            "A Practical Step-by-Step Budgeting and Debt Snowball Guide",
            "How to Take Control of Your Cash Flow in 30 Days",
            "Simple Personal Finance Systems for Young Professionals",
        ],
        "target_reader_avatar": "Working professional aged 24-38 seeking structured, non-intimidating personal finance guidance to eliminate credit card debt and automate savings.",
        "front_matter_pages": 4,
        "back_matter_pages": 2,
        "chapters": [
            {
                "chapter_number": 1,
                "title": "Taking Stock: The Reality Check Audit",
                "summary": "Assess current net worth, track 90-day expenses, and identify unconscious spending leaks without shame.",
                "key_takeaways": ["Calculate baseline net worth", "Identify hidden recurring subscriptions", "Establish zero-judgment baseline"],
                "estimated_word_count": 2800,
                "allocated_pages": 14,
            },
            {
                "chapter_number": 2,
                "title": "The Anti-Budget: Automated Cash Flow",
                "summary": "Design a pay-yourself-first automated split between fixed obligations, guilt-free spending, and wealth accumulation.",
                "key_takeaways": ["Automate payday allocations", "Separate emergency liquidity from spending", "Build frictionless buffer"],
                "estimated_word_count": 3200,
                "allocated_pages": 16,
            },
            {
                "chapter_number": 3,
                "title": "The Debt Elimination Engine",
                "summary": "Compare the mathematical efficiency of the Avalanche method with the psychological momentum of the Snowball method.",
                "key_takeaways": ["Choose snowball vs avalanche", "Negotiate interest rates", "Accelerate principal paydown"],
                "estimated_word_count": 3500,
                "allocated_pages": 18,
            },
            {
                "chapter_number": 4,
                "title": "Building the High-Yield Buffer",
                "summary": "Optimize cash reserves across high-yield savings accounts and laddered short-term instruments.",
                "key_takeaways": ["Calculate 3-6 month runway", "Select secure FDIC/SIPC accounts", "Avoid premature drawdown"],
                "estimated_word_count": 2900,
                "allocated_pages": 14,
            },
            {
                "chapter_number": 5,
                "title": "Index Investing for the Busy Earner",
                "summary": "Demystify total market index funds, dollar-cost averaging, and tax-advantaged retirement accounts.",
                "key_takeaways": ["Understand broad index compounding", "Maximize tax-advantaged space", "Ignore market noise"],
                "estimated_word_count": 3600,
                "allocated_pages": 18,
            },
            {
                "chapter_number": 6,
                "title": "Lifestyle Inflation Defense",
                "summary": "Strategies for managing salary bumps, bonuses, and social spending pressures while maintaining long-term freedom.",
                "key_takeaways": ["The 50% raise rule", "Value-aligned luxury spending", "Cultivate quiet financial independence"],
                "estimated_word_count": 3000,
                "allocated_pages": 14,
            },
        ],
    },
    "default": {
        "title_options": [
            "The Practical Blueprint",
            "Essential Strategies for Mastery",
            "The Structured Operating Guide",
        ],
        "subtitle_options": [
            "Step-by-Step Systems for Actionable Results",
            "Clear Methodologies to Achieve Sustainable Progress",
            "A Practical Handbook for Daily Execution",
        ],
        "target_reader_avatar": "Ambitious self-directed learner looking for structured, fluff-free execution steps and realistic frameworks.",
        "front_matter_pages": 4,
        "back_matter_pages": 2,
        "chapters": [
            {
                "chapter_number": 1,
                "title": "Foundational Principles",
                "summary": "Establish core concepts, eliminate misconceptions, and prepare the baseline operating environment.",
                "key_takeaways": ["Understand first principles", "Audit existing workflows", "Set quantifiable targets"],
                "estimated_word_count": 2500,
                "allocated_pages": 12,
            },
            {
                "chapter_number": 2,
                "title": "Core Methodology & Systems",
                "summary": "Detailed walkthrough of the primary framework with real-world application examples.",
                "key_takeaways": ["Apply the 3-part framework", "Establish standard operating habits", "Mitigate common failure modes"],
                "estimated_word_count": 3200,
                "allocated_pages": 16,
            },
            {
                "chapter_number": 3,
                "title": "Execution & Overcoming Obstacles",
                "summary": "How to maintain momentum, navigate friction points, and sustain consistency under pressure.",
                "key_takeaways": ["Anticipate roadblocks", "Implement feedback loops", "Track objective progress"],
                "estimated_word_count": 3400,
                "allocated_pages": 16,
            },
            {
                "chapter_number": 4,
                "title": "Long-Term Mastery & Scaling",
                "summary": "Transition from initial adoption to compounding results, optimization, and future resilience.",
                "key_takeaways": ["Refine operating efficiency", "Build resilient compounding systems", "Continuous improvement cadence"],
                "estimated_word_count": 3000,
                "allocated_pages": 14,
            },
        ],
    },
}

DEFAULT_METADATA_FIXTURES = {
    "coloring": {
        "keywords": [
            "cute animal coloring book",
            "easy coloring pages for kids",
            "animals coloring book ages 4-8",
            "bold easy animal pictures",
            "preschool coloring activities",
            "farm forest safari animals",
            "first coloring book for children",
        ],
        "keyword_advisories": [
            "Suggested phrases only; verify category and keyword relevance in KDP before publishing."
        ],
        "categories": [
            "Children's Books > Activities, Crafts & Games > Coloring Books",
            "Children's Books > Animals",
            "Children's Books > Growing Up & Facts of Life > Friendship",
        ],
        "description_html": (
            "<h4>Meet 50 Cute Animal Friends to Color!</h4>"
            "<p>Little artists can enjoy a cheerful collection of easy animal pictures made for young children. "
            "Explore friendly forest, farm, safari, ocean, pet and tiny-creature favorites.</p>"
            "<p><b>Inside this coloring adventure:</b></p>"
            "<ul>"
            "<li>50 simple, friendly animal designs.</li>"
            "<li>Bold outlines and large spaces that are easy for little hands to color.</li>"
            "<li>A variety of familiar animals to encourage creativity and imagination.</li>"
            "<li>Single-sided artwork planning with blank reverse pages.</li>"
            "</ul>"
            "<p>A playful activity for children ages 4-8. Review every illustration and all book details before publishing.</p>"
        ),
        "plain_text_summary": "A beginner-friendly coloring book with 50 cute animal designs, bold outlines and large coloring spaces for children ages 4-8.",
        "unconfirmed_disclosure_recommendation": {
            "text_creation_method": "ai_assisted",
            "text_tools_used": ["AI Money Companion Publisher Suite"],
            "text_editing_extent": "extensive_editing",
            "image_creation_method": "none",
            "image_tools_used": [],
            "image_editing_extent": None,
            "translation_creation_method": "none",
            "translation_tools_used": [],
            "translation_editing_extent": None,
            "author_confirmed": False,
        },
    },
    "finance": {
        "keywords": [
            "personal finance for beginners",
            "budgeting planner workbook",
            "debt snowball payoff guide",
            "money management habit reset",
            "how to save and invest money",
            "emergency fund cash flow",
            "financial independence blueprint",
        ],
        "keyword_advisories": [
            "All 7 keyword slots populated under 50 characters.",
            "Keywords do not repeat words from main title."
        ],
        "categories": [
            "Non-fiction > Business & Money > Personal Finance > Budgeting",
            "Non-fiction > Business & Money > Personal Finance > Money Management",
            "Non-fiction > Business & Money > Personal Finance > Investing",
        ],
        "description_html": (
            "<h4>Take Complete Control of Your Money in 30 Days</h4>"
            "<p>Are you tired of feeling like your hard-earned paycheck slips through your fingers before the month even ends? "
            "<i>The 30-Day Money Reset</i> delivers a practical, non-judgmental blueprint to eliminate debt, automate your savings, and build lasting peace of mind.</p>"
            "<p><b>Inside this practical guide, you will discover:</b></p>"
            "<ul>"
            "<li><b>The Reality Check Audit:</b> How to pinpoint unconscious spending leaks in under 60 minutes.</li>"
            "<li><b>The Anti-Budget Method:</b> Automate your cash flow so savings grow on autopilot.</li>"
            "<li><b>The Debt Payoff Engine:</b> Step-by-step strategies to accelerate debt elimination with low stress.</li>"
            "<li><b>Smart Index Investing:</b> A beginner-friendly breakdown of compounding wealth without market timing.</li>"
            "</ul>"
            "<p>Whether you are starting from zero or ready to optimize your financial systems, this book provides the exact framework to build financial freedom.<br>"
            "<em>Scroll up and click Add to Cart to begin your 30-day reset today!</em></p>"
        ),
        "plain_text_summary": "A 30-day practical personal finance guide providing step-by-step frameworks for budgeting, automated savings, debt payoff, and beginner index investing.",
        "unconfirmed_disclosure_recommendation": {
            "text_creation_method": "ai_assisted",
            "text_tools_used": ["AI Money Companion Publisher Suite"],
            "text_editing_extent": "extensive_editing",
            "image_creation_method": "none",
            "image_tools_used": [],
            "image_editing_extent": None,
            "translation_creation_method": "none",
            "translation_tools_used": [],
            "translation_editing_extent": None,
            "author_confirmed": False,
        },
    },
    "default": {
        "keywords": [
            "step by step practical guide",
            "actionable operating blueprint",
            "how to achieve lasting mastery",
            "structured execution framework",
            "daily habit improvement systems",
            "practical strategies handbook",
            "productivity and focus guide",
        ],
        "keyword_advisories": [
            "All 7 keyword slots populated under 50 characters."
        ],
        "categories": [
            "Non-fiction > Self-Help > Personal Growth",
            "Non-fiction > Business & Money > Skills",
            "Non-fiction > Reference > Handbooks",
        ],
        "description_html": (
            "<h4>The Practical Guide to Sustainable Execution</h4>"
            "<p>Transform chaotic ambitions into reliable, repeatable daily systems. "
            "This book provides a clear, actionable methodology designed to eliminate friction and build measurable momentum.</p>"
            "<p><b>What you will learn:</b></p>"
            "<ul>"
            "<li><b>First Principles Audit:</b> Establish a clear baseline without guesswork.</li>"
            "<li><b>The Execution Engine:</b> Practical systems designed for real-world consistency.</li>"
            "<li><b>Overcoming Friction:</b> Actionable protocols when progress stalls.</li>"
            "</ul>"
            "<p><em>Get started on your roadmap to mastery today!</em></p>"
        ),
        "plain_text_summary": "A structured non-fiction operating guide outlining frameworks for continuous progress, habit design, and long-term mastery.",
        "unconfirmed_disclosure_recommendation": {
            "text_creation_method": "ai_assisted",
            "text_tools_used": ["AI Money Companion Publisher Suite"],
            "text_editing_extent": "extensive_editing",
            "image_creation_method": "none",
            "image_tools_used": [],
            "image_editing_extent": None,
            "translation_creation_method": "none",
            "translation_tools_used": [],
            "translation_editing_extent": None,
            "author_confirmed": False,
        },
    },
}


DEFAULT_MANUSCRIPT_FIXTURES = {
    "coloring": {
        "chapter_title": "How to Enjoy Your Animal Coloring Book",
        "markdown_content": (
            "# Welcome, Little Artist!\n\n"
            "Get your favorite crayons, colored pencils or markers ready. This book is filled with friendly animals waiting for your colors.\n\n"
            "## Coloring Tips\n\n"
            "- Start with your favorite animal and choose any colors you like.\n"
            "- Color slowly inside the bold outlines, or make your own patterns.\n"
            "- Try a new color combination and make every page your own.\n"
            "- Place a spare sheet behind the page when using markers.\n\n"
            "There are no wrong colors. Have fun bringing each animal friend to life!"
        ),
    },
    "finance": {
        "chapter_title": "Taking Stock: The Reality Check Audit",
        "markdown_content": (
            "# Taking Stock: The Reality Check Audit\n\n"
            "Before you can direct your money toward long-term wealth, you must confront exactly where it stands today. "
            "Most people avoid this audit not because the math is complicated, but because financial anxiety thrives in ambiguity. "
            "When numbers remain vague, they feel insurmountable. Once they are documented in black and white, they become manageable operational variables.\n\n"
            "## 1. Establishing Your True Net Worth Baseline\n\n"
            "Net worth is not an ego metric; it is your financial compass. Calculate it with complete objectivity:\n\n"
            "- **Liquid Assets:** Checking accounts, high-yield savings, cash reserves.\n"
            "- **Invested Assets:** Retirement accounts, brokerage accounts, employer matching contributions.\n"
            "- **Short-Term Liabilities:** Credit card balances, personal lines of credit, buy-now-pay-later obligations.\n"
            "- **Long-Term Liabilities:** Student loans, auto financing, mortgage balances.\n\n"
            "> **The Golden Rule of Audits:** Treat your personal finances like the Chief Financial Officer of an enterprise. A CFO does not feel guilt about a quarterly deficit; they adjust the cash allocation matrix.\n\n"
            "## 2. Tracking the 90-Day Cash Flow Leaks\n\n"
            "A one-month budget is too short to account for quarterly billing cycles and irregular expenses. "
            "Pull your bank statements and credit card activity for the last 90 days. Group your outflows into three precise categories:\n\n"
            "1. **Fixed Survival Obligations:** Rent or mortgage, basic utilities, core groceries, minimum debt service.\n"
            "2. **Frictionless Convenience Leaks:** Food delivery apps, subscription services you have not opened in 30 days, premium convenience fees.\n"
            "3. **Intentional Discretionary Spending:** Meaningful dining with friends, books, hobbies, and wellness.\n\n"
            "## 3. The 48-Hour Implementation Protocol\n\n"
            "Do not attempt to overhaul your entire lifestyle overnight. Complete these three steps within 48 hours:\n\n"
            "- **Cancel three zombie subscriptions:** Save an immediate $40-$100 per month.\n"
            "- **Consolidate high-interest balances:** Identify the single card charging the highest APR.\n"
            "- **Document your monthly baseline burn rate:** Know your exact minimum cost of living.\n\n"
            "In the next chapter, we will turn this baseline into an automated anti-budget that routes your money before impulse can divert it."
        ),
    },
    "default": {
        "chapter_title": "First Principles: Establishing the Foundation",
        "markdown_content": (
            "# First Principles: Establishing the Foundation\n\n"
            "Sustainable progress requires stripping away conventional assumptions and analyzing your operating environment from first principles. "
            "When you understand the fundamental constraints, solutions become obvious and durable.\n\n"
            "## 1. Defining the Core Operating System\n\n"
            "Systems outperform willpower consistently. To construct an effective workflow:\n\n"
            "- Identify the single highest-leverage recurring action.\n"
            "- Remove friction between intention and execution.\n"
            "- Establish rapid feedback loops to detect drift early.\n\n"
            "## 2. Eliminating Unconscious Waste\n\n"
            "Energy and attention are finite resources. Audit where cognitive overhead accumulates:\n\n"
            "1. Unclear priorities that require repeated daily decision-making.\n"
            "2. Fragmented communication channels.\n"
            "3. Lack of documented standard procedures.\n\n"
            "## 3. Actionable Next Steps\n\n"
            "Focus on incremental, verifiable adjustments that compound over weeks rather than dramatic short-lived efforts."
        ),
    },
}

DEFAULT_ILLUSTRATION_PROMPT_FIXTURES = {
    "coloring": [
            {
                    "prompt": "Cute baby fox sitting beside a small mushroom, centered single animal composition, very bold smooth black closed outlines, large simple coloring areas, minimal background, pure white background, no gray, no shading, no gradients, no text, print-ready children's coloring book line art.",
                    "description": "A friendly fox in a simple woodland scene.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "A cute gentle deer standing beneath an oak tree with two falling leaves, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly gentle deer coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "A cute curious rabbit peeking out from a burrow beside two carrots, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly curious rabbit coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "A cute happy squirrel holding a large acorn on a tree stump, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly happy squirrel coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "A cute smiling hedgehog walking past three simple woodland flowers, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly smiling hedgehog coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "A cute playful raccoon holding a round berry beside a hollow log, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly playful raccoon coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "A cute friendly bear cub sitting beside a small beehive with flowers nearby, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly friendly bear cub coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "A cute wise little owl perched on a thick branch with a crescent moon shape behind it, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly wise little owl coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "A cute busy beaver holding a twig beside a simple pond bank, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly busy beaver coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Woodland and Forest Friends"
            },
            {
                    "prompt": "Cute little cow with large friendly eyes standing in a simple farmyard, bold black closed outlines, broad uncluttered coloring spaces, minimal fence and grass details, white background, no shading, no gray, no text, printable kids coloring book line art.",
                    "description": "A friendly farm cow with a simple setting.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "A cute fluffy sheep standing on a grassy patch with a simple cloud above, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly fluffy sheep coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "A cute cheerful piglet sitting in a clean puddle with two reeds, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly cheerful piglet coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "A cute gentle pony standing beside a hay bale in a barnyard, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly gentle pony coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "A cute curious goat balancing its front hooves on a low rock, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly curious goat coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "A cute little duckling paddling across a small farm pond, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly little duckling coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "A cute happy hen standing beside three large eggs in a nest, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly happy hen coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "A cute friendly donkey wearing a simple neck scarf beside a fence, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly friendly donkey coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "A cute proud rooster standing on a haystack with a simple barn outline, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly proud rooster coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Farmyard Friends"
            },
            {
                    "prompt": "Adorable baby elephant standing and smiling, simple rounded shapes, thick clean black closed outlines, large open spaces for crayons, very few background details, pure white background, no gray, no shadows, no color, no text, print-ready children's coloring page.",
                    "description": "A smiling elephant with beginner-friendly shapes.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "A cute tall giraffe bending its long neck toward a leafy tree, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly tall giraffe coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "A cute striped zebra standing on a savanna patch with two simple grasses, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly striped zebra coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "A cute playful monkey swinging from a short vine with a banana in one hand, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly playful monkey coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "A cute curious tiger cub sitting among two oversized tropical leaves, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly curious tiger cub coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "A cute gentle rhinoceros standing beside a small acacia tree, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly gentle rhinoceros coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "A cute smiling hippopotamus standing in a shallow river with round water ripples, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly smiling hippopotamus coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "A cute baby crocodile resting on a riverbank with a friendly smile, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly baby crocodile coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "A cute colorful-feathered parrot perched on a branch with two large leaves, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly colorful-feathered parrot coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Safari and Jungle Animals"
            },
            {
                    "prompt": "Sweet smiling dolphin jumping above two simple waves, large smooth areas, thick uniform black outlines, clean closed shapes, minimal details, plain white background, no color, no gray, no gradients, no text, printable preschool coloring page.",
                    "description": "An easy-to-color dolphin and wave design.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "A cute giant whale swimming beside three simple bubbles and a tiny fish, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly giant whale coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "A cute curious octopus floating with eight clearly separated arms and a seashell, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly curious octopus coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "A cute sea turtle gliding above a simple coral shape, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly sea turtle coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "A cute happy penguin standing on an ice floe with a small snowflake, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly happy penguin coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "A cute playful seal pup balancing a round beach ball on its nose, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly playful seal pup coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "A cute polar bear cub sitting beside a small igloo on a snowy plain, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly polar bear cub coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "A cute friendly walrus resting on an ice floe with two smooth tusks, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly friendly walrus coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "A cute little clownfish swimming beside a sea anemone with open simple shapes, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly little clownfish coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Ocean and Polar Pals"
            },
            {
                    "prompt": "Adorable fluffy kitten sitting with a small ball of yarn, centered composition, thick clean black outlines, large open coloring areas, minimal background, pure white page, no shadows or gray, no text, kids coloring book line art.",
                    "description": "A playful kitten for young children.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Pets and Playful Companions"
            },
            {
                    "prompt": "A cute happy puppy sitting with a bone-shaped toy on the floor, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly happy puppy coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Pets and Playful Companions"
            },
            {
                    "prompt": "A cute tiny hamster running inside a simple exercise wheel, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly tiny hamster coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Pets and Playful Companions"
            },
            {
                    "prompt": "A cute gentle guinea pig nibbling a leafy vegetable beside a small bowl, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly gentle guinea pig coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Pets and Playful Companions"
            },
            {
                    "prompt": "A cute cute budgie perched on a simple swing inside a birdcage with the door open, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly cute budgie coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Pets and Playful Companions"
            },
            {
                    "prompt": "A cute goldfish swimming in a round fishbowl with two bubbles, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly goldfish coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Pets and Playful Companions"
            },
            {
                    "prompt": "A cute floppy-eared pet rabbit sitting beside a small basket of hay, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly floppy-eared pet rabbit coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Pets and Playful Companions"
            },
            {
                    "prompt": "Cute round butterfly with large symmetrical wings and simple decorative shapes, bold black closed outlines, broad coloring spaces, no intricate patterns, plain white background, no gray, no color, no text, printable children's coloring page.",
                    "description": "A simple butterfly design with broad wing spaces.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Birds, Bugs and Tiny Creatures"
            },
            {
                    "prompt": "A cute spotted ladybug crawling on one broad leaf with a smiling face, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly spotted ladybug coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Birds, Bugs and Tiny Creatures"
            },
            {
                    "prompt": "A cute busy honeybee hovering beside a large daisy flower, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly busy honeybee coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Birds, Bugs and Tiny Creatures"
            },
            {
                    "prompt": "A cute curious snail crawling along a curved garden stem, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly curious snail coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Birds, Bugs and Tiny Creatures"
            },
            {
                    "prompt": "A cute smiling caterpillar resting on a leaf with a tiny flower nearby, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly smiling caterpillar coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Birds, Bugs and Tiny Creatures"
            },
            {
                    "prompt": "A cute friendly toucan perched on a branch with a large beak and two leaves, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly friendly toucan coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Birds, Bugs and Tiny Creatures"
            },
            {
                    "prompt": "A cute graceful flamingo standing on one leg beside a small pond, centered single-subject composition, very bold smooth black closed outlines, large simple coloring areas, child-friendly rounded shapes, minimal uncluttered background, pure white background, no gray, no shading, no gradients, no color fills, no text, no border, print-ready 8.5 x 11 inch children's coloring book line art.",
                    "description": "A simple, friendly graceful flamingo coloring page for ages 4–8.",
                    "style_preset": "bold_kids_coloring_line_art",
                    "suggested_placement": "Birds, Bugs and Tiny Creatures"
            }
    ],
    "finance": [
        {
            "prompt": "Minimalist vector diagram showing the debt snowball method vs debt avalanche method, clean geometric shapes, professional finance editorial style, high contrast, white background.",
            "description": "Visual comparison chart of snowball and avalanche debt repayment trajectories.",
            "style_preset": "modern_clean_vector",
            "suggested_placement": "Chapter 3: The Debt Elimination Engine",
        },
        {
            "prompt": "Clean line-art infographic illustrating automated cash flow allocation: paycheck splitting into emergency savings, investment index fund, and fixed expenses.",
            "description": "Flowchart diagram illustrating automated payday cash routing.",
            "style_preset": "clean_minimalist_line_art",
            "suggested_placement": "Chapter 2: The Anti-Budget",
        },
        {
            "prompt": "Editorial charcoal and monochrome illustration of a focused professional reviewing a simple financial dashboard, elegant composition, crisp line work.",
            "description": "Hero illustration representing the personal net worth reality check audit.",
            "style_preset": "editorial_monochrome",
            "suggested_placement": "Chapter 1: Taking Stock",
        },
    ],
    "default": [
        {
            "prompt": "Modern architectural line-art concept representing strong foundational systems and upward compounding progress, clean vectors, high contrast.",
            "description": "Foundational principles diagram illustrating systemic leverage.",
            "style_preset": "modern_clean_vector",
            "suggested_placement": "Chapter 1: First Principles",
        },
        {
            "prompt": "Minimalist diagram of a continuous feedback loop and iterative optimization framework, monochrome, publication-ready vector style.",
            "description": "Feedback loop optimization diagram.",
            "style_preset": "clean_minimalist_line_art",
            "suggested_placement": "Chapter 2: The Core Framework",
        },
    ],
}

