<memory:entity schema="2" name="nested-agents-discussion" type="semantic" importance="9">
  <memory:description>Architectural discussion on nested agents using project folders as agent boundaries</memory:description>
  <memory:observations>
    <memory:observation>User conceptualizes each project folder as an agent with its own memory, rules, and behavior</memory:observation>
    <memory:observation>memory-schema project field already supports multi-agent scoping</memory:observation>
    <memory:observation>Neo4j graph can filter by project for agent-scoped queries</memory:observation>
    <memory:observation>Cross-agent communication possible via typed relations</memory:observation>
    <memory:observation>Gaps: hook routing is global, rule inheritance is CWD-only, no orchestration layer</memory:observation>
    <memory:observation>Key question: flat multi-project vs hierarchical nesting with inheritance</memory:observation>
  </memory:observations>
  <memory:reasoning>This points toward an agent orchestration layer on top of memory-schema. The schema already has the primitives (project scoping, typed relations, graph traversal). What's missing is the control plane: scoped hooks, rule inheritance across directory hierarchy, and a mechanism for parent agents to query or delegate to child agent memory spaces.</memory:reasoning>
  <memory:relations>
    <memory:relation target="deployment-verified" type="DEPENDS_ON"/>
    <memory:relation target="session-memory-switch" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
