# Graph Refactoring Engine v2.5.0

Purpose: transform a valid Pixel Processor graph into an editable Substance Designer style graph.

Pass order:
1. duplicate subgraph analysis
2. safe function extraction candidates
3. dead node cleanup
4. constant folding (only pure expressions)
5. while region organization
6. edge readability scoring
7. author score evaluation

Safety:
- never fold Sequence-derived values
- never replace Set/Get/While state semantics
- preserve current runtime-semantic rules
