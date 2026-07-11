# memoryschema-managed — this compose is auto-recovered by `memoryschema preflight` when the Neo4j
# container is missing. The header sentinel above is REQUIRED for that auto `compose up`; preflight refuses
# to run a compose file that lacks it, so it never executes an untrusted docker-compose.yml from the CWD.
# Do NOT add untrusted services to this file.
services:
  neo4j:
    image: neo4j:5.26-community
    container_name: {neo4j_container_name}
    ports:
      - "{neo4j_http_port}:7474"
      - "{neo4j_bolt_port}:7687"
    environment:
      - NEO4J_AUTH=neo4j/{neo4j_password}
      - NEO4J_server_memory_heap_initial__size=1G
      - NEO4J_server_memory_heap_max__size=2G
      - NEO4J_server_memory_pagecache_size=1G
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
    volumes:
      - {volume_name}:/data
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "{neo4j_password}", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  {volume_name}:
