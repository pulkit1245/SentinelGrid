// SentinelGrid - Neo4j Graph Schema & Constraints

// 1. Constraints for unique identifiers
CREATE CONSTRAINT IF NOT EXISTS FOR (z:Zone) REQUIRE z.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sensor) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Permit) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (w:Worker) REQUIRE w.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Equipment) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (h:HazardClass) REQUIRE h.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE;

// 2. Indexes for fast querying
CREATE INDEX IF NOT EXISTS FOR (z:Zone) ON (z.name);
CREATE INDEX IF NOT EXISTS FOR (s:Sensor) ON (s.sensor_type);
CREATE INDEX IF NOT EXISTS FOR (p:Permit) ON (p.permit_type, p.status);
CREATE INDEX IF NOT EXISTS FOR (i:Incident) ON (i.date);

// Note: Relationships in Neo4j are created dynamically during ingestion.
// Expected schema semantic mappings:
// (:Sensor)-[:LOCATED_IN]->(:Zone)
// (:Worker)-[:LOCATED_IN]->(:Zone)
// (:Equipment)-[:LOCATED_IN]->(:Zone)
// (:Permit)-[:OVERLAPS_WITH]->(:Zone)
// (:Equipment)-[:MAINTAINED_BY]->(:Worker)
// (:Zone)-[:HISTORICALLY_CORRELATED_WITH {weight: 0.9}]->(:Incident)
// (:Zone)-[:PRECEDES]->(:ShiftBoundary)

// Clear existing data (for demo reset purposes only - remove in prod)
// MATCH (n) DETACH DELETE n;
