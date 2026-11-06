"""Deterministic publishing domain fixtures for MockAIProvider."""

DEFAULT_PLANNING_FIXTURES = {
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
