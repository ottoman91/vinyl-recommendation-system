# Project Information for Claude

## Project Overview
A web app that can tell a user whether they should purchase a record based on
their existing vinyl collection on Discogs.
I came across this use case because I am an avid collector of vinyl records. Oftentimes
when I visit record stores,I get confused on whether I should buy a record if it
matches with my existing taste in music. I end up browsing the album on Discogs or listening
to it on Bandcamp/Youtube,but I would ideally like an app that is trained on my
existing record collection and can recommend to me whether I should purchase the
album with reasons on why I might enjoy the album.

## V1 Functionalities
1. I can create my account and sync my Discogs account.
2. I enter the name of a record and artist and the app tells me its recommendation
3. The app should be mobile first and scale well on different devices(including ultra wide and curved monitors)
4. The app should have reasonable latency and not take more than 10-15 seconds to
give its recommendation.
5. The app should give me a yes/no rating on whether I should purchase a record and
if I will like it depending on my existing record collection.

## V2 Functionalities
1. I scan the barcode of a record and the app automatically extracts the name
and other pertinent details of the record(name of artist/band etc) that it
needs to search for the record and recommend whether I should buy it.
2. Along with giving me a yes/no rating on whether I should buy a record, the app
should also give me reasons for why I might like that record.
3. The app is open for multiple users.Each user can create their account, get a login
email and password, and connect their Discogs account. Each user is authenticated
with their account differently and securely.


## Key Design Considerations
1. How should I create the content based filtering model?
2. Where should the model be deployed?
3. How do I test/train and validate my model?
3. As the app is scaled to multiple users, will each user have their own content based
filtering model?
4. What are some data sources that I can use to train the model?


# Commit

Create well-formatted commits with conventional commit messages and emojis.

## Features:
- Runs pre-commit checks by default (lint, build, generate docs)
- Automatically stages files if none are staged
- Uses conventional commit format with descriptive emojis
- Suggests splitting commits for different concerns

## Usage:
- `/commit` - Standard commit with pre-commit checks
- `/commit --no-verify` - Skip pre-commit checks

## Commit Types:
- ✨ feat: New features
- 🐛 fix: Bug fixes
- 📝 docs: Documentation changes
- ♻️ refactor: Code restructuring without changing functionality
- 🎨 style: Code formatting, missing semicolons, etc.
- ⚡️ perf: Performance improvements
- ✅ test: Adding or correcting tests
- 🧑‍💻 chore: Tooling, configuration, maintenance
- 🚧 wip: Work in progress
- 🔥 remove: Removing code or files
- 🚑 hotfix: Critical fixes
- 🔒 security: Security improvements

## Process:
1. Check for staged changes (`git status`)
2. If no staged changes, review and stage appropriate files
3. Run pre-commit checks (unless --no-verify)
4. Analyze changes to determine commit type
5. Generate descriptive commit message
6. Include scope if applicable: `type(scope): description`
7. Add body for complex changes explaining why
8. Execute commit

## Best Practices:
- Keep commits atomic and focused
- Write in imperative mood ("Add feature" not "Added feature")
- Explain why, not just what
- Reference issues/PRs when relevant
- Split unrelated changes into separate commits

# Implement Task

Approach task implementation methodically with careful planning and execution.

## Process:

### 1. Think Through Strategy
- Understand the complete requirement
- Identify key components needed
- Consider dependencies and constraints
- Plan the implementation approach

### 2. Evaluate Approaches
- List possible implementation strategies
- Compare pros and cons of each
- Consider:
  - Performance implications
  - Maintainability
  - Scalability
  - Code reusability
  - Testing complexity

### 3. Consider Tradeoffs
- Short-term vs long-term benefits
- Complexity vs simplicity
- Performance vs readability
- Flexibility vs focused solution
- Time to implement vs perfect solution

### 4. Implementation Steps
1. Break down into subtasks
2. Start with core functionality
3. Implement incrementally
4. Test each component
5. Integrate components
6. Add error handling
7. Optimize if needed
8. Document decisions

### 5. Best Practices
- Write tests first (TDD approach)
- Keep functions small and focused
- Use meaningful names
- Comment complex logic
- Handle edge cases
- Consider future maintenance

## Checklist:
- [ ] Requirements fully understood
- [ ] Approach documented
- [ ] Tests written
- [ ] Code implemented
- [ ] Edge cases handled
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Performance acceptable
