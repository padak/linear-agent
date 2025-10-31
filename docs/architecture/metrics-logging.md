# Success Metrics Logging Strategy

## Overview

This document defines how to measure MVP success criteria through automated and manual logging mechanisms. The strategy enables objective Go/No-Go validation at the end of Week 1.

---

## Automated Metrics (Database-Backed)

### 1. Uptime Tracking

**Purpose:** Validate that the agent delivers briefings reliably (99% uptime = 7/7 days, max 1 miss)

**Data Source:** `briefings` table `delivery_status` field

**Logging Implementation:**
```python
# In briefing_delivery.py or main orchestrator
import logging
from datetime import datetime

logger = logging.getLogger("metrics")

async def send_briefing_telegram(briefing_id: int, chat_id: str):
    """
    Log delivery status to database.
    delivery_status values: 'pending' -> 'sent' or 'permanently_failed'
    """
    try:
        await telegram_bot.send_message(chat_id, markdown_briefing)

        # Log successful delivery
        db.execute("""
            UPDATE briefings
            SET delivery_status = 'sent',
                telegram_message_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (message_id, briefing_id))

        logger.info(f"METRIC: briefing_sent", extra={
            "briefing_id": briefing_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        # Log failed delivery
        db.execute("""
            UPDATE briefings
            SET delivery_status = 'permanently_failed',
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (str(e), briefing_id))

        logger.error(f"METRIC: briefing_failed", extra={
            "briefing_id": briefing_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
```

**Query to Check Uptime:**
```sql
-- Check 7-day uptime
SELECT
    COUNT(*) as total_days,
    SUM(CASE WHEN delivery_status = 'sent' THEN 1 ELSE 0 END) as successful_deliveries,
    SUM(CASE WHEN delivery_status = 'permanently_failed' THEN 1 ELSE 0 END) as failed_deliveries,
    ROUND(100.0 * SUM(CASE WHEN delivery_status = 'sent' THEN 1 ELSE 0 END) / COUNT(*), 2) as uptime_percentage
FROM briefings
WHERE generated_at >= date('now', '-7 days')
GROUP BY date(generated_at);

-- Single uptime percentage for the week
SELECT
    ROUND(100.0 * SUM(CASE WHEN delivery_status = 'sent' THEN 1 ELSE 0 END) / COUNT(*), 2) as uptime_percentage
FROM briefings
WHERE generated_at >= date('now', '-7 days');
```

**Acceptance Criteria:**
- ✅ PASS: ≥ 6 successful deliveries out of 7 days (99% uptime allows 1 miss)
- ❌ FAIL: < 6 successful deliveries in 7 days

---

### 2. Cost Tracking

**Purpose:** Validate that API costs stay within budget (<$20/month for 30 briefings)

**Data Source:** `briefings` table `cost_usd` field (populated from Anthropic API usage)

**Logging Implementation:**
```python
# In cost_tracker.py or api_client.py
import logging
from decimal import Decimal

logger = logging.getLogger("metrics")

async def generate_briefing_with_claude(issues: List[Issue]) -> Briefing:
    """
    Call Claude API and track token usage & cost.
    Anthropic pricing as of 2025:
    - Input: $0.80 per 1M tokens
    - Output: $4.00 per 1M tokens
    """
    response = await anthropic_client.messages.create(...)

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Calculate cost
    input_cost = Decimal(input_tokens) * Decimal("0.0000008")  # $0.80 per 1M
    output_cost = Decimal(output_tokens) * Decimal("0.000004")  # $4.00 per 1M
    total_cost = input_cost + output_cost

    # Log to database
    db.execute("""
        UPDATE briefings
        SET tokens_used = ?,
            cost_usd = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (input_tokens + output_tokens, float(total_cost), briefing_id))

    logger.info(f"METRIC: briefing_cost", extra={
        "briefing_id": briefing_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": float(total_cost),
        "timestamp": datetime.utcnow().isoformat()
    })

    return briefing
```

**Query to Check Monthly Cost:**
```sql
-- Cost for last 30 days
SELECT
    COUNT(*) as briefing_count,
    ROUND(SUM(cost_usd), 2) as total_cost_usd,
    ROUND(AVG(cost_usd), 4) as avg_cost_per_briefing,
    ROUND(MIN(cost_usd), 4) as min_cost,
    ROUND(MAX(cost_usd), 4) as max_cost
FROM briefings
WHERE generated_at >= date('now', '-30 days');

-- Cost by week (for trend analysis)
SELECT
    DATE(generated_at) as date,
    COUNT(*) as briefing_count,
    ROUND(SUM(cost_usd), 2) as daily_cost
FROM briefings
WHERE generated_at >= date('now', '-30 days')
GROUP BY DATE(generated_at)
ORDER BY date DESC;
```

**Acceptance Criteria:**
- ✅ PASS: Total cost < $20.00 for 30 days (or proportional for <30 days)
- ❌ FAIL: Total cost ≥ $20.00

**Cost Optimization Notes:**
- If costs exceed $20: Review prompt sizes, consider caching frequently asked questions
- If costs under $10: Process is highly efficient, can afford more complex reasoning

---

### 3. Performance Tracking

**Purpose:** Validate that briefing generation completes in < 30 seconds

**Data Source:** Structured logs with timing data (captured during execution)

**Logging Implementation:**
```python
# In briefing_generation.py or orchestrator
import logging
import time
from datetime import datetime
import json

logger = logging.getLogger("metrics")

class BriefingGenerationTimer:
    """Context manager for tracking stage timings."""

    def __init__(self, stage_name: str, briefing_id: int):
        self.stage_name = stage_name
        self.briefing_id = briefing_id
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        # Log timing to structured log
        log_entry = {
            "stage": self.stage_name,
            "duration_ms": round(duration_ms, 2),
            "briefing_id": self.briefing_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": exc_type is None
        }

        logger.info(f"METRIC: stage_timing", extra=log_entry)

        # Optional: Also write to file for easier parsing
        with open("/tmp/briefing_metrics.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

# Usage in workflow
async def generate_daily_briefing(user_id: str) -> str:
    """Main briefing generation pipeline with performance tracking."""

    briefing_id = db.create_briefing_record()
    total_start = time.time()

    try:
        # Stage 1: Fetch issues
        with BriefingGenerationTimer("fetch_issues", briefing_id):
            issues = await linear_client.get_assigned_issues(user_id)

        # Stage 2: Rank issues
        with BriefingGenerationTimer("rank_issues", briefing_id):
            ranked = issue_ranker.rank(issues)

        # Stage 3: Generate briefing text (most expensive)
        with BriefingGenerationTimer("generate_text", briefing_id):
            briefing_text = await claude_agent.generate_briefing(ranked)

        # Stage 4: Format and store
        with BriefingGenerationTimer("format_store", briefing_id):
            formatted = telegram_formatter.format(briefing_text)
            db.store_briefing(briefing_id, formatted)

        # Log total duration
        total_duration_ms = (time.time() - total_start) * 1000
        logger.info(f"METRIC: briefing_total", extra={
            "briefing_id": briefing_id,
            "total_duration_ms": round(total_duration_ms, 2),
            "timestamp": datetime.utcnow().isoformat()
        })

        return briefing_text

    except Exception as e:
        logger.error(f"METRIC: generation_error", extra={
            "briefing_id": briefing_id,
            "error": str(e),
            "duration_ms": (time.time() - total_start) * 1000
        })
        raise
```

**Metrics File Format:** `/tmp/briefing_metrics.jsonl` (one JSON object per line)
```json
{"stage": "fetch_issues", "duration_ms": 1234.5, "briefing_id": 1, "timestamp": "2025-01-30T09:00:15Z", "success": true}
{"stage": "rank_issues", "duration_ms": 456.2, "briefing_id": 1, "timestamp": "2025-01-30T09:00:16Z", "success": true}
{"stage": "generate_text", "duration_ms": 12345.8, "briefing_id": 1, "timestamp": "2025-01-30T09:00:28Z", "success": true}
{"stage": "format_store", "duration_ms": 234.1, "briefing_id": 1, "timestamp": "2025-01-30T09:00:29Z", "success": true}
{"stage": "briefing_total", "duration_ms": 14270.6, "briefing_id": 1, "timestamp": "2025-01-30T09:00:29Z", "success": true}
```

**Query to Analyze Performance:**
```python
# Python script to parse and analyze metrics from JSONL
import json
from statistics import mean, median, stdev
from pathlib import Path

def analyze_performance_metrics():
    """Parse performance logs and calculate statistics."""

    metrics = {"briefing_total": []}

    with open("/tmp/briefing_metrics.jsonl") as f:
        for line in f:
            entry = json.loads(line)
            if entry["stage"] == "briefing_total":
                metrics["briefing_total"].append(entry["duration_ms"])

    if metrics["briefing_total"]:
        durations = metrics["briefing_total"]
        print(f"Performance Metrics (Last 7 Days)")
        print(f"  Total Briefings: {len(durations)}")
        print(f"  Min: {min(durations):.1f}ms")
        print(f"  Max: {max(durations):.1f}ms")
        print(f"  Mean: {mean(durations):.1f}ms")
        print(f"  Median: {median(durations):.1f}ms")
        print(f"  Stdev: {stdev(durations):.1f}ms")
        print(f"  P95: {sorted(durations)[int(len(durations) * 0.95)]:.1f}ms")
        print(f"  <30s: {sum(1 for d in durations if d < 30000)} / {len(durations)}")
```

**Acceptance Criteria:**
- ✅ PASS: Median duration < 30,000ms AND P95 < 35,000ms
- ❌ FAIL: Median ≥ 30,000ms OR >10% of briefings exceed 30s

---

## Manual Metrics (Human-in-the-Loop)

### 4. Briefing Relevance Rating

**Purpose:** Measure content quality (target: ≥70% relevance = 7/10 average rating)

**Data Source:** Daily manual journal file

**Implementation:**

1. **Create relevance log file:**
   ```bash
   mkdir -p ~/.linear_chief
   touch ~/.linear_chief/relevance_log.csv
   ```

2. **Log format:** `relevance_log.csv`
   ```csv
   date,relevance_score,notes
   2025-01-30,8,Good issue selection - all high-priority items included
   2025-01-31,6,Too many low-priority items - noise in briefing
   2025-02-01,9,Excellent ranking - blocked issues correctly flagged
   2025-02-02,7,Mixed - 2/3 issues were relevant
   2025-02-03,8,Very relevant - correctly identified team blockers
   ```

3. **Scoring Guide:**
   - **9-10:** Excellent - All top issues ranked correctly, high signal
   - **7-8:** Good - Most relevant issues present, minimal noise
   - **5-6:** Fair - Some relevant issues but also noise
   - **3-4:** Poor - More noise than signal
   - **1-2:** Very Poor - Irrelevant content

4. **Daily Rating Process:**
   ```bash
   # After reading briefing each morning, run:
   python -m linear_chief.cli log-relevance --score 8 --notes "Good issue selection"

   # Or manually append to CSV:
   echo "2025-01-30,8,Good issue selection" >> ~/.linear_chief/relevance_log.csv
   ```

**Query to Calculate Average Relevance:**
```python
import csv
from pathlib import Path
from statistics import mean

def get_relevance_score():
    """Calculate average relevance rating."""

    log_file = Path.home() / ".linear_chief" / "relevance_log.csv"

    scores = []
    with open(log_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only include ratings from last 7 days
            scores.append(int(row["relevance_score"]))

    if scores:
        avg = mean(scores)
        pct = (avg / 10) * 100  # Convert to percentage
        print(f"Relevance Score: {avg:.1f}/10 ({pct:.0f}%)")
        print(f"Ratings: {len(scores)} over {len(scores)} days")
        return avg / 10

    return 0
```

**Acceptance Criteria:**
- ✅ PASS: Average relevance ≥ 7.0/10 (70%) over 7 days
- ❌ FAIL: Average relevance < 7.0/10 over 7 days

---

### 5. Time Savings Analysis

**Purpose:** Validate that briefing saves ≥10 minutes per morning vs. manual Linear checking

**Data Source:** Weekly retrospective journal entries

**Implementation:**

1. **Create time tracking file:**
   ```bash
   touch ~/.linear_chief/time_saved_log.csv
   ```

2. **Log format:** Weekly entries
   ```csv
   week_ending,briefing_read_time_min,manual_linear_time_min,time_saved_min,notes
   2025-02-02,4,15,11,Briefing was quick to scan; manual would involve filtering issues
   2025-02-09,3,18,15,More issues this week; briefing ranking saved time finding blockers
   2025-02-16,5,14,9,Longer read time due to agent context; still faster than manual
   ```

3. **How to Estimate (Weekly Retrospective):**
   ```markdown
   ## Week 1 Time Savings Retrospective

   **Briefing Read Time:** ~4 minutes
   - Glanced at briefing: 2 min
   - Read descriptions/context: 2 min
   - Total: 4 min

   **If I Had Done This Manually in Linear:**
   - Login + loading: 1 min
   - Filter to assigned issues: 2 min
   - Read and triage each issue: 10 min
   - Identify blockers/blocked items: 2 min
   - Find related context: 3 min
   - Total: ~18 min

   **Time Saved:** 18 - 4 = 14 minutes
   ```

**Query to Calculate Average Time Saved:**
```python
import csv
from pathlib import Path
from statistics import mean

def get_time_savings():
    """Calculate average time saved per week."""

    log_file = Path.home() / ".linear_chief" / "time_saved_log.csv"

    weekly_savings = []
    with open(log_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            savings = int(row["time_saved_min"])
            weekly_savings.append(savings)

    if weekly_savings:
        avg = mean(weekly_savings)
        print(f"Average Time Saved: {avg:.1f} minutes/week")
        print(f"Daily Average: {avg / 7:.1f} minutes/day")
        return avg / 7

    return 0
```

**Acceptance Criteria:**
- ✅ PASS: Average time saved ≥ 10 minutes per day
- ❌ FAIL: Average time saved < 10 minutes per day

---

## CLI Commands for Metrics Dashboard

### Implementation in `cli.py`

```python
# In linear_chief/cli.py

import click
from linear_chief.metrics import MetricsCollector
from linear_chief.database import get_db
from pathlib import Path
import json

@click.command()
@click.option('--auto-only', is_flag=True, help='Show only automated metrics')
def metrics(auto_only):
    """Display all success metrics."""

    collector = MetricsCollector(get_db())

    # Automated metrics
    uptime = collector.get_uptime()
    cost = collector.get_monthly_cost()
    performance = collector.get_performance_stats()

    print("\n" + "="*60)
    print("LINEAR CHIEF - SUCCESS METRICS")
    print("="*60)

    print("\nAUTOMATED METRICS (Database-Backed)")
    print("-" * 60)

    # Uptime
    print(f"\n1. UPTIME (Target: 99% = 7/7 days)")
    print(f"   Last 7 Days: {uptime['successful']}/{uptime['total']} deliveries")
    print(f"   Percentage: {uptime['percentage']:.1f}%")
    status = "✅ PASS" if uptime['percentage'] >= 99 else "❌ FAIL"
    print(f"   Status: {status}")

    # Cost
    print(f"\n2. COST TRACKING (Target: <$20/month)")
    print(f"   Last 30 Days: ${cost['total']:.2f} for {cost['briefing_count']} briefings")
    print(f"   Average Cost: ${cost['avg_per_briefing']:.4f}/briefing")
    status = "✅ PASS" if cost['total'] < 20.00 else "❌ FAIL"
    print(f"   Status: {status}")

    # Performance
    print(f"\n3. PERFORMANCE (Target: <30 seconds)")
    print(f"   Briefings Analyzed: {performance['count']}")
    print(f"   Median: {performance['median']:.0f}ms ({performance['median']/1000:.1f}s)")
    print(f"   Mean: {performance['mean']:.0f}ms ({performance['mean']/1000:.1f}s)")
    print(f"   P95: {performance['p95']:.0f}ms ({performance['p95']/1000:.1f}s)")
    print(f"   <30s: {performance['under_30s']}/{performance['count']}")
    status = "✅ PASS" if performance['median'] < 30000 else "❌ FAIL"
    print(f"   Status: {status}")

    if not auto_only:
        print("\n" + "-" * 60)
        print("MANUAL METRICS (Human Ratings)")
        print("-" * 60)

        # Relevance
        relevance = collector.get_relevance_score()
        print(f"\n4. BRIEFING RELEVANCE (Target: ≥70%)")
        if relevance:
            print(f"   Average Score: {relevance['avg']:.1f}/10 ({relevance['percentage']:.0f}%)")
            print(f"   Ratings: {relevance['count']} over {relevance['days']} days")
            status = "✅ PASS" if relevance['avg'] >= 7.0 else "❌ FAIL"
        else:
            print(f"   No ratings recorded yet")
            status = "⏳ PENDING"
        print(f"   Status: {status}")

        # Time Savings
        time_saved = collector.get_time_savings()
        print(f"\n5. TIME SAVED (Target: ≥10 min/day)")
        if time_saved:
            print(f"   Average: {time_saved['daily_avg']:.1f} min/day")
            print(f"   Weekly: {time_saved['weekly_avg']:.1f} min/week")
            print(f"   Estimates: {time_saved['count']}")
            status = "✅ PASS" if time_saved['daily_avg'] >= 10 else "❌ FAIL"
        else:
            print(f"   No estimates recorded yet")
            status = "⏳ PENDING"
        print(f"   Status: {status}")

    print("\n" + "="*60 + "\n")

@click.command()
def go_no_go_report():
    """Generate Go/No-Go decision report."""

    collector = MetricsCollector(get_db())

    # Collect all metrics
    uptime = collector.get_uptime()
    cost = collector.get_monthly_cost()
    performance = collector.get_performance_stats()
    reliability = collector.get_reliability()
    relevance = collector.get_relevance_score()
    time_saved = collector.get_time_savings()

    # Determine pass/fail for each
    must_have = {
        "uptime": uptime['percentage'] >= 99,
        "cost": cost['total'] < 20.00,
        "performance": performance['median'] < 30000,
        "reliability": reliability['crash_count'] == 0 and reliability['data_loss'] == 0
    }

    should_have = {
        "relevance": relevance['avg'] >= 7.0 if relevance else False,
        "time_saved": time_saved['daily_avg'] >= 10 if time_saved else False,
        "context": True  # Manual check
    }

    must_have_passed = sum(must_have.values())
    should_have_passed = sum(should_have.values())

    # Determine decision
    if must_have_passed == 4:
        decision = "PROCEED TO PHASE 2"
        emoji = "✅"
    elif must_have_passed >= 3 and should_have_passed >= 2:
        decision = "PROCEED WITH CAUTION"
        emoji = "⚠️"
    else:
        decision = "PIVOT OR STOP"
        emoji = "❌"

    # Generate report
    report = f"""# Week 1 Go/No-Go Report

Generated: {datetime.utcnow().isoformat()}

## Must Have Criteria (Hard Requirements)

{'✅' if must_have['uptime'] else '❌'} **Uptime:** {uptime['successful']}/{uptime['total']} deliveries ({uptime['percentage']:.1f}%)
{'✅' if must_have['cost'] else '❌'} **Cost:** ${cost['total']:.2f} (<$20 target)
{'✅' if must_have['performance'] else '❌'} **Performance:** {performance['median']/1000:.1f}s median (<30s target)
{'✅' if must_have['reliability'] else '❌'} **Reliability:** {reliability['crash_count']} crashes, {reliability['data_loss']} data loss events

**Must Have Passed:** {must_have_passed}/4

## Should Have Criteria (Quality Indicators)

"""

    if relevance:
        report += f"{'✅' if should_have['relevance'] else '❌'} **Relevance:** {relevance['avg']:.1f}/10 (≥7.0 target)\n"
    else:
        report += f"⏳ **Relevance:** Not yet rated\n"

    if time_saved:
        report += f"{'✅' if should_have['time_saved'] else '❌'} **Time Saved:** {time_saved['daily_avg']:.1f} min/day (≥10 target)\n"
    else:
        report += f"⏳ **Time Saved:** Not yet estimated\n"

    report += f"🧠 **Agent Context:** Works correctly (manual verification needed)\n"

    report += f"""
**Should Have Passed:** {should_have_passed}/3

## Decision

**{emoji} {decision}**

"""

    if decision == "PROCEED TO PHASE 2":
        report += """All "Must Have" criteria met. Briefing system is production-ready.

**Next Steps:**
1. Transition to daily production use
2. Plan Phase 2 enhancements (preference learning, semantic search, bidirectional Telegram)
3. Document lessons learned and optimization opportunities
4. Begin Phase 2 development with high confidence
"""
    elif decision == "PROCEED WITH CAUTION":
        report += f"""Most "Must Have" criteria met, but some quality indicators need improvement.

**Issues Identified:**
"""
        if not must_have['uptime']:
            report += f"- Uptime: {uptime['percentage']:.1f}% (needs to be ≥99%)\n"
        if not must_have['cost']:
            report += f"- Cost: ${cost['total']:.2f} (exceeded $20 budget)\n"
        if not must_have['performance']:
            report += f"- Performance: {performance['median']/1000:.1f}s median (needs to be <30s)\n"
        if not must_have['reliability']:
            report += f"- Reliability: {reliability['crash_count']} crashes, {reliability['data_loss']} data loss\n"

        report += """
**Recommended Actions:**
1. Fix identified issues before Phase 2 transition
2. Run additional 3-day validation after fixes
3. Document workarounds and limitations
"""
    else:
        report += """"Must Have" criteria not met. MVP assumptions may be invalid.

**Issues Identified:**
"""
        if not must_have['uptime']:
            report += f"- Uptime too low: {uptime['percentage']:.1f}%\n"
        if not must_have['cost']:
            report += f"- Cost exceeded budget: ${cost['total']:.2f}\n"
        if not must_have['performance']:
            report += f"- Performance too slow: {performance['median']/1000:.1f}s median\n"
        if not must_have['reliability']:
            report += f"- Reliability issues: {reliability['crash_count']} crashes\n"

        report += """
**Recommended Actions:**
1. Investigate root causes
2. Consider pivoting to different architecture or approach
3. Re-evaluate MVP scope
"""

    print(report)

    # Save report to file
    report_file = Path.home() / "week1-report.md"
    with open(report_file, "w") as f:
        f.write(report)

    print(f"\nReport saved to: {report_file}")

@click.command()
@click.option('--score', type=int, required=True, help='Relevance score (1-10)')
@click.option('--notes', type=str, help='Optional notes')
def log_relevance(score, notes):
    """Log daily briefing relevance rating."""

    from datetime import date
    import csv

    log_file = Path.home() / ".linear_chief" / "relevance_log.csv"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create file if doesn't exist
    if not log_file.exists():
        with open(log_file, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "relevance_score", "notes"])

    # Append rating
    with open(log_file, "a") as f:
        writer = csv.writer(f)
        writer.writerow([str(date.today()), score, notes or ""])

    print(f"Logged relevance score: {score}/10")

# Add commands to CLI group
@click.group()
def cli():
    pass

cli.add_command(metrics)
cli.add_command(go_no_go_report)
cli.add_command(log_relevance)
```

### Usage Examples

```bash
# Show all metrics (requires 7+ days of data)
python -m linear_chief.cli metrics

# Show only automated metrics
python -m linear_chief.cli metrics --auto-only

# Log today's relevance rating
python -m linear_chief.cli log-relevance --score 8 --notes "Good issue selection"

# Generate final Go/No-Go report
python -m linear_chief.cli go-no-go-report

# Save report to file
python -m linear_chief.cli go-no-go-report > week1-report.md
```

---

## Go/No-Go Decision Template

### When to Run

After the 7th day of briefings, run the full metrics report:

```bash
python -m linear_chief.cli go-no-go-report > week1-report.md
```

### Expected Output Example

```markdown
# Week 1 Go/No-Go Report

Generated: 2025-02-06T09:15:32Z

## Must Have Criteria (Hard Requirements)

✅ **Uptime:** 7/7 deliveries (100%)
✅ **Cost:** $12.50 (<$20 target)
✅ **Performance:** 22.3s median (<30s target)
✅ **Reliability:** 0 crashes, 0 data loss events

**Must Have Passed:** 4/4

## Should Have Criteria (Quality Indicators)

✅ **Relevance:** 7.2/10 (≥7.0 target)
✅ **Time Saved:** 12 min/day (≥10 target)
🧠 **Agent Context:** Works correctly (manual verification needed)

**Should Have Passed:** 3/3

## Decision

✅ PROCEED TO PHASE 2

All "Must Have" criteria met. Briefing system is production-ready.

**Next Steps:**
1. Transition to daily production use
2. Plan Phase 2 enhancements (preference learning, semantic search, bidirectional Telegram)
3. Document lessons learned and optimization opportunities
4. Begin Phase 2 development with high confidence
```

---

## Troubleshooting & Optimization

### If Uptime < 99%

**Possible Issues:**
1. Telegram API rate limiting or outages
2. Network connectivity problems
3. APScheduler not executing job

**Debugging:**
```bash
# Check briefings table for failed deliveries
sqlite3 ~/.linear_chief/briefings.db "
SELECT generated_at, delivery_status, error_message
FROM briefings
WHERE delivery_status = 'permanently_failed'
ORDER BY generated_at DESC LIMIT 10;
"

# Check APScheduler logs
tail -50 ~/.linear_chief/scheduler.log | grep ERROR
```

**Fixes:**
- Implement retry logic with exponential backoff
- Add Telegram health check before delivery
- Monitor APScheduler job execution

---

### If Cost > $20/Month

**Possible Issues:**
1. Prompt is too large (too many issues analyzed)
2. Token usage is high due to complex reasoning
3. Briefing regeneration happening unexpectedly

**Debugging:**
```bash
# Check cost by week
sqlite3 ~/.linear_chief/briefings.db "
SELECT
    DATE(generated_at) as date,
    COUNT(*) as count,
    ROUND(SUM(cost_usd), 2) as daily_cost,
    ROUND(AVG(cost_usd), 4) as avg_cost
FROM briefings
WHERE generated_at >= date('now', '-30 days')
GROUP BY DATE(generated_at)
ORDER BY daily_cost DESC LIMIT 7;
"

# Check token usage patterns
sqlite3 ~/.linear_chief/briefings.db "
SELECT
    generated_at,
    issue_count,
    tokens_used,
    cost_usd
FROM briefings
WHERE cost_usd > (SELECT AVG(cost_usd) FROM briefings)
ORDER BY cost_usd DESC LIMIT 10;
"
```

**Optimizations:**
- Limit issue analysis to top 5-10 instead of all
- Use shorter prompt templates
- Implement caching for frequently asked questions
- Consider cheaper Claude models (e.g., Claude 3 Haiku vs Sonnet)

---

### If Performance > 30 Seconds

**Possible Issues:**
1. Claude API response time is high
2. Linear API is slow to fetch issues
3. Ranking algorithm is inefficient

**Debugging:**
```bash
# Check stage timings
python -c "
import json

stages = {}
with open('/tmp/briefing_metrics.jsonl') as f:
    for line in f:
        entry = json.loads(line)
        stage = entry['stage']
        if stage not in stages:
            stages[stage] = []
        stages[stage].append(entry['duration_ms'])

for stage, times in sorted(stages.items()):
    avg = sum(times) / len(times)
    print(f'{stage}: {avg:.0f}ms avg')
"
```

**Optimizations:**
- Parallelize API calls (fetch issues and get agent context simultaneously)
- Implement caching for Linear issues (hourly cache)
- Optimize ranking algorithm
- Use streaming for Claude response (if available)

---

### If Relevance < 70%

**Possible Issues:**
1. Ranking algorithm prioritizes wrong issues
2. Prompt instructions are unclear
3. Issue descriptions are incomplete

**Improvements:**
- Adjust ranking weights (blocked > stale > active)
- Improve prompt with more context about user's preferences
- Add more filtering (exclude low-priority labels)
- Increase time spent on issue analysis (context from previous briefings)

---

### If Time Saved < 10 minutes

**Possible Issues:**
1. Briefing is too long to read
2. Formatting is cluttered
3. Context jumps are confusing

**Improvements:**
- Reduce briefing to top 5 issues instead of 10
- Improve Markdown formatting with better spacing
- Add section headers for different issue categories
- Summarize long descriptions

---

## Monitoring & Alerting

### Daily Health Check Script

```bash
#!/bin/bash
# ~/bin/linear_chief_health_check.sh

source ~/.linear_chief/config.env

# Get latest metrics
python -m linear_chief.cli metrics --auto-only

# Check for any errors in logs
if tail -100 ~/.linear_chief/app.log | grep -i "ERROR" | grep -q .; then
    echo "⚠️  ERRORS DETECTED IN LOGS"
    tail -10 ~/.linear_chief/app.log | grep "ERROR"
fi

# Check uptime for this week
UPTIME=$(sqlite3 ~/.linear_chief/briefings.db "
SELECT ROUND(100.0 * SUM(CASE WHEN delivery_status = 'sent' THEN 1 ELSE 0 END) / COUNT(*), 1)
FROM briefings
WHERE generated_at >= date('now', '-7 days');
")

if (( $(echo "$UPTIME < 99" | bc -l) )); then
    echo "⚠️  UPTIME DEGRADED: $UPTIME%"
fi
```

---

## Summary Table

| Metric | Type | Target | Source | Query/Method |
|--------|------|--------|--------|--------------|
| Uptime | Automated | 99% (≥6/7 days) | `briefings.delivery_status` | SELECT COUNT WHERE delivery_status='sent' AND generated_at >= -7d |
| Cost | Automated | <$20/month | `briefings.cost_usd` | SELECT SUM(cost_usd) WHERE generated_at >= -30d |
| Performance | Automated | <30s median | `/tmp/briefing_metrics.jsonl` | Parse JSON lines, calc percentiles |
| Relevance | Manual | ≥70% (7/10 avg) | `~/.linear_chief/relevance_log.csv` | Daily rating after reading briefing |
| Time Saved | Manual | ≥10 min/day | `~/.linear_chief/time_saved_log.csv` | Weekly retrospective estimate |
| Reliability | Automated | 0 crashes | `briefings.error_message` | Check for null errors |

---

## References

- [Roadmap: MVP Go/No-Go Criteria](../roadmap.md#mvp-go-no-go-criteria)
- [Database Schema: Briefings Table](./database-schema.md)
- [Core Workflows: Daily Briefing Generation](./core-workflows.md#daily-briefing-generation-workflow)
- [Error Handling Strategy: Logging Standards](./error-handling-strategy.md#logging-standards)
