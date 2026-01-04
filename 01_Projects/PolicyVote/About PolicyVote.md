PolicyVote is an electoral system concept where citizens vote directly on policy proposals rather than candidates or parties. Each vote contributes to a mandate for specific issues rather than giving blanket authority to elected individuals.

Political parties would still develop election programs containing policy proposals, but voters would select which proposals they support regardless of party origin. When multiple parties include the same policy in their programs, it can accumulate support across traditional party boundaries.

The approach aims to create a clearer connection between voter intent and political outcomes. Modern information technology could potentially enable the implementation and management of such a system at scale.

## Voting Mechanism

### Basic vote model
Each voter can simply support a proposal or not. Binary choice per policy.

> [!note] Open question
> Evaluate alternative models later: ranked preferences, vote point budgets, approval voting with weights.

### Policy types
- **Binary proposals**: legalize X, ban Y, join/leave agreement Z
- **Continuous proposals**: set tax rate at N%, allocate €X to program Y

All proposals must be concrete and actionable - not vague goals like "improve healthcare" but specific measures like "build 5 new hospitals in region X" or "increase nurse salaries by 10%".

### Bundling and delegation
Voters choose their level of engagement:
1. **Individual voting** - vote on each proposal separately
2. **Full package adoption** - pick a party's entire program
3. **Partial package** - adopt a party's positions for specific policy areas (e.g., "follow Party X on environmental policy")
4. **Package with overrides** - adopt a bundle but override specific votes with personal selections

This allows both engaged citizens to vote granularly and busy voters to delegate to trusted parties while maintaining override capability.

## Implementation (Finland context)

### Voting schedule
**Phase 1**: Single election day, like current system. Policies voted alongside or instead of candidate elections.

**Phase 2 (future)**: Transition to continuous voting where citizens can update positions between elections as they learn more or situations change.

### Vote privacy
- **Default**: Anonymous voting (same as current Finnish elections)
- **Optional**: Verifiable-but-private - voters can confirm their vote was counted correctly, but others cannot see individual votes. This also enables the continuous voting model where votes can be changed.

### Technical infrastructure
Centralized government system, managed by existing election authorities (e.g., Oikeusministeriö).

### Accessibility
Paper-based voting preserved. Digital voting as additional channel, not replacement. Maintains current Finnish accessibility standards.

## Handling Conflicts

### During voting
**Conflict flagging**: System warns voters when their selections are contradictory (e.g., supporting both lower taxes and increased spending). Voter must explicitly resolve or acknowledge the conflict.

### After voting
**Post-vote arbitration**: Parliament resolves conflicts between popular but incompatible policies. This is why representatives are still needed.

## Parliament and Representation

The system still elects a representative parliament, but seat allocation can be influenced by policy votes.

### Candidate positions
Candidates declare their policy positions before the election (like current vaalikone). These become their "policy bundle."

### Voter choice for representation
Voters choose their level of engagement (same flexibility as policy bundling):

1. **Pure policy voting** - vote only on issues; seat allocation calculated from how well candidates match the aggregate policy results
2. **Policy + person** - vote on issues AND explicitly support specific candidates
3. **Person only** - select a candidate (who functions as a policy bundle), with option to override specific policy positions

### Parliament's role
Parliament shifts from decision-making to implementation. Citizens have already voted on policies - parliament works out the details.

**Primary functions:**
- Implement the policy mandates from the vote
- Resolve conflicts between contradictory policies that both passed
- Handle unforeseen situations and implementation details
- Negotiate specifics within the mandate boundaries

**When parliamentary votes occur:**
- Conflict resolution between mandates
- Implementation details not covered by policy votes
- Emergency/unforeseen situations

### Mandate enforcement

**Constitutional obligation**: MPs are legally bound to vote according to the policy mandate. Deviation requires formal justification and supermajority approval.

**Transparency tracking**: Public dashboard shows:
- Each policy mandate and its support level
- How parliament/MPs have voted on related legislation
- Deviation tracking - where implementation differs from mandate and why
- MPs' individual compliance with the mandates they were "elected to represent"

This creates accountability without micromanaging every parliamentary action.

> [!note] Open question
> How exactly to calculate seat allocation from policy votes? Options: total agreement %, weighted by policy support strength, must-match on top policies.
