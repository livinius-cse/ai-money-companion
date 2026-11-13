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


DEFAULT_MANUSCRIPT_FIXTURES = {
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

