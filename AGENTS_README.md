# Three Agent System Documentation

This document describes the three specialized AI agents designed to accelerate your journey to trillionaire-level capability.

---

## Overview

The system consists of **four specialized agents**, each with a unique purpose:

1. **Task Executor** (Original) - General-purpose task execution with planning
2. **Transcript Analyzer** (NEW) - Extract maximum value from any transcript
3. **Trillionaire Futurist** (NEW) - Strategic advisor operating at trillionaire scale
4. **Framework Teacher** (NEW) - Meta-learning through frameworks, not prescriptions

---

## Agent 1: Transcript Analyzer 📊

### Purpose
Extracts business value, skills, frameworks, and actionable insights from any transcript (podcasts, interviews, talks, meetings).

### Capabilities

- **Business Value Analysis**: Quantifies revenue impact, cost optimization, strategic positioning
- **Thought Process Deconstruction**: Analyzes how speakers think, their mental models, decision frameworks
- **Skills Identification**: Catalogs hard skills, soft skills, meta-skills, and unique skill combinations
- **Framework Detection**: Identifies named and implicit frameworks used by speakers
- **Lesson Extraction**: Distills universal principles, contrarian insights, meta-lessons
- **10-Step Action Plan**: Creates progressive implementation roadmap from insights

### Use Cases

```python
from agents.transcript_analyzer import TranscriptAnalyzer

analyzer = TranscriptAnalyzer()

# Full comprehensive analysis
analysis = analyzer.analyze(transcript_text)
print(analysis)

# Quick summary (faster)
summary = analyzer.quick_summary(transcript_text)
print(summary["summary"])
```

### Example Output Structure

```markdown
# TRANSCRIPT ANALYSIS REPORT

## 📊 EXECUTIVE SUMMARY
[2-3 sentence core value]

## 💰 BUSINESS VALUE ANALYSIS
- Revenue Impact: [Opportunities]
- Cost Impact: [Efficiencies]
- Strategic Value: [Positioning]
- ROI: [Estimated returns]

## 🧠 THOUGHT PROCESS DECONSTRUCTION
- Mental Models: [Frameworks used]
- Decision-Making Pattern: [How they decide]
- Cognitive Strengths: [What makes them exceptional]

## 🎯 SKILLS DEMONSTRATED
[Table of skills with evidence and proficiency levels]

## 🏗️ FRAMEWORKS IDENTIFIED
[Frameworks with applications and effectiveness scores]

## 📚 KEY LESSONS
- Universal Principles
- Contrarian Perspectives
- Meta-Lessons

## 🚀 10-STEP ACTION PATHWAY
[Detailed steps with Why, How, Success Metrics, Resources, Risks]
```

### Best For
- Analyzing podcast transcripts from world-class performers
- Extracting lessons from interviews and talks
- Identifying patterns across multiple transcripts
- Building personal capability roadmaps

---

## Agent 2: Trillionaire Futurist 🚀

### Purpose
Speaks to you as a peer trillionaire. Data-driven, proof-based, creates the future rather than predicting it.

### Operating Philosophy

- **Create, Don't Predict**: You don't forecast - you architect reality
- **Proof-Based Conviction**: Every statement backed by data, case studies, first principles
- **Infinite Resources, Finite Time**: Money unlimited, time is the constraint
- **Asymmetric Information**: Operates with information others don't have
- **Systems-Level Thinking**: Sees second/third-order effects, cross-sector convergence

### Communication Style

- **Quantified**: Numbers, not adjectives
- **Global Scope**: Thinks in continents, not cities
- **Long Timeframes**: 2030, 2040, 2050 horizons
- **Action-Oriented**: Every response demands execution within 48-72 hours
- **Dense**: Maximum insight per sentence

### Use Cases

```python
from agents.trillionaire_futurist import TrillionaireFuturist

futurist = TrillionaireFuturist()

# Strategic guidance
response = futurist.respond("Should I start a company or keep my job?")
print(response)

# Opportunity analysis
analysis = futurist.analyze_opportunity("""
AI-powered climate tech B2B platform targeting Fortune 500 companies.
$50M raised, $5M ARR, 40% YoY growth.
""")
print(analysis["analysis"])
```

### Response Framework

Every response includes:
1. **Reframe to Trillionaire Scale**: Shifts perspective to 10x-100x outcomes
2. **Multi-Horizon Perspective**: Immediate, near-term, medium-term, long-term
3. **Quantified Analysis**: Market size, growth rates, timelines, capital required
4. **Evidence**: Data, case studies, research, precedents
5. **Concrete Pathways**: Executable strategies with budgets and timelines
6. **Portfolio Thinking**: Multiple bets across risk profiles
7. **Hidden Opportunities**: Non-obvious connections and arbitrage

### Example Response Structure

```markdown
SITUATION ANALYSIS
[Data-backed current state]

TRILLIONAIRE PERSPECTIVE
[Unlimited resources view]

OPPORTUNITY QUANTIFICATION
- Market: $X
- Growth: Y%
- Time Window: Z months

EXECUTION BLUEPRINT
Phase 1: [Specific actions, budget, team]
Phase 2: [Scaling, targets, metrics]
Phase 3: [Dominance, exit options]

RISK FACTORS & MITIGATION
[Risks with probabilities and solutions]

YOUR MOVE
[Action in next 48 hours]
```

### Best For
- Strategic business decisions
- Opportunity evaluation
- High-stakes planning
- Breaking through incremental thinking
- Capital allocation

---

## Agent 3: Framework Teacher 🧠

### Purpose
Teaches through frameworks and mental models, not specific steps. Focuses on meta-skills that transfer across all contexts.

### Teaching Philosophy

- **Frameworks Over Formulas**: Flexible systems, not rigid scripts
- **Generalization Over Specification**: Broad principles, not narrow tactics
- **Transferability**: Skills that work across domains and decades
- **Meta-Skills**: Capabilities that make learning other skills easier
- **Simplicity Through Structure**: Memorable (3-2-1, OODA, 80/20)

### Trillionaire Skill Taxonomy

#### Tier 1: Foundational Meta-Skills
- Thinking Frameworks (First Principles, Systems Thinking, Probabilistic Reasoning)
- Learning Frameworks (Rapid Skill Acquisition, Deliberate Practice, Meta-Learning)
- Decision Frameworks (Speed-Quality Tradeoff, Expected Value, Regret Minimization)

#### Tier 2: Execution Meta-Skills
- Communication Frameworks (Audience Calibration, Information Density, Narrative Structure)
- Influence Frameworks (Reciprocity, Social Proof, Authority Building)
- Negotiation Frameworks (BATNA, Value Creation, Concession Strategy)

#### Tier 3: Strategic Meta-Skills
- Opportunity Recognition (Arbitrage Spotting, Trend Intersection)
- Resource Allocation (Portfolio Thinking, Leverage Maximization)
- Relationship Building (Network Orchestration, Value-First Approach)

#### Tier 4: Mastery Meta-Skills
- Self-Awareness (Bias Detection, Emotion Regulation)
- Resilience (Failure Processing, Adaptation Speed)
- Legacy (Impact Measurement, Institution Building)

### Use Cases

```python
from agents.framework_teacher import FrameworkTeacher

teacher = FrameworkTeacher()

# Full framework teaching
response = teacher.teach("How do I make better decisions under uncertainty?")
print(response)

# Quick framework
quick = teacher.quick_framework("responding to difficult questions")
print(quick)

# List frameworks
frameworks = teacher.list_frameworks(category="thinking")
print(frameworks)
```

### Framework Format

Every framework includes:
1. **NAME**: Memorable (3-2-1, THINK, DECIDE)
2. **PRINCIPLE**: Underlying truth
3. **STRUCTURE**: Exact components/steps
4. **APPLICATION**: How to use across contexts
5. **EXAMPLES**: 3-5 diverse scenarios
6. **ANTI-PATTERNS**: Common mistakes
7. **PROGRESSION**: Beginner → Master

### Example: 3-2-1 Framework Family

#### 3-2-1 Communication
- **3 elements**: Context, Core, Consequence
- **2 depths**: Simple or Complex
- **1 question**: Is this worth communicating?

#### 3-2-1 Decision
- **3 outcomes**: Best, Base, Worst
- **2 factors**: Reversibility + Magnitude
- **1 bias check**: What am I missing?

#### 3-2-1 Learning
- **3 passes**: Skim, Study, Synthesize
- **2 modes**: Consume + Create
- **1 test**: Can you teach it?

### Best For
- Learning generalized capabilities
- Developing mental models
- Building transferable skills
- Meta-learning optimization
- Creating personal frameworks

---

## Using the Agents

### Via CLI

```bash
# Start the ChatSystem
python -m ChatSystem

# List available agents
/agents

# Switch to an agent
/agent analyzer          # Transcript Analyzer
/agent futurist          # Trillionaire Futurist
/agent teacher           # Framework Teacher
/agent executor          # Task Executor (default)

# Use the agent
[Type your request]
```

### Via Python

```python
from agents.agent_manager import AgentManager, AgentType
from ChatSystem.core.config import get_settings

# Initialize
settings = get_settings()
manager = AgentManager(settings=settings)

# Use Transcript Analyzer
analyzer = manager.get_agent(AgentType.TRANSCRIPT_ANALYZER)
result = analyzer.analyze(transcript)

# Use Trillionaire Futurist
futurist = manager.get_agent(AgentType.TRILLIONAIRE_FUTURIST)
guidance = futurist.respond("Should I raise a Series A or bootstrap?")

# Use Framework Teacher
teacher = manager.get_agent(AgentType.FRAMEWORK_TEACHER)
framework = teacher.teach("How do I build resilience?")
```

### Via Test Script

```bash
# Run comprehensive tests
python test_agents.py
```

---

## Configuration

Edit `config.yaml` to customize agent behavior:

```yaml
agents:
  transcript_analyzer:
    max_iterations: 3
    model: o3-mini
    timeout_seconds: 600

  trillionaire_futurist:
    max_iterations: 5
    model: o3-mini
    timeout_seconds: 600

  framework_teacher:
    max_iterations: 3
    model: o3-mini
    timeout_seconds: 300
```

---

## Workflow Recommendations

### Daily Learning Workflow
1. **Morning**: Framework Teacher - Learn a new meta-skill framework
2. **During Day**: Transcript Analyzer - Analyze 1-2 podcasts/interviews
3. **Evening**: Trillionaire Futurist - Strategic planning and opportunity analysis

### Project Workflow
1. **Ideation**: Trillionaire Futurist - Opportunity analysis and strategic direction
2. **Capability Building**: Framework Teacher - Learn necessary meta-skills
3. **Learning**: Transcript Analyzer - Extract insights from expert transcripts
4. **Execution**: Task Executor - Implement and execute

### Weekly Review Workflow
1. **Analyze transcripts** from the week's learning
2. **Extract frameworks** and create personal mental models
3. **Get strategic guidance** on next moves
4. **Plan execution** for the coming week

---

## Advanced Usage

### Combining Agents

```python
# 1. Analyze a transcript
analysis = analyzer.analyze(podcast_transcript)

# 2. Extract frameworks from the analysis
frameworks_request = f"Based on this analysis, what frameworks can I learn?\n\n{analysis}"
frameworks = teacher.teach(frameworks_request)

# 3. Get strategic guidance on implementation
strategy_request = f"Based on these insights, what strategic moves should I make?\n\n{analysis}"
strategy = futurist.respond(strategy_request)
```

### Custom Personas

You can modify agent personas by editing:
- `agents/transcript_analyzer/analyzer.py` - `SYSTEM_PERSONA`
- `agents/trillionaire_futurist/futurist.py` - `SYSTEM_PERSONA`
- `agents/framework_teacher/teacher.py` - `SYSTEM_PERSONA`

---

## Tips for Maximum Value

### Transcript Analyzer
- Feed it transcripts from world-class performers in your field
- Use the 10-step pathways as actual execution plans
- Look for patterns across multiple analyses
- Focus on meta-lessons and frameworks identified

### Trillionaire Futurist
- Ask big, ambitious questions - don't think small
- Demand quantification - make it back you up with data
- Use it for go/no-go decisions on major opportunities
- Follow the 48-hour action items religiously

### Framework Teacher
- Start with foundational meta-skills (Tier 1)
- Practice frameworks immediately - don't just collect them
- Adapt frameworks to your specific context
- Teach frameworks to others to deepen understanding

---

## File Structure

```
agents/
├── agent_manager.py                 # Orchestrates all agents
├── task_executor/                   # Original task executor
│   ├── executor.py
│   ├── planner.py
│   └── reasoner.py
├── transcript_analyzer/             # NEW
│   ├── __init__.py
│   └── analyzer.py
├── trillionaire_futurist/           # NEW
│   ├── __init__.py
│   └── futurist.py
└── framework_teacher/               # NEW
    ├── __init__.py
    └── teacher.py
```

---

## Support

For issues or enhancements:
1. Check the agent source code for detailed personas
2. Run `test_agents.py` to verify functionality
3. Modify `config.yaml` for custom behavior
4. Edit agent `SYSTEM_PERSONA` for customization

---

## Philosophy

These three agents represent three dimensions of capability:

1. **Transcript Analyzer** = **INPUT OPTIMIZATION**
   - Extract maximum value from what exists
   - Learn from the best

2. **Trillionaire Futurist** = **OUTPUT OPTIMIZATION**
   - Create maximum value in the world
   - Operate at the highest level

3. **Framework Teacher** = **SYSTEM OPTIMIZATION**
   - Build the operating system for excellence
   - Develop meta-capabilities

Together, they form a complete system for accelerating toward trillionaire-level capability:
- **Learn** the best thinking (Analyzer)
- **Build** the best capabilities (Teacher)
- **Execute** at the highest level (Futurist)

---

*Built for those who don't just want to reach the top - but redefine what the top is.*
